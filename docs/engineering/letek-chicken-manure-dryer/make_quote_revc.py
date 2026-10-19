"""LETEK Rev C budgetary quote (reportlab, base-14 fonts, e-mail size).
Basis: 128.7 MT/day liquid digestate at 8% TS, screw press to 30-35% TS cake, XD-72 Mk.2.
Pricing basis and open items are in README.md (Rev C section). Writes quote_data_revC.json and the PDF.
The biogas skid allowance comes from skid_estimate.py; SKID=<dollars> overrides it."""
import json, io, os
from pathlib import Path
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, PageBreak
from reportlab.lib.enums import TA_RIGHT
HERE = Path(__file__).parent; REPO = HERE.parents[2]
REF = '20261019-LETEK-C'; ISSUE = 'Oct 19, 2026'; EXPIRES = 'Dec 18, 2026'
import skid_estimate
SKID = float(os.environ['SKID']) if os.environ.get('SKID') else (float(skid_estimate.sell) if skid_estimate.sell else None)

APP = """Feed: 128.7 MT/day of liquid digestate at 8% TS (about 34,000 gal/day), 24 h/day, 350 days/year
Dewatered cake to the dryer: 3,153 lb/hr at 30% TS (70% moisture), sized at full solids capture
Desired output moisture: 15%
Dried product: 1,113 lb/hr (12.1 MT/day) at full capture
Water removed: 2,040 lb/hr (245 gal/hr)
Thermal duty: 3.57 MMBtu/hr (rigorous check 3.24); at 35% TS cake 2.8 MMBtu/hr
Biogas (145.8 MMBtu/day, about 6.1 MMBtu/hr average) covers about 170% of the duty
Exhaust: 6,342 ACFM at 230 F, 12 in WC static, about 18 bhp at the fan shaft (the 60 HP XF-36 fan on line 1 also covers the decanter case); drum inlet gas 900 F"""

XD72 = """XD Series - Heavy Duty Direct Fired Rotary Thermal Conditioning System
- Feed screw system with 2 HP motor; the dewatering unit discharges by chute directly onto the feed screw
- Co-current single pass rotary dehydration drum (7' dia x 35' long), A36 steel (stainless on request, see options)
- Heavy duty drop-out box for dry product
- Airlock with 1.5 HP motor, drive and control devices, mild steel
- Drum drive on a structural base with 20 HP motor and drive; full tooth chain sprocket
- Forged steel drum tracks; front and rear trunnion bases with hardened trunnion wheels and thrust wheel assembly
- Front and rear water deluge nozzles for fire suppression; inlet and discharge seals

Exhaust Fan
- XF-36 fan, arrangement #9F, AR 235 rotor, 60 HP TEFC 230-460V/3/60, V-belt drive, 21" inlet, vibration isolation sleeve, inspection door, drain port

Ducting and Transition
- Ducting, transitions and elbows up to 60 lineal feet, A36 construction

Control System and Fire Prevention
- Basic burner management system control panel; electrical and control instrumentation for MCE equipment
- Motor control cabinet for seller's equipment, 3 phase, 60 Hz, 480 V
- Manual quench nozzles; automated fire suppression quoted on request
- The standard 435 MOP burner and valve train are replaced by the dual-fuel burner on line 2

System Commissioning
- 1 man-week; installation instructions for the buyer's contractors; start-up and operator training"""

BURNER = """10 MMBtu/hr maximum with 10:1 turndown. Normal fire is about 3.6 MMBtu/hr on screw press cake; the margin covers wetter cake, LPG-only operation when the digester is down, and the decanter option below.
- Dual-burner system: one LPG burner and one biogas burner, each with stainless combustor sleeve, integral combustion blower and filter, and independent air and gas actuators with position feedback
- Two NFPA 86 safety valve trains (LPG and flanged biogas) with dual safety shut-off valves, high and low gas pressure switches and gas meters; automatic changeover to LPG on loss of biogas
- Parallel-positioning air/fuel control with separate LPG and biogas fuel profiles (runs in the PLC/HMI on line 3)
- Burner management panel, NEMA 4X fiberglass enclosure, two self-checking UV flame safeguards, high-temperature limits, combustion E-stop
- One week of combustion start-up and tuning on site"""

