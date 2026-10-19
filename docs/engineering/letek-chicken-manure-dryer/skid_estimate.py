"""Budget estimate for the LETEK biogas conditioning skid (MCE-LETEK-BGS-001, 500 ppm inlet case).
MCE engineering estimate from typical budget costs per component, not vendor quotes; accuracy about +/-30%.
Equipment list and sizes are from BGS-001 Rev A (vessels and cooler unchanged at 500 ppm; media life ~179 days).
The vessels are bought from a tank shop (their fab labor is in the vendor price); MCE builds the skid, so its shop
hours are carried separately at SHOP_RATE. The skid is MCE-fabricated equipment: sell = cost / (1 - MARGIN), MARGIN 30%.
SHOP_RATE defaults to $95/hr burdened (Jason, 19 Oct 2026); SHOP_RATE=<$/hr> overrides it."""
import math, os
MARGIN = 0.30
SHOP_RATE = float(os.environ.get('SHOP_RATE') or 95)

BUYOUT = [
    ('FA-1/FA-2', '4 in bidirectional deflagration flame arresters, 316 SS, with temperature switches (2)', 9000),
    ('V-1/V-2', 'Iron-oxide vessels from a tank shop, 304 SS, 5 ft dia x 14 ft T/T, top-loading, supports and nozzles (2)', 80000),
    ('Media', 'First charge of pelletized iron oxide, 2 x 14,000 lb at about $2/lb (matches the $50-60k/yr OPEX at 500 ppm)', 56000),
    ('E-1', 'Shell and tube gas cooler, 316L tubes, ~50,000 Btu/hr', 15000),
    ('Chiller', '5-ton air-cooled glycol chiller, outdoor', 22000),
    ('F-1', 'Coalescing separator, 316L, with level-controlled condensate drainer', 9000),
    ('F-2', 'Duplex 5 micron particulate filter housing with differential pressure gauge', 8000),
    ('K-1', 'Rotary-lobe biogas blower package, gas-tight seals, 7.5 hp explosion-proof motor, VFD', 30000),
    ('PCV-1', 'Outlet pressure control and recycle valves, PT / PSL / PSH', 10000),
    ('AIT-1/2', 'Continuous gas analyzers, inlet and outlet: CH4, H2S, O2', 35000),
    ('LCP-1', 'Local control panel, NEMA 4X 304 SS, I/O and Modbus link to the burner BMS and plant PLC', 25000),
]
MATERIALS = [
    ('Steel', 'Structural steel for the two-module skid frame, ~3,000 lb', 4000),
    ('Piping', '4 in 304 SS / 316L pipe, fittings, flanges, isolation valves, gaskets', 18000),
    ('Electrical', 'Conduit, Class I Div 2 fittings, wire, junction boxes, cable tray', 6000),
    ('Consumables', 'Paint, weld consumables, gas, test media', 2000),
]
SHOP_HOURS = [
    ('Skid frame, two modules', 60),
    ('Stainless piping, ~120 ft, ~50 welds', 140),
    ('Set and mount equipment', 40),
    ('Electrical and instrument wiring, panel install', 80),
    ('Pressure, leak and function test', 30),
    ('Paint and ship prep', 20),
]
ENGINEERING = 20000   # detail engineering and drawings

buyout = sum(c for *_, c in BUYOUT)
materials = sum(c for *_, c in MATERIALS)
hours = sum(h for _, h in SHOP_HOURS)
labor = hours * SHOP_RATE if SHOP_RATE else None
cost = buyout + materials + ENGINEERING + (labor or 0)
sell = math.ceil(cost / (1 - MARGIN) / 5000) * 5000 if SHOP_RATE else None   # round up so margin never drops below MARGIN

if __name__ == '__main__':
    for group, rows in (('Bought-in equipment', BUYOUT), ('Skid materials', MATERIALS)):
        print(group)
        for tag, d, c in rows: print(f'  {tag:11s} {c:>9,}  {d}')
    print('Shop hours')
    for d, hh in SHOP_HOURS: print(f'  {hh:>4} h  {d}')
    print(f'  {hours:>4} h  total' + (f' at ${SHOP_RATE:,.0f}/hr = {labor:,.0f}' if SHOP_RATE else ' (set SHOP_RATE)'))
    print(f'Engineering {ENGINEERING:,}')
    print(f'Cost {cost:,.0f}' + ('' if SHOP_RATE else ' excluding shop labor'))
    if sell: print(f'Sell at {MARGIN:.0%} margin, rounded up to $5k: {sell:,} ({1 - cost / sell:.1%} margin)')
