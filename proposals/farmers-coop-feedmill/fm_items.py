# Farmers Coop Van Buren feed mill - budgetary cost model R1 (Nov 20, 2026)
# kind: M = MCE-built (sell = 2x cost), B = buyout (sell = cost / 0.70), F = fixed sell
# base = quoted/reference cost, qd = quote date (YYYY-MM), steel = steel share of cost (escalated if quoted before 2026-07)
from datetime import date
STEEL_FACTOR = 1.20/0.575 - 1      # steel $0.55-0.60/lb early 2026 -> $1.20/lb now = +109%
GEN_INFL = 0.04                    # general inflation per year, to mid-2027 order/build
BUILD = date(2027, 6, 1)
STEEL_CUTOFF = date(2026, 7, 1)
CLS = {"H": 0.35, "M": 0.20, "L": 0.06, "N": 0.0}
I = []
def a(sec, tag, kind, desc, base, qd, cls, src, fixed=None):
    I.append(dict(sec=sec, tag=tag, kind=kind, desc=desc, base=base, qd=qd, cls=cls, src=src, fixed=fixed))
S = "A. Receiving and bulk storage"
a(S,"A1","B","Drive-over truck receiving hopper, ~5,000 BPH, 15 HP (Sudenga 4012 type)",23830,"2025-12","H","Graham sell $37,821 = Sudenga list; net 63%")
a(S,"A2","B","Receiving leg, ~3,000 BPH, ~100 ft, platforms, ladder and cage",40000,"2025-12","H","Graham Hi-Cap 24 5,200 BPH list $82,890; net 63%, scaled down")
a(S,"A3","B","Rotary scalper and drawer magnet on receiving",18000,"2026-11","M","Allowance")
a(S,"A4","B","10-inch 8-hole distributor with electric positioner",9385,"2025-12","H","Graham 14-hole list $14,895; net 63%")
a(S,"A5","M","Fill spouting to bins, with supports",15000,"2026-11","H","Allowance")
a(S,"A6","B","Hopper bins, 8 (6 ingredients + 2 whole grains), 24 ft dia x 12 ring, ~110 tons each, 3-4 days at peak",8*24000,"2025-11","H","Sukup 329680 Nov-25 net $17,608 bin + hopper/legs")
a(S,"A7","B","Bin level indicators, high and low, 8 bins",6000,"2026-11","L","Allowance")
a(S,"A8","B","Bin unload screws, 9 in, 8 bins, to grinding and batching collector",8*8500,"2026-11","H","SCC Nov-26 screws $14.5-16.3k for longer units")
a(S,"A9","M","Flat storage reclaim: loader-fed receiving hopper and screw (shared with tub plant)",35000,"2026-11","H","Allowance")
a(S,"A10","M","Tie-in of existing roller mill: feed screw and rolled grain conveying",12000,"2026-11","H","Allowance")
S = "B. Grinding"
a(S,"B1","M","MCE XM-2220 hammer mill, 75 HP motor",47650,"2025-12","H","Graham Dec-25 sell $68,075 x 0.70")
a(S,"B2","M","Mill surge bin and rotary feeder with magnet",13000,"2026-10","M","Townline Oct-26 feeder sell $9,670 + bin")
a(S,"B3","M","Air assist: plenum, MCE pulse-jet filter with fan, airlock",30000,"2026-10","H","Townline Oct-26 baghouse/fan, plenum, PAV-8 (scaled to 2220)")
a(S,"B4","B","Collecting screw and ground-product conveying to batching bins",28000,"2026-11","H","SCC Nov-26 screws + leg allowance")
S = "C. Batching, micro and mixing"
a(S,"C1","B","Overhead batching bins (8) with support structure",205000,"2026-01","H","Scott Jan-26: 4-packs of 4-ton bins $75k, structures $110k")
a(S,"C2","B","Bin discharge feeder screws to scale, 8",48000,"2026-11","H","Allowance $6,000 each")
a(S,"C3","B","Major ingredient scale hopper (4 ton) and minor ingredient scale, load cells",60000,"2026-01","M","Scott Jan-26 scale sets $90-110k for 3")
a(S,"C4","B","Micro ingredient skid, 12 bins (Scherer, budgetary allowance)",64196,"2018-06","M","Sudenga #6768B 12-bin 2018; Scherer price to follow")
a(S,"C5","B","4-ton horizontal paddle mixer with surge and drag, used and rebuilt (ASI Industrial)",70000,"2026-11","M","Allowance pending Bob Hamlin price; new Scott 4-ton $230k")
a(S,"C6","B","Molasses addition at mixer: pump, mass flow meter, spray bar, traced piping from shared tank",35000,"2026-10","M","Tub plant pump $13,375 / meter $15,960 sell")
a(S,"C7","B","High-speed molasses blender for sweet feed, 30 HP",25900,"2025-12","M","Graham sell $36,995 x 0.70")
a(S,"C8","B","Mixed feed leg, gentle handling, and 2-way diverter (pellet surge or sweet-feed bagging)",22000,"2026-01","H","Sudenga Jr 1500 BPH 30 ft net $16,918 + diverter")
S = "D. Pelleting and steam"
a(S,"D1","M","Pellet mill surge bin, ~10 ton, level controls and slide gate",18000,"2026-10","H","NBO3 bins")
a(S,"D2","B","Continental Agra CPM Century pellet mill with feeder, force feeder and CA-125 stainless conditioner, 7-10 TPH",125000,"2026-10","N","Per Jason; CA Q31618 Oct-26")
a(S,"D3","B","125 HP 1800 rpm motor, coupling, guard and mounting",17850,"2026-10","L","New 125 HP ~$12,500 + CA mount $5,329")
a(S,"D4","B","Steam generator, Clayton Steam Master 40 BHP (1,380 lb/hr), hotwell, softener, chemical feed, blowdown",102000,"2025-01","L","Clayton 1825B Jan-25 (Farmers Rice unit); resale option")
a(S,"D5","B","Steam piping to conditioner: PRV, separator, traps and valves",28000,"2026-11","L","Allowance")
S = "E. Cooling, screening and bulk loadout"
a(S,"E1","M","Hot pellet belt conveyor, 18 in, to jump leg",32000,"2026-11","H","NEMO C3 belt (longer) sell $68,950")
a(S,"E2","B","Jump leg, gentle handling, ~1,000 BPH, ~30 ft",17000,"2026-01","H","Sudenga Jr net $16,918")
a(S,"E3","M","MCE counterflow cooler CC 10-134-4, stainless contact parts, with inlet feeder",53400,"2026-10","H","NBO3 Oct-26 sell $76,251 x 0.70")
a(S,"E4","M","Cooler air system: fan, MCE HE-36 cyclone, airlock, ductwork",37000,"2026-10","H","NEMO fan $9,666 cost; cyclone/airlock/duct")
a(S,"E5","M","Cooler level and discharge controls",14200,"2026-10","L","Cooler control sell $20,251 x 0.70")
a(S,"E6","B","Enclosed drag conveyor, cooler to screener",22000,"2026-11","H","Allowance; Lambton GLID-09X14 not yet priced")
a(S,"E7","B","Pellet screener, 10 TPH, with fines return screw",48000,"2026-10","M","SMICO 36x72 $25,200 Oct-26 + SCC fines screw $16,250; used option from ASI pending")
a(S,"E8","B","Loadout leg, gentle handling, and 4-way distributor",30000,"2026-09","H","Lambton Sep-26 leg $14,937 + distributor $14,949")
a(S,"E9","B","Bulk loadout bins, 4 x ~35 ton hopper tanks with slide gates",4*17000,"2025-11","H","Sukup/hopper tank budget")
a(S,"E10","B","Drive-through loadout structure, hot-dip galvanized, handrails, stairs and ladders (existing truck scale)",135000,"2026-01","H","Farmers Rice 2025-26: steel $50,405 (Superior) + Dubois fab/galv $82,049")
a(S,"E11","B","Bulk loadout spouts, slide gates and dust-suppression spout",30000,"2026-11","M","Allowance")
S = "F. Bagging and palletizing"
a(S,"F1","M","Bagging surge bins, 2 (pellets and sweet feed), with gates",30000,"2026-11","H","Allowance")
a(S,"F2","B","Automatic 50 lb bagging line: net-weigh scale, belt feeder, JBH9400-II bag placer, closing conveyor with kicker, sewer, flattener, stretch wrapper",183051,"2024-07","L","ESP #32052 Rev D Jul-24 net")
a(S,"F3","B","Robotic palletizer, Fuji EC-201, infeed and pallet handling",227668,"2024-06","L","ESP #32052 Jun-24 $239,650 list less 5% OEM")
S = "G. Dust control"
a(S,"G1","M","Central dust collection: receiving pit, legs, bins, scales and mixer pickups",45000,"2026-11","H","Allowance")
S = "H. Controls and electrical"
a(S,"H1","B","Plant control system: MCC, PLC, HMIs, batching and recipe software, soft starters and VFDs",265000,"2026-10","L","Craft NEMO CQ261005024 $142,670 + batching software/larger MCC")
S = "I. Engineering and services"
a(S,"I1","F","Detailed engineering, layout, structural and electrical design",0,"2026-11","N","Fixed sell",fixed=118500)
a(S,"I2","F","MCE start-up services and operator training",0,"2026-11","N","Fixed sell",fixed=34500)

def esc(it):
    y, m = map(int, it["qd"].split("-")); qd = date(y, m, 1)
    yrs = max(0, (BUILD - qd).days / 365.25)
    f = (1 + GEN_INFL) ** yrs
    if qd < STEEL_CUTOFF: f *= 1 + CLS[it["cls"]] * STEEL_FACTOR
    return f
def r5(x): return int(round(x / 5.0)) * 5
for it in I:
    it["f"] = esc(it); it["cost"] = round(it["base"] * it["f"])
    it["sell"] = it["fixed"] if it["kind"] == "F" else r5(it["cost"] * 2) if it["kind"] == "M" else r5(it["cost"] / 0.70)
