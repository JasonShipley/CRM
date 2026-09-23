// Export what the ORIGINAL cyclone / hammer-pattern calculators actually render.
//
// Unlike the other reference runners, these two drive the original's own
// compute() and read the values back out of the DOM shim, so the diff covers
// selection, wording and formatting end to end.
const path_ = require("path");
const { runCalc } = require("./domshim.js");
const TOOLS = path_.join(__dirname, "..", "tools");
const mode = process.argv[2];
const cases = JSON.parse(process.argv[3]);

const text = (get, sel) => get("q:" + sel).textContent;
// the originals write a few strips as innerHTML with <span class="hi"> markers
const plain = (get, sel) => get("q:" + sel).innerHTML
  .replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();

if (mode === "cyclone") {
  const { exports: ex, get } = runCalc(
    TOOLS + "/cyclone-cfm-calculator.html",
    { }, ["state", "compute", "BUDGET_SPEC", "HE_SPEC", "H_SPEC", "HE_MAX_CFM"]);

  const results = cases.map(c => {
    ex.state.mode = c.mode || "cfm";
    ex.state.series = c.series || "mce";
    ex.state.wg = String(c.wg || "3");
    ex.state.inletShape = c.inletShape || "round";
    ex.state.fpm = c.fpm || 3500;
    get("q:#direct-cfm").value = c.cfm != null ? String(c.cfm) : "";
    get("q:#inlet-round-id").value = c.inletId != null ? String(c.inletId) : "";
    get("q:#inlet-rect-w-id").value = c.inletW != null ? String(c.inletW) : "";
    get("q:#inlet-rect-h-id").value = c.inletH != null ? String(c.inletH) : "";
    ex.compute();
    const heShown = get("q:#he-info").style.display === "block";
    return {
      ratedCfm: text(get, "#rated-cfm"),
      matchSize: text(get, "#match-size"),
      detail: text(get, "#match-detail"),
      pill: text(get, "#match-pill"),
      formula: plain(get, "#formula-strip"),
      // #he-alt-note lives inside #he-info, which the page hides whole on the
      // budget and H paths; the shim has no containers, so scope it here.
      altNote: (ex.state.series === "mce" && heShown && get("q:#he-alt-note").style.display === "block")
        ? get("q:#he-alt-note").textContent : "",
    };
  });
  console.log(JSON.stringify(results));
}

if (mode === "hammer") {
  const { exports: ex, get } = runCalc(
    TOOLS + "/hammer-pattern-calculator.html",
    { }, ["compute", "distribute", "REF_BOM", "TOTAL_PINS", "COLLAR_W"]);

  const results = cases.map(c => {
    // the row toggle is a querySelectorAll click target the shim cannot press,
    // so seed the pressed button's dataset the way a click would leave it
    get('q:#pattern-toggle button[aria-pressed="true"]').dataset.rows = String(c.rows);
    get("q:#motor-hp").value = c.motorHp != null ? String(c.motorHp) : "";
    get("q:#hp-per-hammer").value = String(c.hpPerHammer);
    get("q:#pin-length").value = String(c.pinLength);
    get("q:#hammer-thickness").value = String(c.thickness);
    get("q:#pin-allowance").value = String(c.pinAllowance);
    get("q:#count-override").value = c.countOverride != null ? String(c.countOverride) : "";
    ex.compute();
    const viz = get("q:#row-viz").innerHTML;
    const perPair = (viz.match(/<div class="rc-count">(\d+)<\/div>/g) || [])
      .map(s => Number(s.replace(/\D/g, "")));
    const bom = (get("q:#bom-tbody").innerHTML.match(/<tr><td>(.*?)<\/td><td>(.*?)<\/td><\/tr>/g) || [])
      .map(r => { const m = r.match(/<tr><td>(.*?)<\/td><td>(.*?)<\/td><\/tr>/); return [m[1], m[2]]; });
    return {
      count: text(get, "#count-result"),
      pill: text(get, "#count-pill"),
      actualHph: text(get, "#actual-hph"),
      capacityRange: text(get, "#capacity-range"),
      countNote: text(get, "#count-note"),
      distDetail: text(get, "#dist-detail"),
      balanceNote: text(get, "#balance-note"),
      stackNote: text(get, "#stack-note"),
      stackHammers: text(get, "#stack-hammers"),
      stackLength: text(get, "#stack-length"),
      spacerLength: text(get, "#spacer-length"),
      spacerTotal: text(get, "#spacer-total"),
      perPair, bom,
    };
  });
  console.log(JSON.stringify(results));
}