PRESS = """Two screw presses in parallel, sized for about 35,000 gal/day of digestate at 8% TS, 0.5 mm screen, direct fed by chopper pump. Includes the chopper feed pump and press drives on VFDs and a basic control package. About 50 hp connected for the presses and pumps. Expected cake 30 to 35% TS. Lead time about 20 weeks.
Materials: stainless steel components throughout except the cast iron press bodies, which are kept for rigidity (stainless bodies flex and wear the screens and screws). An internal protective coating of the press bodies is recommended for the chloride and ammonia in this digestate; it will be confirmed and priced after the sample test.
A screw press needs some fiber structure in the solids to work. This line is conditional on a test of a sample of your digestate, which will confirm cake solids, solids capture and whether polymer is needed.
Good mixing ahead of the presses is essential to separation; the feed tank and its mixer are by others, with the mixer sized after the sample test. Polymer make-up system, if the test shows it is needed, is quoted after the test."""

SKIDTXT = """For 195 scfm (7,455 Nm3/day) of biogas at 500 ppm H2S or less (bulk H2S removal in the digester by others): iron-oxide polishing vessels to under 100 ppm, gas cooler and moisture knockout, booster blower to 2 psig, inlet and outlet flame arresters, pressure control, inlet and outlet gas analyzers (CH4, H2S, O2), local control panel linked to the burner BMS, and the first charge of iron-oxide media. Process design MCE-LETEK-BGS-001.
"""

lines = [
 dict(name='XD-72 Mk.2 Rotary Thermal Conditioning System', qty=1, unit=489000.0, desc=XD72),
 dict(name='Dual-fuel burner upgrade, 10 MMBtu/hr, LPG + biogas', qty=1, unit=170000.0, desc=BURNER),
 dict(name='Automation and Controls (PLC / HMI)', qty=1, unit=89950.0, desc="Required with the dual-fuel burner: the PLC hosts the parallel-positioning fuel profiles for LPG and biogas, the automatic changeover logic, dryer temperature control and the operator HMI, and links to the dewatering unit, the biogas skid and the plant system."),
 dict(name='HE-36 Cyclone', qty=1, unit=13570.0, desc="Dryer exhaust collector for 6,342 ACFM at 230 F, selected with MCE's cyclone sizing calculator: the duty sits in the HE-36 operating range (6,175 to 7,600 CFM), close to its optimum inlet velocity for capturing fines. 36 in diameter, 25.5 x 10.75 in tangential inlet, 10 in flanged discharge, mount pads and inspection port. Fines rejoin the dried product."),
 dict(name='HE-36 Cyclone - 304 stainless construction adder', qty=1, unit=8000.0, desc="304 stainless construction of the cyclone for the wet, ammonia-laden dryer exhaust."),
 dict(name='FT-12 Airlock', qty=1, unit=12895.0, desc="Rotary airlock under the cyclone discharge; fines rejoin the dried product."),
 dict(name='Screw press dewatering system, 2 units, subject to sample test', qty=1, unit=312500.0, desc=PRESS),
 dict(name='Biogas conditioning skid, 500 ppm inlet', qty=1, unit=SKID or 0.0, desc=SKIDTXT + ("Budget allowance from our component estimate for this design (accuracy about +/-30%); it will be firmed up into a fixed price once the biogas analysis is available." if SKID else "PRICE: budget allowance to follow.")),
 dict(name='Freight', qty=1, unit=0.0, desc="FOB Stuart, FL. Sea freight door to door Stuart - Miami - Progreso - Merida to be quoted for the final equipment list and billed at time of shipment; the April 2026 estimate for a comparable shipment was about $27,000."),
 dict(name='OPTION: decanter centrifuge in place of the screw press (line 7)', qty=1, unit=-46620.0, desc="If the sample test shows the solids are too fine for a screw press. A reconditioned decanter centrifuge in place of line 7, with the cyclone stepped up to an HE-47 in 304 stainless for the higher airflow (HE-47 range 10,825 to 12,600 CFM): net change -$46,620 against the base total (reconditioned decanter $262,500).\nTrade-offs: cake about 20% TS instead of 30 to 35%, so the dryer duty rises to about 6.3 MMBtu/hr (biogas covers about 96%, the rest LPG) and exhaust to about 11,200 ACFM; polymer is more likely to be needed. Availability and lead time are confirmed when a specific reconditioned unit is selected."),
 dict(name='OPTION: 316L stainless steel drum system (in lieu of line 1 A36)', qty=1, unit=422500.0, desc="316L drum shell and flights, feed screw, drop-out box and airlock in place of A36, for long service on digestate (ammonia, chlorides, pH about 8). Estimated shell life 30 to 35 years for 316L versus 7 to 10 years for 3/8 in A36. Adder over line 1."),
]

