// Export what the ORIGINAL rotary cooler calculator renders.
//
// Drives its own calc() and reads the rendered blocks back out of the DOM shim,
// so the diff covers the psychrometrics, the drum selection, the drive and fan
// sizing, the summer sweep and every label as the page writes it.
const path_ = require("path");
const { runCalc, pageDefaults } = require("./domshim.js");
const TOOLS = path_.join(__dirname, "..", "tools");
const cases = JSON.parse(process.argv[2]);
const RC = TOOLS + "/rotary-cooler-sizing-calculator.html";

const plain = (s) => String(s).replace(/<sub>/g, "").replace(/<\/sub>/g, "")
  .replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/\s+/g, " ").trim();

const pairs = (el) => {
  const out = [];
  const re = /<span class="k">([\s\S]*?)<\/span><span class="v">([\s\S]*?)<\/span>/g;
  let m;
  while ((m = re.exec(String(el.innerHTML))) !== null) out.push([plain(m[1]), plain(m[2])]);
  return out;
};

const results = cases.map(c => {
  // the preset list is injected by the page at load, so the shim never sees those
  // options — every case states the preset explicitly
  const seed = Object.assign({ preset: "feed", units: "1", humMode: "wb",
                               sweepMode: "w", fanLoc: "id" },
                             pageDefaults(RC), c);
  const { exports: ex, get } = runCalc(RC, seed, ["calc"]);
  ex.calc();
  return {
    model: plain(get("modelName").textContent),
    chips: plain(get("chips").innerHTML),
    qair: plain(get("sQair").innerHTML),
    scfm: plain(get("sScfm").innerHTML),
    fan: plain(get("sFan").innerHTML),
    tout: plain(get("sTout").innerHTML),
    drum: pairs(get("drumSpecs")),
    thermal: pairs(get("thermalSpecs")),
    psy: pairs(get("psySpecs")),
    fanSpecs: pairs(get("fanSpecs")),
    banners: [...String(get("banners").innerHTML)
      .matchAll(/<div class="banner (\w+)">([\s\S]*?)<\/div>/g)]
      .map(m => [m[1], plain(m[2])]),
  };
});
console.log(JSON.stringify(results));
