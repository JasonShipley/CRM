/* MCE quote form builder.
 *
 * Plain ES2020, no build step — the rest of this service has no toolchain and
 * this page is not worth adding one for.
 *
 * Three jobs:
 *   1. run a sizing calculator against /api/calc/<key> and show what came back
 *   2. turn a sizing result into priced line items
 *   3. keep totals live and save the whole quote as one JSON document
 */
"use strict";

const BOOT = JSON.parse(document.getElementById("boot").textContent);
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const usd = (n) =>
  "$" + (Math.round(n * 100) / 100).toLocaleString("en-US",
    { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/* Quote state. `lines` drives the table; `sizing` is the audit trail of every
   calculator run that fed it, saved with the quote so an engineer can see where
   a number came from. */
let lines = [];
let sizing = [];
let quoteId = BOOT.quote ? BOOT.quote.id : null;
const lastResult = {};

/* ------------------------------------------------------------ line items -- */

function lineTotal(l) {
  const qty = parseFloat(l.quantity) || 0;
  const unit = parseFloat(l.unitPrice) || 0;
  const pct = parseFloat(l.discountPercent) || 0;
  const flat = parseFloat(l.unitDiscount) || 0;
  const perUnitDiscount = flat + unit * pct / 100;
  if (String(l.amount ?? "").trim() !== "") {
    const explicit = parseFloat(l.amount);
    if (!Number.isNaN(explicit)) return { total: explicit, perUnitDiscount };
  }
  return { total: qty * (unit - perUnitDiscount), perUnitDiscount };
}

function renderLines() {
  const body = $("#lines-body");
  body.innerHTML = "";
  lines.forEach((l, i) => {
    const tr = document.createElement("tr");
    if (l.needsPrice) tr.className = "needsprice";
    tr.innerHTML = `
      <td class="dragcell">${i + 1}</td>
      <td>
        <input class="nm" type="text" data-f="name" value="">
        <textarea data-f="description" rows="2"></textarea>
      </td>
      <td><input type="text" data-f="sku" value=""></td>
      <td class="num"><input type="number" step="1" min="0" data-f="quantity"></td>
      <td class="num"><input type="number" step="0.01" data-f="unitPrice"></td>
      <td class="num"><input type="number" step="0.1" min="0" max="100" data-f="discountPercent"></td>
      <td class="num"><input type="number" step="0.01" data-f="amount" placeholder="auto"></td>
      <td><button type="button" class="rm" title="Remove line">&times;</button></td>`;

    // set values as properties, never through innerHTML, so a customer name with
    // a quote character or an angle bracket can't break the row
    $$("[data-f]", tr).forEach((el) => {
      const key = el.dataset.f;
      el.value = l[key] ?? "";
      el.addEventListener("input", () => {
        lines[i][key] = el.value;
        if (key === "unitPrice" && el.value) lines[i].needsPrice = false;
        recalc();
      });
    });
    $(".rm", tr).addEventListener("click", () => {
      lines.splice(i, 1);
      renderLines();
    });
    // auto-grow the description as it fills
    const ta = $("textarea", tr);
    const grow = () => { ta.style.height = "auto"; ta.style.height = ta.scrollHeight + "px"; };
    ta.addEventListener("input", grow);
    body.appendChild(tr);
    grow();
  });
  $("#lines-empty").hidden = lines.length > 0;
  recalc();
}

function recalc() {
  let subtotal = 0, discount = 0;
  lines.forEach((l) => {
    const { total, perUnitDiscount } = lineTotal(l);
    subtotal += total;
    discount += perUnitDiscount * (parseFloat(l.quantity) || 0);
  });
  const override = $("#q-amount").value;
  const grand = String(override).trim() !== "" ? parseFloat(override) || 0 : subtotal;
  $("#t-subtotal").textContent = usd(subtotal);
  $("#t-discount").textContent = usd(discount);
  $("#t-discount-wrap").hidden = discount <= 0;
  $("#t-total").textContent = usd(grand);
}

function addLines(newLines) {
  newLines.forEach((l) => lines.push({
    name: l.name || "",
    description: l.description || "",
    sku: l.sku || "",
    quantity: l.quantity ?? 1,
    unitPrice: l.unitPrice || "",
    unitDiscount: "",
    discountPercent: "",
    amount: "",
    needsPrice: !!l.needsPrice,
  }));
  renderLines();
}

$("#add-line").addEventListener("click", () => addLines([{ name: "", quantity: 1 }]));
$("#q-amount").addEventListener("input", recalc);

/* ------------------------------------------------------------ calculators -- */

$$("#calc-tabs .tab[data-calc]").forEach((tab) => {
  tab.addEventListener("click", () => {
    $$("#calc-tabs .tab[data-calc]").forEach((t) => t.classList.toggle("on", t === tab));
    BOOT.calcKeys.forEach((k) => { $("#panel-" + k).hidden = k !== tab.dataset.calc; });
  });
});

function collect(key) {
  const form = {};
  $$(`#panel-${key} [name]`).forEach((el) => { form[el.name] = el.value; });
  if (key === "cooler") {
    form.options = {};
    $$("[data-cooler-opt]").forEach((el) => { form.options[el.dataset.coolerOpt] = el.checked; });
  }
  return form;
}

/* Fields that only apply to one mode (the baghouse airflow basis) hide when that
   mode isn't selected, so nobody fills in a box the calculator will ignore. */
function applyShowWhen(key) {
  const form = collect(key);
  $$(`#panel-${key} [data-show-when]`).forEach((el) => {
    const cond = JSON.parse(el.dataset.showWhen);
    el.hidden = !Object.entries(cond).every(([k, v]) => String(form[k]) === String(v));
  });
}

function renderResult(key, data) {
  const box = $("#results-" + key);
  box.hidden = false;
  box.innerHTML = "";

  if (data.formula) {
    const f = document.createElement("div");
    f.className = "formula";
    f.textContent = data.formula;
    box.appendChild(f);
  }
  if (data.plenum_formula) {
    const f = document.createElement("div");
    f.className = "formula";
    f.textContent = data.plenum_formula;
    box.appendChild(f);
  }

  const outs = document.createElement("div");
  outs.className = "outs";
  (data.outputs || []).forEach((o) => {
    const d = document.createElement("div");
    d.className = "out" + (o.headline ? " head" : "");
    const k = document.createElement("span"); k.className = "k"; k.textContent = o.label;
    const v = document.createElement("span"); v.className = "v";
    v.textContent = o.unit ? `${o.value} ${o.unit}` : String(o.value);
    d.append(k, v);
    if (o.note) {
      const n = document.createElement("span"); n.className = "n"; n.textContent = o.note;
      d.appendChild(n);
    }
    outs.appendChild(d);
  });
  box.appendChild(outs);

  (data.warnings || []).forEach((w) => {
    const n = document.createElement("div");
    n.className = "note warn";
    n.style.marginTop = "10px";
    n.textContent = w;
    box.appendChild(n);
  });

  if (data.quote_lines && data.quote_lines.length) {
    const t = document.createElement("table");
    t.style.marginTop = "14px";
    const rows = data.quote_lines.map((l) => {
      const tr = document.createElement("tr");
      const a = document.createElement("td"); a.textContent = l.label;
      const b = document.createElement("td"); b.className = "num money";
      b.textContent = l.included ? "incl." : usd(l.amount);
      tr.append(a, b);
      return tr;
    });
    const head = document.createElement("tr");
    head.innerHTML = '<th>Package breakdown</th><th class="num">Amount</th>';
    t.append(head, ...rows);
    box.appendChild(t);
  }

  if (data.price_notes && data.price_notes.length) {
    const p = document.createElement("div");
    p.className = "pricenotes";
    data.price_notes.forEach((note) => {
      const d = document.createElement("div");
      d.textContent = note;
      p.appendChild(d);
    });
    box.appendChild(p);
  }

  if (data.total) {
    const tot = document.createElement("div");
    tot.className = "formula";
    tot.style.marginTop = "12px";
    tot.textContent = `Package total ${usd(data.total)}`;
    box.appendChild(tot);
  }
}

async function runCalc(key) {
  const status = $("#status-" + key);
  const addBtn = $(`[data-add="${key}"]`);
  status.textContent = "Sizing…";
  addBtn.disabled = true;
  let data;
  try {
    const res = await fetch(BOOT.calcUrl.replace("__KEY__", key), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(collect(key)),
    });
    data = await res.json();
  } catch (e) {
    status.textContent = "Could not reach the server.";
    return;
  }
  if (data.error) {
    const box = $("#results-" + key);
    box.hidden = false;
    box.innerHTML = "";
    const n = document.createElement("div");
    n.className = "note err";
    n.textContent = data.error;
    box.appendChild(n);
    status.textContent = "";
    return;
  }
  lastResult[key] = data;
  renderResult(key, data);
  const n = (data.lines || []).length;
  addBtn.disabled = n === 0;
  status.textContent = n ? `${n} line${n === 1 ? "" : "s"} ready to add` : "Sized — no priced lines";
}

BOOT.calcKeys.forEach((key) => {
  $(`[data-run="${key}"]`).addEventListener("click", () => runCalc(key));
  $(`[data-add="${key}"]`).addEventListener("click", () => {
    const data = lastResult[key];
    if (!data) return;
    addLines(data.lines || []);
    sizing.push({
      calculator: data.calculator, key,
      inputs: collect(key),
      formula: data.formula || "",
      outputs: data.outputs || [],
      warnings: data.warnings || [],
      at: new Date().toISOString(),
    });
    $("#status-" + key).textContent = "Added to the quote below.";
    $(`[data-add="${key}"]`).disabled = true;
  });
  $$(`#panel-${key} [name]`).forEach((el) =>
    el.addEventListener("change", () => applyShowWhen(key)));
  applyShowWhen(key);
});

/* Hammermill: picking a product refills the three figures it governs and shows
   the XM index chart row, the way the standalone calculator does. */
const productSel = $("#hammermill-product");
if (productSel) {
  const refill = () => {
    const d = BOOT.productDefaults[Number(productSel.value)];
    if (!d) return;
    $("#hammermill-index").value = d.index;
    $("#hammermill-sqInHp").value = d.sqInHp;
    $("#hammermill-bulkDensity").value = d.bulkDensity;
    const hint = $("#hm-chart");
    if (d.chart) {
      const c = d.chart;
      hint.hidden = false;
      hint.textContent =
        `XM index chart${c.row ? ` (${c.row})` : ""}: index ${c.idx} · ${c.sq} in²/HP · ` +
        `${c.dens} lb/ft³ · recommended rotor ${c.rec}` + (c.note ? ` — ${c.note}` : "");
    } else {
      hint.hidden = true;
    }
  };
  productSel.addEventListener("change", refill);
  refill();
}

/* ------------------------------------------------------------------ save -- */

function payload() {
  return {
    name: $("#q-name").value,
    quoteNumber: $("#q-ref").value,
    status: $("#q-status").value,
    project: $("#q-project").value,
    expirationDate: $("#q-expires").value,
    terms: $("#q-terms").value,
    comments: $("#q-comments").value,
    preparedBy: $("#q-prepared").value,
    amount: $("#q-amount").value,
    customer: {
      company: $("#c-company").value, contact: $("#c-contact").value,
      email: $("#c-email").value, phone: $("#c-phone").value,
      street1: $("#c-street1").value, street2: $("#c-street2").value,
      city: $("#c-city").value, state: $("#c-state").value,
      postcode: $("#c-postcode").value, country: "",
    },
    lines,
    sizing,
  };
}

async function save() {
  const status = $("#save-status");
  status.textContent = "Saving…";
  const url = quoteId ? BOOT.updateUrl.replace("__ID__", quoteId) : BOOT.createUrl;
  let data;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload()),
    });
    data = await res.json();
  } catch (e) {
    status.textContent = "Could not reach the server — nothing was saved.";
    return null;
  }
  if (data.error) {
    status.textContent = data.error;
    return null;
  }
  quoteId = data.id;
  // keep the URL in step so a refresh reopens this quote rather than a blank form
  history.replaceState(null, "", data.editUrl);
  status.textContent = "Saved.";
  return data;
}