def money(v): return '${:,.2f}'.format(v)
subtotal = sum(l['qty']*l['unit'] for l in lines if not l['name'].startswith('OPTION'))

comments = ("Bernardo, thank you for the data and the call on 29 September. This Rev C budgetary proposal is sized on your confirmed basis: "
"128.7 MT/day of liquid digestate at 8% TS, with the grit and sand stream handled separately. "
"We recommend a screw press ahead of the dryer. We expect 30 to 35% TS cake from a screw press on this feed and about 20% from a decanter centrifuge. "
"At 30% TS the dryer duty is about 3.6 MMBtu/hr, so your biogas covers it with a wide margin and LPG is only needed at start-up or with the digester down. "
"That lets us drop from the XD-96 to the XD-72 drum, delete the storage hopper and transfer screw (the press discharges straight onto the dryer feed screw), "
"and size the cyclone to the smaller airflow. The 10 MMBtu/hr dual-fuel burner stays, so the dryer can still run on LPG alone. "
"The biogas conditioning skid is carried as a budget allowance from our component estimate, to be firmed up once the biogas analysis is available. "
"A reconditioned decanter centrifuge is priced as an option in case the sample test shows the solids are too fine for a press. "
"A sample of your digestate is needed to confirm cake solids, solids capture and polymer for either route; the press line is quoted subject to that test. "
"Dried product is 12.1 MT/day at full solids capture. A press without polymer typically captures 60 to 80% of the solids, which would give about 7.3 to 9.7 MT/day; polymer raises capture. "
"The liquid fraction from the dewatering step is described after the line items so you can size its treatment to the NOM-001 limits; that treatment is by others.")
terms = ("50% down with order, 30% on approval drawings, 15% before shipment, 5% on start-up. Payment terms are as stated on this quote and on the invoice. Past-due balances may be reported to business credit bureaus, including Dun & Bradstreet and Experian. Budgetary proposal, valid 60 days. "
"Delivery 18-22 weeks after approval drawings, to be confirmed by production at time of order. Installation, foundations, utilities, permits, biogas H2S bulk removal in the digester, "
"LPG supply, digestate feed tank and its mixer, treatment and disposal of the liquid fraction, and any exhaust scrubber required by the air permit are by others. "
"Prices in US dollars, FOB Stuart, FL, exclusive of taxes and duties.")

