"""Build the LETEK budgetary quote PDF from the repo's branded quote template, priced from the
HubSpot product export (hubspotcrmexportsallproducts20260824.csv), and append the calculator PFD."""
import base64, csv, json, subprocess, sys, os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
HERE=Path(__file__).parent; REPO=HERE.parents[2]
PRODUCTS=sys.argv[1]  # path to the HubSpot export csv
rows={r['Name']:r for r in csv.DictReader(open(PRODUCTS,encoding='utf-8-sig'))}
def price(name): return float(rows[name]['Unit price'])
def money(v): return "${:,.2f}".format(v)

APP="""Application (sized with the MCE Dryer HMB Calculator, case LETEK_140tpd_caseA, 9 Sep 2026; PFD attached):
Product: chicken manure biodigester effluent, screw-pressed to cake, 3/8" minus
Incoming moisture content (to dryer): 70% (effluent 85% ahead of the press)
Est bulk density: 55 lb/ft3 wet cake, 30 lb/ft3 dried
Desired output MC: 15%
Lb/hr in: 6,430 (140 MT/day of effluent at 85%)
Lb/hr out: 2,269 (24.7 MT/day bedding)
Lb of water removed: 4,161 per hour
Gal of H2O removed: 499 per hour
Est BTU of entire system: 7,281,000 BTU/hr (rigorous check 6,610,000)
Drum inlet gas 900 F, exhaust 230 F, 24 h/day
Fuel source: LPG with biogas (55% CH4) as primary; 145.77 MMBtu/day of biogas covers about 83% of the duty"""

XD96 = APP + """

XD Series - Heavy Duty Direct Fired Rotary Thermal Conditioning System
- Feed screw system with 5 HP motor
- Co-current single pass Rotary Dehydration Drum (8' dia x 40' long). Drum to be constructed from A36 steel (see line 3 for stainless)
- Heavy Duty Dryer Drop-Out Box for dry product
- Airlock complete with 1.5 HP motor, drive and control devices, mild steel construction
- Drum Drive mounted on a structural base complete with 30 HP motor and drive
- Full tooth, mounted chain sprocket to match chain drive
- Forged steel drum tracks with HD attachment points
- Front trunnion base with hardened trunnion wheels mounted on a structural base
- Rear trunnion base with hardened trunnion wheels and thrust wheel assembly mounted on a structural base
- Front and rear water deluge nozzle for fire suppression
- Inlet and discharge seals

Exhaust Fan
- XF-40 fan, arrangement #9F, AR 235 rotor, 60 HP TEFC 230-460V/3/60, V-belt drive, 23" inlet, vibration isolation sleeve, inspection door, drain port
- Calculator: 12,934 ACFM at 230 F, 12 in WC static, 42 bhp

Ducting and Transition
- Ducting, transitions and elbows up to 60 lineal feet, 22" dia, A36 construction

Control System and Fire Prevention
- Basic Burner Management System control panel
- Electrical and control instrumentation for MCE's proprietary processing equipment
- Motor control cabinet for seller's equipment, 3 phase, 60 Hz, 480 V
- Manual quench nozzles provided; automated fire suppression system quoted upon request
- Standard 435 MOP burner and pre-piped, pre-wired valve train are replaced by the oversized dual-fuel burner on line 2

System Commissioning
- 1 man-week; equipment installation instructions for buyer's installation contractors
- Start-up and operator training"""

BURNER="""Burner oversized for this application per MCE engineering: 10 MMBtu/hr maximum with 10:1 turndown (normal fire 7.3 MMBtu/hr, calculator 8.7 with margin), sized to hold capacity if the press cake runs wetter than 70% or the plant runs 160 MT/day.
- Dual-fuel: biogas (55% CH4, ~195 scfm at 2 psig) and LPG, two independent NFPA 86 gas trains with automatic changeover on gas pressure
- Combustion air blower, flame safeguard integrated with the BMS panel
- Replaces the standard 435 MOP burner and single valve train included in line 1
PRICE: burner vendor quote pending - to be added"""

