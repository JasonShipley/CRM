// Drive the ORIGINAL hammermill calculator headless and print its results as JSON.
const path_ = require("path");
const { runCalc } = require("./domshim.js");
const TOOLS = path_.join(__dirname, "..", "tools");
const path = TOOLS + "/hammermill-sizing-calculator.html";
const cases = JSON.parse(process.argv[2]);
const out = [];
for (const c of cases) {
  const seed = {
    "capacity-pph": c.pph, "screen-64ths": c.screen64, "index-no": c.index,
    "sqin-hp": c.sqInHp, "bulk-density": c.bulkDensity, "run-length": c.runLength,
    "mill-mult": 1.73, "feeder-mult": 2.00, "plenum-duty": 1.35, "plenum-rate": 15.25,
    "plenum-velocity": String(c.plenumVelocity || 300), "feeder-dia": String(c.feederDia || 10),
    "cup-type": c.cupType || "nylon", "magnet-clean": c.magnetClean || "sma",
    "row-count": c.rowCount || "", "product-select": "0",
  };
  const { exports: ex, get } = runCalc(path, seed,
    ["compute", "state", "MCE_XM_MILLS", "FAMILY_SETS", "familyOf", "nextMotorHp",
     "MILL_PRICING", "FEEDER_PRICING", "PLENUM_V_IDX", "WIDTH_TO_ROW", "sizeCodeOf",
     "SCREW_TABLES", "FEEDER_10", "FEEDER_14", "POCKET_FILL", "toStandardLength"]);
  // reproduce the file's own chain using ITS functions and ITS tables
  const hp = c.pph / c.index / c.screen64;
  const motorHp = ex.nextMotorHp(hp);
  const areaReq = motorHp * c.sqInHp;
  const fam = c.family || "grain";
  const pool = ex.MCE_XM_MILLS.filter(m => ex.FAMILY_SETS[fam].includes(ex.familyOf(m)))
                              .sort((a, b) => a.area - b.area);
  const mill = pool.find(m => m.area >= areaReq) || pool[pool.length - 1];
  const rowCount = c.rowCount || ex.WIDTH_TO_ROW[ex.sizeCodeOf(mill)];
  const fTable = String(c.feederDia || 10) === "14" ? ex.FEEDER_14 : ex.FEEDER_10;
  const fRow = fTable.find(f => f.rows === rowCount);
  const cuft = String(c.feederDia || 10) === "14" ? fRow.cuft
    : ((c.cupType || "nylon") === "nylon" ? fRow.nylon : fRow.ss);
  const feederRpm = c.pph / 60 / c.bulkDensity / (cuft * ex.POCKET_FILL);
  const cfm = mill.area * 1.3;
  const flange = cfm / (c.plenumVelocity || 300);
  const cuftHr = c.pph / c.bulkDensity;
  const trough = c.trough || "45";
  const srows = ex.SCREW_TABLES[trough];
  const screw = srows.find(r => r.atMax >= cuftHr) || srows[srows.length - 1];
  const stdLen = ex.toStandardLength(mill.glen / 12 + (c.runLength || 0));
  const mp = ex.MILL_PRICING[mill.model];
  const millPrice = mp.bliss * 1.73;
  const fIdx = ex.FEEDER_PRICING.rows.indexOf(rowCount);
  const dia = String(c.feederDia || 10) === "14" ? "d14" : "d10";
  const feederPrice = fIdx === -1 ? null :
    (ex.FEEDER_PRICING[dia][c.cupType || "nylon"][fIdx] + ex.FEEDER_PRICING.clean[c.magnetClean || "sma"][fIdx]) * 2.00;
  const wBliss = mp.pw[ex.PLENUM_V_IDX[String(c.plenumVelocity || 300)]];
  const plenumPrice = wBliss * 1.35 * 15.25;
  out.push({
    hp: +hp.toFixed(4), motorHp, areaReq, mill: mill.model, millArea: mill.area,
    fAreaReq: Math.round(areaReq).toLocaleString(), fCfm: Math.round(mill.area * 1.3).toLocaleString(),
    headroom: Math.round((mill.area - areaReq) / mill.area * 100),
    hpHeadroom: Math.round((mill.hpMax - motorHp) / mill.hpMax * 100),
    rowCount, feederRpm: +feederRpm.toFixed(4), cfm: +cfm.toFixed(4),
    flange: +flange.toFixed(4), cuftHr: +cuftHr.toFixed(4), screwDia: screw.dia,
    screwRpm: +(cuftHr / screw.at1).toFixed(4), stdLen,
    millPrice: +millPrice.toFixed(2), feederPrice: feederPrice === null ? null : +feederPrice.toFixed(2),
    plenumPrice: +plenumPrice.toFixed(2),
    total: +(millPrice + (feederPrice || 0) + plenumPrice).toFixed(2),
  });
}
console.log(JSON.stringify(out));