LIQ = [
 ['', 'Screw press (base)', 'Decanter (option)'],
 ['Liquid fraction flow', '101 to 111 MT/day (4.2 to 4.6 m3/h)', '82 to 93 MT/day (3.4 to 3.9 m3/h)'],
 ['Solids capture assumed', '60 to 80%, no polymer', '70 to 90%'],
 ['Total solids in the liquid', '2.0 to 3.8%', '1.2 to 3.3%'],
 ['Ammoniacal nitrogen', 'about 3,500 mg/L', 'about 3,500 mg/L'],
 ['Chlorides', 'about 3,000 mg/L', 'about 3,000 mg/L'],
 ['pH', 'about 8', 'about 8'],
 ['Total N, COD, BOD, total P, oils and grease', 'by laboratory analysis', 'by laboratory analysis'],
]
LIQNOTE = ("Basis: 128.7 MT/day at 8% TS (10.3 MT/day of solids). Dissolved species (ammonia, chlorides) leave with the water at about the digestate concentration. "
"Total nitrogen will be at least the ammoniacal nitrogen plus the organic nitrogen carried on the uncaptured solids. Polymer raises solids capture and lowers the solids in the liquid. "
"The sample test will firm up these figures; we recommend the same sample be analysed for total N, COD, BOD, total P and oils and grease against the NOM-001 table.")

json.dump(dict(ref=REF, issue_date=ISSUE, expires=EXPIRES, subtotal=money(subtotal), skid=SKID, comments=comments, terms=terms,
               lines=lines, liquid=LIQ, liquid_note=LIQNOTE), open(HERE/'quote_data_revC.json', 'w'), indent=1)

OUT = HERE/('MCE_Quote_%s_Chicken_Manure_Dryer.pdf' % REF)
NAVY = colors.HexColor('#0b2a4a'); GREY = colors.HexColor('#555555')
def esc(t): return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
base = ParagraphStyle('b', fontName='Helvetica', fontSize=8.6, leading=11)
small = ParagraphStyle('s', parent=base, fontSize=7.8, leading=9.6, textColor=GREY)
h = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=NAVY, spaceBefore=8, spaceAfter=3)
title = ParagraphStyle('t', fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=NAVY)
right = ParagraphStyle('r', parent=base, alignment=TA_RIGHT)
im = Image.open(REPO/'renderer'/'assets'/'mce-logo.png').convert('RGBA'); im.thumbnail((240, 240))
bg = Image.new('RGB', im.size, 'white'); bg.paste(im, mask=im.split()[3]); lb = io.BytesIO(); bg.save(lb, 'JPEG', quality=60, optimize=True); lb.seek(0)
logo = RLImage(lb, width=1.9*inch, height=1.9*inch*im.size[1]/im.size[0])

def footer(c, doc):
    c.saveState(); c.setFont('Helvetica', 7); c.setFillColor(GREY)
    c.drawString(0.6*inch, 0.42*inch, 'Midwest Custom Engineering, Inc.  -  6526 S Kanner Hwy #215, Stuart, FL 34997  -  usemce.com')
    c.drawRightString(doc.pagesize[0]-0.6*inch, 0.42*inch, 'Quote %s  -  page %d' % (REF, doc.page)); c.restoreState()
doc = BaseDocTemplate(str(OUT), pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=0.55*inch, bottomMargin=0.65*inch,
                      title='MCE Quote %s - LETEK DCG' % REF, author='Midwest Custom Engineering, Inc.')
W = letter[0]-1.2*inch
doc.addPageTemplates([PageTemplate('p', [Frame(0.6*inch, 0.65*inch, W, letter[1]-1.2*inch, id='f')], onPage=footer)])
S = []
meta = Table([[logo, Paragraph('Quote', title)], ['', Table([[Paragraph('Quote ref.', small), Paragraph(REF, base)], [Paragraph('Issue date', small), Paragraph(ISSUE, base)],
      [Paragraph('Expires', small), Paragraph(EXPIRES, base)], [Paragraph('Revision', small), Paragraph('C (supersedes 20260917-LETEK-B)', base)]], colWidths=[0.8*inch, 1.8*inch])]], colWidths=[W-2.8*inch, 2.8*inch])
