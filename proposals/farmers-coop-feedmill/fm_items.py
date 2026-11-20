# Feed mill budgetary cost build-up. cost = MCE cost (2026/27 $). sell = 2x cost rounded to $5 unless 'fixed' sell.
I = []
def a(sec, tag, desc, cost, src, fixed=None): I.append(dict(sec=sec, tag=tag, desc=desc, cost=cost, src=src, fixed=fixed))
S="A. Receiving and bulk storage"
a(S,"A1","Drive-over truck receiving hopper, ~5,000 BPH, 15 HP (Sudenga 4012 type)",24500,"Graham Dec-25 sell $37,821 at Sudenga list; net ~63%")
a(S,"A2","Receiving leg, ~3,000 BPH, ~100 ft, with platforms, ladder and cage",45000,"Graham Hi-Cap 24 5,200 BPH 100 ft sell $82,890; scaled down")
a(S,"A3","Rotary scalper and drawer magnet on receiving",18000,"Allowance")
a(S,"A4","10-inch 8-hole distributor with electric positioner",9500,"Graham 14-hole sell $14,895")
a(S,"A5","Fill spouting to bins, supports",15000,"Allowance")
a(S,"A6","Hopper bins, 8 total (6 ingredients + 2 whole grains for textured feed), 24 ft dia x 12 ring, ~110 tons each, 3-4 days at peak",8*22000,"Sukup 329680 Nov-25 dealer net $17,608 bin only + hopper/gate, escalated")
a(S,"A7","Bin level indicators, high and low, 8 bins",6000,"Allowance")
a(S,"A8","Bin unload screws, 9 in, 8 bins, to grinding and batching collector",8*8500,"SCC Nov-26 screws $14.5-16.3k for longer units")
a(S,"A9","Flat storage reclaim: loader-fed receiving hopper and screw (shared with tub plant)",35000,"Allowance")
a(S,"A10","Tie-in of existing roller mill: feed screw and rolled grain conveying",12000,"Allowance")
S="B. Grinding"
a(S,"B1","MCE XM-2220 hammer mill, 75 HP motor",48000,"Graham Dec-25 sell $68,075")
a(S,"B2","Mill surge bin and rotary feeder with magnet",13000,"Townline Oct-26 feeder sell $9,670 + bin")
a(S,"B3","Air assist: plenum, pulse-jet filter with fan, airlock",30000,"Townline 16-8 baghouse/fan $15,298, plenum $7,288, PAV-8 $5,495 (sell), scaled to 2220")
a(S,"B4","Collecting screw and ground-product conveying to batching bins",28000,"Townline 9 in screw sell $12,821 + leg/screw allowance")
S="C. Batching, micro and mixing"
a(S,"C1","Overhead batching bins (8) with support structure",205000,"Scott Jan-26: 4-packs of 4-ton bins $75k each, structures $110k (cost)")
a(S,"C2","Bin discharge feeder screws to scale, 8",48000,"Allowance $6,000 each")
a(S,"C3","Major ingredient scale hopper (4 ton) and minor ingredient scale, load cells",60000,"Scott Jan-26 3-hopper scale sets $90-110k")
a(S,"C4","Micro ingredient skid, 12 bins (Scherer, budgetary allowance)",90000,"Sudenga #6768B 12-bin $64,196 (2018) escalated ~40%; Scherer price to follow")
a(S,"C5","4-ton horizontal paddle mixer with surge and drag, used and rebuilt (ASI Industrial)",70000,"Allowance; ASI 4-ton Hayes & Stolz in Billings, price TBD. New Scott 4-ton with surge/drag $230k")
a(S,"C6","Molasses addition at mixer: pump, mass flow meter, spray bar, heat-traced piping from shared tank",35000,"Tub plant pump $13,375, meter $15,960 (sell)")
a(S,"C7","High-speed molasses blender for sweet feed, 30 HP",25900,"Graham sell $36,995")
a(S,"C8","Mixed feed conveying: gentle-handling leg and 2-way diverter to pellet surge or sweet-feed bagging",24000,"Sudenga Jr 1500 BPH 30 ft net $16,918 Jan-26")
S="D. Pelleting and steam"
a(S,"D1","Pellet mill surge bin, ~10 ton, with level controls and slide gate",18000,"NBO3 35-ton bins $27,857 sell")
a(S,"D2","Continental Agra CPM Century pellet mill with feeder, force feeder and CA-125 stainless conditioner, 7-10 TPH",125000,"Per Jason; CA Q31618 Oct-26 recon package net $122,121")
a(S,"D3","125 HP 1800 rpm motor, coupling, guard, mounting",17850,"New 125 HP ~$12,500 + CA mount $5,329")
a(S,"D4","Steam generator, Clayton Steam Master 40 BHP (1,380 lb/hr) with hotwell, softener, chemical feed, blowdown",105000,"Clayton 1825B Jan-25 (Farmers Rice unit) net ~$102k; resale option")
a(S,"D5","Steam piping to conditioner: PRV, separator, traps, valves",28000,"Allowance")
S="E. Cooling, screening and bulk loadout"
a(S,"E1","Hot pellet belt conveyor, 18 in, to jump leg",32000,"NEMO C3 belt sell $68,950 (longer)")
a(S,"E2","Jump leg, gentle handling, ~1,000 BPH, ~30 ft",17500,"Sudenga Jr net $16,918 Jan-26")
a(S,"E3","Counterflow cooler CC 10-134-4, stainless contact parts, with inlet feeder",53400,"NBO3 Oct-26 sell $76,251")
a(S,"E4","Cooler air system: fan, MCE HE-36 cyclone, airlock, ductwork",37000,"NEMO: AirPro fan $9,666 cost; cyclone $13,570, airlock $9,730, duct $12,350 sell")
a(S,"E5","Cooler level and discharge controls",14200,"Cooler control system sell $20,251")
a(S,"E6","Enclosed drag conveyor, cooler to screener",22000,"Allowance; Lambton GLID-09X14 selected for NEMO, not yet priced")
a(S,"E7","Pellet screener, single deck, 10 TPH, with fines return screw",48000,"SMICO 36x72 7 TPH $25,200 cost Oct-26; SCC fines screw $16,250")
a(S,"E8","Loadout leg, gentle handling, and 4-way distributor",30000,"Lambton Sep-26: leg $14,937, distributor $14,949 (cost)")
a(S,"E9","Bulk loadout bins, 4 x ~35 ton, on drive-through structure",4*19500,"NBO3 Oct-26 $27,857 sell each")
a(S,"E10","Bulk loadout spouts, slide gates and dust-suppression spout",30000,"Allowance; ESP loadout quote to follow")
S="F. Bagging and palletizing"
a(S,"F1","Bagging surge bins, 2 (pellets and sweet feed), with gates",30000,"Allowance")
a(S,"F2","Automatic 50 lb bagging line: net-weigh scale, belt feeder, JBH9400-II bag placer, closing conveyor with kicker, sewer, flattener, stretch wrapper",210500,"ESP #32052 Rev D Jul-24 net $183,051, +15%")
a(S,"F3","Robotic palletizer, Fuji EC-201, with infeed and pallet handling",255000,"ESP #32052 Jun-24 $239,650 list, 5% OEM, +12%")
S="G. Dust control"
a(S,"G1","Central dust collection: receiving pit, legs, bins, scales and mixer pickups",45000,"Allowance")
S="H. Controls and electrical"
a(S,"H1","Plant control system: MCC, PLC, HMIs, batching and recipe software, soft starters and VFDs",265000,"Craft NEMO CQ261005024 $142,670 + batching software and larger MCC")
S="I. Engineering and services"
a(S,"I1","Detailed engineering, layout, structural and electrical design",0,"Fixed sell",fixed=118500)
a(S,"I2","MCE start-up services and operator training",0,"Fixed sell",fixed=34500)