$("#save").addEventListener("click", save);
$("#save-pdf").addEventListener("click", async () => {
  const data = await save();
  if (data) window.open(data.pdfUrl, "_blank", "noopener");
});

/* Warn before losing unsaved work. */
let dirty = false;
document.addEventListener("input", () => { dirty = true; });
$("#save").addEventListener("click", () => { dirty = false; });
window.addEventListener("beforeunload", (e) => {
  if (dirty) { e.preventDefault(); e.returnValue = ""; }
});

/* ------------------------------------------------------------- load edit -- */

if (BOOT.quote) {
  const q = BOOT.quote;
  const c = q.customer || {};
  $("#q-name").value = q.name || "";
  $("#q-ref").value = q.quoteNumber || "";
  $("#q-status").value = q.status || "DRAFT";
  $("#q-project").value = q.project || "";
  $("#q-expires").value = q.expirationDate || "";
  $("#q-terms").value = q.terms || "";
  $("#q-comments").value = q.comments || "";
  $("#q-amount").value = q.amount || "";
  if (q.preparedBy) $("#q-prepared").value = q.preparedBy;
  ["company", "contact", "email", "phone", "street1", "street2", "city", "state", "postcode"]
    .forEach((k) => { $("#c-" + k).value = c[k] || ""; });
  lines = (q.lines || []).map((l) => ({ ...l }));
  sizing = q.sizing || [];
}
renderLines();