meta.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, -1), (-1, -1), 1.2, NAVY), ('BOTTOMPADDING', (0, -1), (-1, -1), 6)]))
S += [meta, Spacer(1, 6)]
party = Table([[Paragraph('<b>Seller</b>', base), Paragraph('<b>Buyer</b>', base)],
  [Paragraph('Midwest Custom Engineering, Inc.<br/>6526 S Kanner Hwy #215<br/>Stuart, FL 34997, United States<br/>Contact: Jason Shipley (jason@usemce.com), +1 620 200 9109', base),
   Paragraph('LETEK DCG<br/>Bosques de las Lomas, Mexico City, Mexico<br/>Contact: Bernardo Urquiza (burquiza@letekdcg.com)', base)]], colWidths=[W/2, W/2])
party.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')])); S += [party, Spacer(1, 4)]
S += [Paragraph('Chicken Manure Digestate Drying System - 128.7 MT/day - Budgetary Proposal, Rev C', h), Paragraph(esc(comments), base)]
S += [Paragraph('Design basis (MCE Dryer HMB Calculator, case MCE-HMB-2026-002 Rev C)', h), Paragraph('<br/>'.join(esc(x) for x in APP.splitlines()), base)]
S += [PageBreak(), Paragraph('Line items', h)]
rows = [[Paragraph('<b>#</b>', base), Paragraph('<b>Item</b>', base), Paragraph('<b>Qty</b>', right), Paragraph('<b>Unit price</b>', right), Paragraph('<b>Net</b>', right)]]
n = 0
for l in lines:
    opt = l['name'].startswith('OPTION'); n += 1
    up = 'TBD' if not l['unit'] else ('-' if l['unit'] < 0 else '') + '${:,.2f}'.format(abs(l['unit']))
    nt = up if l['unit'] else 'TBD'
    if opt: nt += '<br/><font size=7 color="#555555">not in total</font>'
    desc = '<br/>'.join(esc(x) for x in l['desc'].splitlines() if x.strip())
    rows.append([Paragraph(str(n), base), Paragraph('<b>%s</b><br/>%s' % (esc(l['name']), desc), base), Paragraph(str(l['qty']), right), Paragraph(up, right), Paragraph(nt, right)])
tot_label = 'Total (USD, FOB Stuart, FL)' + ('' if SKID else ', excluding the biogas skid allowance (line 8)')
rows.append(['', Paragraph('<b>%s</b>' % tot_label, right), '', '', Paragraph('<b>%s</b>' % money(subtotal), right)])
t = Table(rows, colWidths=[0.3*inch, W-3.1*inch, 0.45*inch, 1.15*inch, 1.2*inch], repeatRows=1)
t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, 0), 0.8, NAVY), ('LINEBELOW', (0, 1), (-1, -2), 0.3, colors.HexColor('#cccccc')),
  ('LINEABOVE', (0, -1), (-1, -1), 0.8, NAVY), ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8eef5')), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
S += [t]
lt = Table([[Paragraph(('<b>%s</b>' if i == 0 or j == 0 else '%s') % esc(c), base) for j, c in enumerate(r)] for i, r in enumerate(LIQ)], colWidths=[2.3*inch, (W-2.3*inch)/2, (W-2.3*inch)/2])
lt.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8eef5')), ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#cccccc'))]))
S += [KeepTogether([Paragraph('Liquid fraction from the dewatering step (treatment by others)', h), lt, Spacer(1, 3), Paragraph(esc(LIQNOTE), small)])]
S += [Paragraph('Terms', h), Paragraph(esc(terms), base), Spacer(1, 10),
      Paragraph('Accepted for LETEK DCG: ______________________________   Name: ____________________   Date: ____________', base)]
doc.build(S)
print('subtotal', money(subtotal), '| skid', SKID); print('written', OUT.name, OUT.stat().st_size, 'bytes')
