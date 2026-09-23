// Export the ORIGINAL cooler/baghouse computed tables + selection results as JSON.
const path_ = require("path");
const { runCalc } = require("./domshim.js");
const TOOLS = path_.join(__dirname, "..", "tools");
const mode = process.argv[2];

if (mode === "cooler") {
  const cases = JSON.parse(process.argv[3]);
  const { exports: ex } = runCalc(
    TOOLS + "/counterflow-cooler-sizing-calculator.html",
    { tph: 20, density: 40, margin: 0, upsize: "0", mealHeight: "std4", panel: "mce", xp: "none", sensors: 0, pellet: "p6" },
    ["MODELS", "OPTS", "ADDERS", "PELLETS", "pickModels", "interpPd", "list", "CHECK_DEFS", "PRICING", "DUCT_SIZES", "fmt"]);

  const results = cases.map(c => {
    const p = ex.PELLETS.find(x => x.id === c.pellet);
    const margin = 1 + (c.margin || 0) / 100;
    const density = c.density || p.dens || 40;
    if (p.meal) {
      const reqCfm = c.tph * p.cfmTon * margin;
      const reqArea = reqCfm / p.faceMax;
      const suffix = c.mealHeight === "tall6" ? "-6" : c.mealHeight === "mid5" ? "-5" : "-4";
      let units = 1, best = null;
      while (units <= 4 && !best) {
        const per = reqArea / units;
        const cands = ex.MODELS.filter(m => m.area >= per && m.model.endsWith(suffix))
                               .sort((a, b) => a.area - b.area || a.price - b.price);
        if (cands.length) { best = cands[Math.min(c.upsize || 0, cands.length - 1)]; break; }
        units++;
      }
      return { meal: true, reqCfm: +reqCfm.toFixed(4), reqArea: +reqArea.toFixed(4),
               fCfm: ex.fmt(Math.round(reqCfm)), fArea: ex.fmt(reqArea, 0),
               model: best ? best.model : null, units, price: best ? best.price : null };
    }
    const reqCfm = c.tph * p.cfmTon * margin;
    const reqVol = (c.tph * 2000 / 60) * p.ret / density * margin;
    const reqTph = c.tph * margin;
    const hits = ex.pickModels(reqCfm, reqVol, reqTph);
    const up = Math.min(c.upsize || 0, Math.max(hits.length - 1, 0));
    const best = hits[up];
    // air()
    let air = null;
    for (const d of ex.DUCT_SIZES) {
      const area = Math.PI / 4 * Math.pow(d / 12, 2);
      const v = reqCfm / area;
      if (v <= 5700) {
        const pd = ex.interpPd(d) * Math.pow(v / 4500, 2);
        const bhp = reqCfm * (p.wci + 8) / (6356 * 0.60);
        const motor = [10,15,20,25,30,40,50,60,75,100,125,150,200,250,300].find(h => h >= bhp) || Math.ceil(bhp);
        air = { d, v: +v.toFixed(4), pd: +pd.toFixed(4), motor,
                cyc: 2 * Math.ceil(Math.sqrt(reqCfm / 5.45) / 2) };
        break;
      }
    }
    return { meal: false, reqCfm: +reqCfm.toFixed(4), reqVol: +reqVol.toFixed(4),
             fCfm: ex.fmt(Math.round(reqCfm)), fVol: ex.fmt(reqVol, 0),
             fBed: best ? ex.fmt(reqVol / best.area, 1) : null,
             fVel: best ? ex.fmt(reqCfm / best.area, 0) : null,
             fUtil: best ? ex.fmt(reqVol / best.vol * 100, 0) : null,
             model: best ? best.model : null, price: best ? best.price : null,
             bed: best ? +(reqVol / best.area).toFixed(4) : null,
             vel: best ? +(reqCfm / best.area).toFixed(4) : null,
             util: best ? +(reqVol / best.vol * 100).toFixed(4) : null, air };
  });
  console.log(JSON.stringify({
    modelPrices: Object.fromEntries(ex.MODELS.map(m => [m.model, m.price])),
    opts: ex.OPTS, adders: ex.ADDERS, results }));
}

if (mode === "baghouse") {
  const cases = JSON.parse(process.argv[3]);
  const { exports: ex } = runCalc(
    TOOLS + "/baghouse-filter-calculator.html",
    { "direct-cfm": 3000, "screen-area": 2400, "ratio-custom": "" },
    ["MCE_MODELS", "KICE_MODELS", "CLOTH_PER_BAG_FT", "PULSE_PER_BAG_FT"]);
  const results = cases.map(c => {
    const cfm = c.mode === "mill" ? c.screenArea * 1.3 : c.cfm;
    const reqArea = cfm / c.ratio;
    const pool = ex.MCE_MODELS.filter(m => c.lenFilter === "any" || m.len === Number(c.lenFilter));
    const mce = pool.find(m => m.area >= reqArea) || null;
    const kice = ex.KICE_MODELS.find(m => m.area >= reqArea) || null;
    return { cfm: +cfm.toFixed(4), reqArea: +reqArea.toFixed(4),
             mce: mce ? mce.model : null, mceArea: mce ? +mce.area.toFixed(4) : null,
             mcePulse: mce ? +mce.pulse.toFixed(4) : null,
             mcePlan: mce ? mce.plan : null, mceH: mce ? mce.housingH : null,
             kice: kice ? kice.model : null };
  });
  console.log(JSON.stringify({ count: ex.MCE_MODELS.length, results }));
}