SS="""Recommended for digestate (ammonia, chlorides, pH to 8.2). In lieu of the A36 construction on line 1: 316L stainless drum shell (1/2" plate, sub-arc welded, X-ray shell) and flights, 316L feed screw and live bottom, 316L drop-out box (3/16" walls, 1/4" hopper), 316L airlock, R-15 mineral wool insulation with 26 ga 304 SS cladding on drum and drop-out box, Nomex inlet and discharge seals.
Priced from MCE's 8' x 40' 316L XC Series system as built for a US animal-health customer (2022 pricing, not escalated); the exhaust fan, ducting and cyclone in 316L are quoted on request (the 304 SS cyclone adder is on line 7). Estimated equipment life 30-35 years for 316L versus 7-10 years for 3/8" A36.
Adder over the line 1 price; not included in the total below."""

lines=[
 dict(name='XD-96 Mk.2 Rotary Thermal Conditioning System', qty=1, unit=price('XD-96 Mk.2 Rotary Thermal Conditioning System'), desc=XD96),
 dict(name='Dual-fuel burner upgrade, 10 MMBtu/hr, LPG + biogas', qty=1, unit=0.0, desc=BURNER),
 dict(name='OPTION: 316L stainless steel construction (in lieu of line 1 A36)', qty=1, unit=1529000.0-price('XD-96 Mk.2 Rotary Thermal Conditioning System'), desc=SS),
 dict(name='XB 4.9 Live Bottom Storage Hopper', qty=1, unit=price('XB 4.9 Live Bottom Storage Hopper'), desc="Press cake surge ahead of the dryer feed screw, 2 hours at 6,430 lb/hr.\n"+rows['XB 4.9 Live Bottom Storage Hopper']['Product description']),
 dict(name='HD Screw Conveyor', qty=1, unit=price('HD Screw Conveyor'), desc="Cake transfer from live-bottom hopper to the dryer feed screw.\n"+rows['HD Screw Conveyor']['Product description']),
 dict(name='HE-74 Cyclone', qty=1, unit=price('HE-74 Cyclone'), desc="Dryer exhaust collector, 12,934 ACFM at 230 F (rated to 30,500 CFM).\n"+rows['HE-74 Cyclone']['Product description']),
 dict(name='HE-74 Cyclone - 304 stainless construction adder', qty=1, unit=21000.0, desc="304 stainless construction of the HE-74 for the wet, ammonia-laden dryer exhaust (adder per HE-74 catalog description). 1\" insulation and aluminum cladding available for an additional $9,995."),
 dict(name='FT-12 Airlock', qty=1, unit=price('FT-12 Airlock'), desc="Rotary airlock under the HE-74 cyclone discharge; fines rejoin the dried product.\n"+rows['FT-12 Airlock']['Product description']),
 dict(name='OPTION: Automation and Controls (PLC / HMI upgrade)', qty=1, unit=price('Automation and Controls'), desc="Optional upgrade in place of the basic BMS panel. Not included in the total below.\n"+rows['Automation and Controls']['Product description']),
 dict(name='Screw press dewatering system', qty=1, unit=0.0, desc="Screw press, 12,900 lb/hr (5.8 m3/h) of digestate at 15% TS to 30% TS cake, 316 SS screen and screw, with agitated receiving tank (8 h) and progressive-cavity feed pump. Cake moisture sets the dryer duty; a bench test on a 5-gallon sample is required.\nPRICE: vendor quote pending - to be added"),
 dict(name='Biogas conditioning skid', qty=1, unit=0.0, desc="For 195 scfm (7,455 Nm3/day): iron-oxide H2S vessel (5,000 ppm in, under 200 ppm out), chiller / coalescer moisture knockout, booster blower to 2 psig, flame arrester, pressure control.\nPRICE: allowance to be added once the biogas analysis (H2S, moisture, supply pressure) is received"),
 dict(name='Freight', qty=1, unit=0.0, desc="FOB Stuart, FL. Sea freight door to door Stuart - Miami - Progreso - Merida estimated at $27,206 in April 2026 (two 40 ft HiCube containers plus one oversize drum piece); to be re-quoted for the XD-96 and billed at time of shipment."),
]
items=[]; subtotal=0.0
for i,l in enumerate(lines,1):
    net=l['qty']*l['unit']
    if not l['name'].startswith('OPTION'): subtotal+=net
    items.append(dict(name=l['name'],sku='',_qty=l['qty'],_unit=money(l['unit']) if l['unit'] else 'TBD',_unit_discount='—',_net=money(net) if l['unit'] else ('TBD' if 'PRICE' in l['desc'] else 'not included'),_desc_lines=[x for x in l['desc'].splitlines() if x.strip()]))
