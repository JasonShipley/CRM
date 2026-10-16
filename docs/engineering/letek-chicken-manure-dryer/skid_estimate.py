"""Budget estimate for the LETEK biogas conditioning skid (MCE-LETEK-BGS-001, 500 ppm inlet case).
MCE engineering estimate from typical budget costs per component, not vendor quotes; accuracy about +/-30%.
Equipment list and sizes are from BGS-001 Rev A (vessels and cooler unchanged at 500 ppm; media life ~179 days).
Prints the cost build-up and the sell price at MCE's vendor-net / 0.8 convention."""
ITEMS = [
    ('FA-1/FA-2', '4 in bidirectional deflagration flame arresters, 316 SS, with temperature switches (2)', 9000),
    ('V-1/V-2', 'Iron-oxide vessels, 304 SS, 5 ft dia x 14 ft T/T, top-loading, supports and nozzles (2)', 80000),
    ('Media', 'First charge of pelletized iron oxide, 2 x 14,000 lb at about $2/lb (matches the $50-60k/yr OPEX at 500 ppm)', 56000),
    ('E-1', 'Shell and tube gas cooler, 316L tubes, ~50,000 Btu/hr', 15000),
    ('Chiller', '5-ton air-cooled glycol chiller, outdoor', 22000),
    ('F-1', 'Coalescing separator, 316L, with level-controlled condensate drainer', 9000),
    ('F-2', 'Duplex 5 micron particulate filter housing with differential pressure gauge', 8000),
    ('K-1', 'Rotary-lobe biogas blower package, gas-tight seals, 7.5 hp explosion-proof motor, VFD', 30000),
    ('PCV-1', 'Outlet pressure control and recycle valves, PT / PSL / PSH', 10000),
    ('AIT-1/2', 'Continuous gas analyzers, inlet and outlet: CH4, H2S, O2', 35000),
    ('LCP-1', 'Local control panel, NEMA 4X 304 SS, I/O and Modbus link to the burner BMS and plant PLC', 25000),
    ('Skid', 'Structural skid ~10 x 24 ft, 4 in 304 SS / 316L piping and valves, wiring, assembly in two modules', 60000),
    ('Eng.', 'Detail engineering, drawings, factory pressure and function test', 20000),
]
net = sum(c for _, _, c in ITEMS)
sell = round(net / 0.8 / 5000) * 5000
if __name__ == '__main__':
    for tag, d, c in ITEMS: print(f'{tag:10s} {c:>9,}  {d}')
    print(f'{"net":10s} {net:>9,}')
    print(f'sell (net / 0.8, rounded to $5k): {sell:,}  range at +/-30%: {round(sell*0.7,-3):,.0f} to {round(sell*1.3,-3):,.0f}')
