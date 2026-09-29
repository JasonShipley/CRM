// Export what the ORIGINAL fan calculator actually renders.
//
// Like cy_hp_ref.js, this drives the original's own calc() and reads the values
// back out of the DOM shim, so the diff covers the selection, the wording and the
// formatting end to end — including the RFQ block MCE sends to AirPro.
//
// One case per runCalc: the original auto-fills the static pressure when the
// service changes and the field still holds the previous service's default, and
// that state lives in a module-level variable. A fresh load per case keeps the
// diff about the arithmetic rather than about input carry-over.
const path_ = require("path");
const { runCalc } = require("./domshim.js");
const TOOLS = path_.join(__dirname, "..", "tools");
const cases = JSON.parse(process.argv[2]);
const FAN = TOOLS + "/fan-sizing-calculator.html";

const ACC = ["accDamper", "accTrans", "accSeal", "accIso", "accSpark", "accVfd"];
const plain = (el) => String(el.innerHTML).replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();

const results = cases.map(c => {
  const seed = {
    cfm: c.cfm, sp: c.sp, temp: c.temp, alt: c.alt, margin: c.margin || 0,
    service: c.service || "radial", drive: c.drive || "belt",
    material: c.material || "ms",
  };
  const { exports: ex, get: get2 } = runCalc(FAN, seed, ["calc"]);
  // checkboxes: the shim does not read the HTML's `checked` attributes, so every
  // case states them and the port is driven with the same set.
  ACC.forEach(id => { get2(id).checked = !!(c.acc || {})[id]; });
  ex.calc();

  const rows = [];
  const html = String(get2("specs").innerHTML);
  const re = /<span class="k">([\s\S]*?)<\/span><span class="v">([\s\S]*?)<\/span>/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    rows.push([m[1].replace(/<[^>]+>/g, "").trim(), m[2].replace(/<[^>]+>/g, "").trim()]);
  }
  return {
    cfm: plain(get2("statCfm")),
    sp: plain(get2("statSp")),
    spEq: plain(get2("statSpEq")),
    hp: plain(get2("statHp")),
    specs: rows,
    rfq: String(get2("rfq").textContent),
  };
});
console.log(JSON.stringify(results));
