// Minimal DOM shim: enough to run MCE's calculator scripts headless so their
// outputs can be diffed against the Python ports.
const fs = require("fs");

function makeEl(id) {
  const el = {
    id, _value: "", textContent: "", innerHTML: "", hidden: false, checked: false,
    disabled: false, style: {}, dataset: {}, options: [], tBodies: [], rows: [],
    classList: { _s: new Set(), add(...c){c.forEach(x=>this._s.add(x));},
      remove(...c){c.forEach(x=>this._s.delete(x));}, contains(c){return this._s.has(c);} },
    get value() { return this._value; },
    set value(v) { this._value = String(v); },
    setAttribute(){}, getAttribute(){return null;}, addEventListener(){},
    appendChild(c){ if (this.options !== undefined && c && c.__opt) this.options.push(c); return c; },
    insertRow(){ const r = makeEl(); this.rows.push(r); return r; },
    createTBody(){ const t = makeEl(); this.tBodies.push(t); return t; },
    querySelector(){ return makeEl(); }, querySelectorAll(){ return []; },
    // the XF calculator draws a fan curve; the shim accepts the calls and draws
    // nothing, so the arithmetic around the chart still runs
    clientWidth: 600, clientHeight: 210, width: 600, height: 210, selectedIndex: 0,
    getContext(){ return new Proxy({}, { get: () => () => undefined }); },
    get parentElement(){ return makeEl(); },
    get firstChild(){ return null; }, removeChild(){},
  };
  // tables are read as `table.tBodies[0].innerHTML = ...` by the calculators
  el.tBodies = [{ innerHTML: "", rows: [], insertRow() { const r = makeEl(); this.rows.push(r); return r; } }];
  return el;
}

// Pull each <select>'s own <option> list out of the page. The calculators read
// `sel.options[sel.selectedIndex].dataset.*` for things the option carries — the
// XF calculator keeps each fan class's efficiency and curve shape there — so the
// shim has to have the real options, not an empty list.
function parseSelects(html) {
  const out = new Map();
  const re = /<select\b[^>]*\bid="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const opts = [];
    const ore = /<option\b([^>]*)>([\s\S]*?)<\/option>/g;
    let o;
    while ((o = ore.exec(m[2])) !== null) {
      const attrs = o[1];
      const dataset = {};
      let d;
      const dre = /data-([\w-]+)="([^"]*)"/g;
      while ((d = dre.exec(attrs)) !== null) dataset[d[1]] = d[2];
      const v = /\bvalue="([^"]*)"/.exec(attrs);
      opts.push({ value: v ? v[1] : o[2].trim(), dataset,
                  selected: /\bselected\b/.test(attrs),
                  text: o[2].replace(/<[^>]+>/g, "").trim() });
    }
    out.set(m[1], opts);
  }
  return out;
}

function buildDocument(seed, html) {
  const els = new Map();
  const selects = parseSelects(html || "");
  const get = (id) => {
    if (!els.has(id)) {
      const e = makeEl(id);
      const opts = selects.get(id);
      if (opts && opts.length) {
        e.options = opts.map(o => {
          const el = makeEl();
          el._value = o.value; el.dataset = o.dataset; el.textContent = o.text;
          return el;
        });
        const chosen = opts.find(o => o.selected) || opts[0];
        e._value = chosen.value;
        Object.defineProperty(e, "selectedIndex", {
          get() {
            const i = opts.findIndex(o => o.value === e._value);
            return i < 0 ? 0 : i;
          },
          set() {}, configurable: true,
        });
      }
      // a seeded value always wins over the page's own default
      if (seed[id] !== undefined) e._value = String(seed[id]);
      els.set(id, e);
    }
    return els.get(id);
  };
  const document = {
    getElementById: get,
    addEventListener(){}, documentElement: makeEl("html"),
    querySelector: (s) => get("q:" + s),
    querySelectorAll: () => [],
    createElement: (tag) => { const e = makeEl(); if (tag === "option") e.__opt = true; return e; },
    body: makeEl("body"),
  };
  return { document, els, get };
}

function runCalc(htmlPath, seed, exportNames) {
  const html = fs.readFileSync(htmlPath, "utf8");
  // greedy to the LAST </script>: one calculator closes with </body></html>
  const m = html.match(/<script>([\s\S]*)<\/script>/);
  if (!m) throw new Error("no script block");
  const { document, get } = buildDocument(seed, html);
  const sandbox = {
    document, console, Math, Number, String, Array, Object, JSON, parseInt,
    parseFloat, isNaN,
    window: { addEventListener(){}, devicePixelRatio: 1 },
    // the XF calculator reads its chart colours off CSS custom properties
    getComputedStyle: () => ({ getPropertyValue: () => "#000" }),
  };
  sandbox.globalThis = sandbox;
  const vm = require("vm");
  vm.createContext(sandbox);
  const src = m[1] + "\n;globalThis.__exports = {" +
    exportNames.map(n => `${n}: typeof ${n} !== "undefined" ? ${n} : undefined`).join(",") + "};";
  vm.runInContext(src, sandbox, { filename: htmlPath });
  return { exports: sandbox.__exports, get, sandbox };
}

// The value="" a page ships its number inputs with. runCalc does NOT apply these
// on its own — a case that states nothing would then silently inherit whatever
// MCE last typed into the HTML. A ref script that wants a freshly-loaded page
// merges them into its seed deliberately.
function pageDefaults(htmlPath) {
  const html = fs.readFileSync(htmlPath, "utf8");
  const out = {};
  const re = /<input\b([^>]*)>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const id = /\bid="([^"]+)"/.exec(m[1]);
    const value = /\bvalue="([^"]*)"/.exec(m[1]);
    if (id && value) out[id[1]] = value[1];
  }
  return out;
}

module.exports = { runCalc, makeEl, pageDefaults };