comments=("Bernardo, thank you for the revised requirements of 20 August. This budgetary proposal covers the 85% to 15% case at 120 to 160 MT/day. "
"We recommend mechanical dewatering ahead of the dryer: a screw press removes roughly 60% of the water at a fraction of the cost of evaporating it, which brings the dryer duty to about 7.3 MMBtu/hr at 140 MT/day and lets your biogas cover about 83% of it (LPG make-up on the order of US$420/day at US$14.50/MMBtu; about US$2,500/day with the digester offline). "
"The XD-96 Mk.2 drum is sized with margin for 160 MT/day and cake moisture variability; the burner is oversized to 10 MMBtu/hr for the same reason. "
"Line 3 prices the drum system in 316L stainless as an option (US$1,529,000 for the 316L system in place of the US$589,500 A36 system), which we recommend for this material. Lines marked TBD are awaiting vendor quotes or your process data (effluent total solids, pH, chlorides, ammonia; biogas composition and pressure; site layout). A 5-gallon sample of the effluent to our Stuart, FL shop will let us confirm press performance and flight design. "
"The attached process flow sheet is the mass and energy balance this proposal is built on.")
terms=("50% down with order, 30% on approval drawings, 15% before shipment, 5% on start-up. Budgetary proposal, valid 60 days. "
"Delivery 18-22 weeks after approval drawings, to be confirmed by production at time of order. Installation, foundations, utilities, permits, biogas and LPG supply, effluent storage and pressate disposal by others. "
"Prices in US dollars, FOB Stuart, FL, exclusive of taxes and duties.")
logo=base64.b64encode((REPO/'renderer'/'assets'/'mce-logo.png').read_bytes()).decode()
ctx=dict(q=dict(name='Chicken Manure Digestate Drying System - 140 MT/day - Budgetary Proposal',company=dict(name='LETEK DCG'),comments=comments,terms=terms),
 items=items,logo_b64=logo,seller=dict(company='Midwest Custom Engineering, Inc.',address=['6526 S Kanner Hwy #215','Stuart, FL 34997','United States']),
 seller_contact=('Jason Shipley','jason@usemce.com','+16202009109'),buyer_contact='Bernardo Urquiza (burquiza@letekdcg.com)',
 ref='20260909-LETEK-A',issue_date='Sep 9, 2026',expires='Nov 8, 2026',subtotal=money(subtotal),total_discount=money(0),total=money(subtotal),has_discount=False,
 a=dict(addressStreet1='Bosques de las Lomas',addressStreet2='',addressCity='Mexico City',addressState='',addressPostcode='',addressCountry='Mexico'))
env=Environment(loader=FileSystemLoader(str(REPO/'renderer'/'templates')))
html=env.get_template('quote.html').render(**ctx).replace('size: A4','size: letter')
(HERE/'quote_body.html').write_text(html)
js=f"""const {{ chromium }} = require('playwright');(async()=>{{const b=await chromium.launch({{executablePath:'/opt/pw-browsers/chromium'}});const p=await b.newPage();
await p.setContent(require('fs').readFileSync('{HERE/'quote_body.html'}','utf8'),{{waitUntil:'networkidle'}});
await p.pdf({{path:'{HERE/'quote_body.pdf'}',format:'Letter',printBackground:true,margin:{{top:'0',bottom:'0',left:'0',right:'0'}}}});await b.close();}})();"""
(HERE/'_pdf.js').write_text(js)
subprocess.run(['node',str(HERE/'_pdf.js')],check=True,env=dict(os.environ,NODE_PATH=subprocess.run(['npm','root','-g'],capture_output=True,text=True).stdout.strip()))
subprocess.run(['pdfunite',str(HERE/'quote_body.pdf'),str(HERE/'LETEK_140tpd_caseA_Flow.pdf'),str(HERE/'MCE_Quote_20260909-LETEK-A_Chicken_Manure_Dryer.pdf')],check=True)
for f in ('quote_body.html','quote_body.pdf','_pdf.js'): (HERE/f).unlink()
print('subtotal',money(subtotal)); print('written MCE_Quote_20260909-LETEK-A_Chicken_Manure_Dryer.pdf')
