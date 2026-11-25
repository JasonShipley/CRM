# Two pellet line version, built on the single-line R1 model (fm_items.py)
exec(open('fm_items.py').read())
from copy import deepcopy
byt = {it['tag']: it for it in I}
def clone(tag, newtag, desc=None, base=None):
    it = deepcopy(byt[tag]); it['tag'] = newtag
    if desc: it['desc'] = desc
    if base is not None: it['base'] = base
    return it
adds = []
# Grinding line 2
adds += [clone('B1','B1-2','Second MCE XM-2220 hammer mill, 75 HP motor (grinding for line 2)'),
         clone('B2','B2-2','Mill surge bin and rotary feeder with magnet, mill 2'),
         clone('B3','B3-2','Air assist for mill 2: plenum, MCE pulse-jet filter with fan, airlock')]
# Storage: +2 hopper bins
adds.append(clone('A6','A6-2','Two more hopper bins, 24 ft dia x 12 ring (10 total)', base=2*24000))
adds.append(clone('A8','A8-2','Bin unload screws for the 2 added bins', base=2*8500))
# Mixer upsize allowance
a("C. Batching, micro and mixing","C5-2","B","Mixer upsize to 6 ton for two-line throughput (allowance over the 4-ton)",25000,"2026-11","M","ASI 6-ton single paddle, price TBD")
# Pellet line 2
for t,d in [('D1','Pellet mill surge bin, line 2'),('D2','Second Continental Agra CPM Century pellet mill with feeder, force feeder and CA-125 conditioner, 7-10 TPH'),('D3','125 HP motor, coupling, guard and mounting, line 2'),
            ('E1','Hot pellet belt conveyor, line 2'),('E2','Jump leg, line 2'),('E3','MCE counterflow cooler CC 10-134-4, line 2'),('E4','Cooler air system, line 2'),('E5','Cooler level and discharge controls, line 2'),
            ('E6','Enclosed drag conveyor, line 2'),('E7','Pellet screener with fines return, line 2')]:
    adds.append(clone(t,t+'-2',d))
a("D. Pelleting and steam","D4-2","B","Second Clayton 40 BHP Steam Master (80 BHP total, about 2,760 lb/hr) on the shared feedwater skid",60000,"2025-01","L","Clayton 1825B Jan-25 unit price $56,704 net")
a("D. Pelleting and steam","D5-2","B","Steam piping to the line 2 conditioner",12000,"2026-11","L","Allowance")
# Loadout: 4 -> 6 bins
adds.append(clone('E9','E9-2','Two more bulk loadout bins (6 total)', base=2*17000))
adds.append(clone('E10','E10-2','Loadout structure extension for 6 bins', base=47250))
a("G. Dust control","G1-2","M","Dust collection for the second grinding and pellet line",15000,"2026-11","H","Allowance")
a("H. Controls and electrical","H1-2","B","Controls and MCC expansion for line 2 (motors, I/O, soft starters)",60000,"2026-10","L","Allowance")
I.extend(adds)
for it in I:
    if it['tag']=='I1': it['fixed']=145000
    if it['tag']=='I2': it['fixed']=46500
order = [s for s in dict.fromkeys(x['sec'] for x in I)]
I.sort(key=lambda x: order.index(x['sec']))
for it in I:
    it["f"] = esc(it); it["cost"] = round(it["base"] * it["f"])
    it["sell"] = it["fixed"] if it["kind"] == "F" else r5(it["cost"] * 2) if it["kind"] == "M" else r5(it["cost"] / 0.70)
