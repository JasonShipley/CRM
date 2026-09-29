// Export what the ORIGINAL XF fan calculator renders.
//
// Same pattern as fan_ref.js: drive the original's own recalc() and read the
// values back out of the DOM shim, so the diff covers the duct arithmetic, the
// LS capacity-table selection, the wording and the formatting end to end.
//
// One fresh load per case. The selected catalog row lives in
// window.__selectedCandidateIdx and persists across recalc() calls within a page,
// so reloading keeps the diff about the selection rule rather than about which
// row somebody clicked last.
const path_ = require("path");
const { runCalc } = require("./domshim.js");
const TOOLS = path_.join(__dirname, "..", "tools");
const cases = JSON.parse(process.argv[2]);
const XF = TOOLS + "/xf-fan-sizing-calculator.html";

const text = (el) => String(el.textContent).replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
const plain = (s) => String(s).replace(/<[^>]+>/g, " ").replace(/&quot;/g, '"')
  .replace(/&amp;/g, "&").replace(/&#8593;/g, "").replace(/\s+/g, " ").trim();

const results = cases.map(c => {
  const seed = {
    elev: c.elev, temp: c.temp,
    cfm1: c.cfm1, dia1: c.dia1, len1: c.len1, elbows: c.elbows,
    equip1: c.equip1, cfm2: c.cfm2, sp2: c.sp2, margin: c.margin,
  };
  if (c.entry !== undefined) seed.entry = c.entry;
  if (c.exit !== undefined) seed.exit = c.exit;
  if (c.fanClass !== undefined) seed.fanClass = c.fanClass;
  if (c.assumedDia !== undefined) seed.assumedDia = c.assumedDia;
  if (c.refQ !== undefined) {
    Object.assign(seed, { refQ: c.refQ, refSP: c.refSP, refRPM: c.refRPM,
                          refBHP: c.refBHP, refDia: c.refDia === undefined ? "" : c.refDia });
  }
  const { exports: ex, get } = runCalc(XF, seed, ["recalc"]);
  get("useRef").checked = !!c.useRef;
  ex.recalc();

  // the catalog shortlist, as the table renders it
  const rows = [];
  const html = String(get("catalogTable").innerHTML);
  const re = /<tr onclick="selectCandidate\((\d+)\)"([\s\S]*?)<\/tr>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const cells = [...m[2].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map(x => plain(x[1]));
    rows.push(cells);
  }
  const solve = [];
  const sre = /<span class="k">([\s\S]*?)<\/span><span class="v">([\s\S]*?)<\/span>/g;
  let s;
  const solveHtml = String(get("f_solveRows").innerHTML);
  while ((s = sre.exec(solveHtml)) !== null) solve.push([plain(s[1]), plain(s[2])]);

  return {
    density: String(get("densityOut").value),
    vel: text(get("r_vel")), fric: text(get("r_fric")), fit: text(get("r_fit")),
    equip: text(get("r_equip")), total: text(get("r_total")),
    totalStd: text(get("r_totalstd")),
    spStd: text(get("f_spstd")), bhp: text(get("f_bhp")), motor: text(get("f_motor")),
    tip: text(get("f_tip")), tipFlag: plain(get("f_tipflag").innerHTML),
    solve, rows,
    xref: plain(get("vendorXref").innerHTML).slice(0, 200),
  };
});
console.log(JSON.stringify(results));
