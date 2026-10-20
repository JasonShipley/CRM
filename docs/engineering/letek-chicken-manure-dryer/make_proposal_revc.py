"""LETEK Rev C budgetary proposal in the MCE Equipment Proposal template (as MCE-Q-2610-NBO3-R3): black header band,
proposal summary, design basis, numbered equipment sections, section totals, options and adders, furnished by others,
freight and schedule, commercial terms and sign-off. reportlab with the standard Helvetica fonts, so nothing is embedded
and the PDF stays small enough to e-mail. Pricing basis and open items are in README.md (Rev C sections).
The biogas skid allowance comes from skid_estimate.py; SKID=<dollars> overrides it. Writes quote_data_revC.json and the PDF."""
import io, json, os
from pathlib import Path
from PIL import Image
from reportlab import rl_config
rl_config.useA85 = 0   # binary streams: about 20% smaller than ASCII85
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import BaseDocTemplate, CondPageBreak, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle
import skid_estimate

HERE = Path(__file__).parent; REPO = HERE.parents[2]
REF = '20261019-LETEK-C'; ISSUE = 'October 19, 2026'
SUBTITLE = '128.7 MT/DAY CHICKEN MANURE DIGESTATE DRYING SYSTEM — MERIDA, YUCATAN'
SKID = float(os.environ['SKID']) if os.environ.get('SKID') else (float(skid_estimate.sell) if skid_estimate.sell else None)

SUMMARY = [
 ('PREPARED FOR', ['LETEK DCG', 'Attn: Bernardo Urquiza', 'Bosques de las Lomas, Mexico City, Mexico']),
 ('PROJECT', ['Dewatering and drying system for chicken manure digestate, 128.7 MT/day at 8% TS',
              'Screw press dewatering, XD-72 rotary drum dryer, biogas conditioning', '480V/3-phase/60Hz electrical', 'Ship to: Merida, Yucatan']),
 ('REFERENCE', [REF + ' (Rev C, supersedes 20260917-LETEK-B)',
                'Basis: Bernardo Urquiza (LETEK) process data of Sep 17 and Oct 13, 2026 and our call of Sep 29, 2026',
                'Validity: 60 days from date of issue · Currency: USD', 'FOB origin, MCE Stuart, FL or Newkirk, OK shop (per shop load)']),
]
INTRO = ("Midwest Custom Engineering is pleased to quote the dewatering and drying system for 128.7 MT/day of chicken manure digestate at 8% TS "
 "\u2014 two screw presses, an XD-72 rotary drum dryer with a 10 MMBtu/hr dual-fuel burner, a stainless cyclone and an exhaust fan on a VFD, "
 "controls, and a biogas conditioning skid carried as a budget allowance \u2014 with a reconditioned decanter centrifuge, 304 and 316L stainless "
 "drum systems (304 recommended) and a stainless exhaust stack offered as options. This is Rev C of the budgetary proposal; the press line is "
 "quoted subject to a test of a sample of your digestate.")

DESIGN = [
 ('Process', 'Liquid digestate › screw press › rotary drum dryer › dried product', 'Liquid fraction to LETEK treatment (NOM-001); biogas conditioned for the burner'),
 ('Feed', '128.7 MT/day at 8% TS', 'About 34,000 gal/day, 24 h/day, 350 days/year; grit and sand handled separately'),
 ('Dewatered cake', '3,153 lb/hr at 30% TS', 'Sized at full solids capture; 30 to 35% TS expected from the presses, about 20% from a decanter'),
 ('Dried product', '1,113 lb/hr (12.1 MT/day) at 15% moisture', 'About 7.3 to 9.7 MT/day at typical press capture without polymer; polymer raises capture'),
 ('Water evaporated', '2,040 lb/hr (245 gal/hr)', '3,616 lb/hr with the decanter option'),
 ('Thermal duty', '3.57 MMBtu/hr', 'Design value, conservative; detailed heat balance gives 3.24. 2.8 at 35% TS cake; 6.3 with the decanter option'),
 ('Fuel', 'Biogas, with LPG back-up', 'Biogas 145.8 MMBtu/day (about 6.1 MMBtu/hr average) covers about 170% of the duty'),
 ('Exhaust', '6,342 ACFM at 230°F, 12" WC', 'About 18 bhp at the fan shaft; 60 HP XF-36 fan on a VFD (item 4) also covers the decanter case; drum inlet gas 900°F'),
 ('Electrical', '480V/3-phase/60Hz', 'Site voltage to be confirmed'),
]
LIQ_HEAD = ['LIQUID FRACTION (TREATMENT BY OTHERS)', 'SCREW PRESS (BASE)', 'DECANTER (OPTION A)']
LIQ = [
 ['Liquid fraction flow', '101 to 111 MT/day (4.2 to 4.6 m³/h)', '82 to 93 MT/day (3.4 to 3.9 m³/h)'],
 ['Solids capture assumed', '60 to 80%, no polymer', '70 to 90%'],
 ['Total solids in the liquid', '2.0 to 3.8%', '1.2 to 3.3%'],
 ['Ammoniacal nitrogen', 'about 3,500 mg/L', 'about 3,500 mg/L'],
 ['Chlorides', 'about 3,000 mg/L', 'about 3,000 mg/L'],
 ['pH', 'about 8', 'about 8'],
 ['Total N, COD, BOD, total P, oils and grease', 'by laboratory analysis', 'by laboratory analysis'],
]
LIQNOTE = ("Basis: 128.7 MT/day at 8% TS (10.3 MT/day of solids), 30 to 35% TS press cake. Dissolved species (ammonia, chlorides) leave with the water at "
 "about the digestate concentration. Total nitrogen will be at least the ammoniacal nitrogen plus the organic nitrogen carried on the uncaptured solids. "
 "Polymer raises solids capture and lowers the solids in the liquid. The sample test will firm up these figures; we recommend the same sample be "
 "analysed for total N, COD, BOD, total P and oils and grease against the NOM-001 table.")

SECTIONS = [
 ('2A. DEWATERING', 'Dewatering', [
  dict(n=1, name='Screw Press Dewatering System – 2 Units, Subject to Sample Test', qty=1, unit=312500.0, bullets=[
   'Two screw presses in parallel, sized for about 35,000 gal/day of digestate at 8% TS, 0.5 mm screen, direct fed by the chopper pump',
   'Chopper feed pump and press drives on VFDs, basic control package; about 50 HP connected for the presses and pumps',
   'Expected cake 30 to 35% TS; lead time about 20 weeks',
   'Stainless steel throughout except the cast iron press bodies, which are kept for rigidity (stainless bodies flex and wear the screens and screws)',
   'Internal protective coating of the press bodies recommended for the chloride and ammonia in this digestate; confirmed and priced after the sample test',
   'Conditional on a test of a sample of your digestate, which confirms cake solids, solids capture and whether polymer is needed',
   'Good mixing ahead of the presses is essential: feed tank and mixer by others, mixer sized after the sample test; polymer make-up system, if needed, quoted after the test']),
 ]),
 ('2B. DRYER SYSTEM', 'Dryer System', [
  dict(n=2, name='XD-72 Mk.2 Rotary Thermal Conditioning System', qty=1, unit=489000.0, bullets=[
   'Heavy duty direct fired, co-current single pass rotary drum, 7 ft dia x 35 ft long, A36 steel (304 or 316L stainless priced as Options B and C; 304 recommended)',
   'Feed screw with 2 HP motor; the dewatering unit discharges by chute directly onto the feed screw',
   'Heavy duty drop-out box for dry product; airlock with 1.5 HP motor, drive and control devices, mild steel',
   'Drum drive on a structural base with 20 HP motor; full tooth chain sprocket; forged steel drum tracks; front and rear trunnion bases with hardened trunnion wheels and thrust wheel assembly',
   'Front and rear water deluge nozzles for fire suppression; inlet and discharge seals',
   'XF-36 exhaust fan, arrangement #9F, AR 235 rotor, 60 HP TEFC inverter-duty 230/460V/3-phase/60Hz (VFD, item 4), V-belt drive, 21" inlet, vibration isolation sleeve, inspection door, drain port',
   'Ducting, transitions and elbows up to 60 lineal feet, A36',
   'Basic burner management panel; electrical and control instrumentation for MCE equipment; motor control cabinet, 480V/3-phase/60Hz',
   'Manual quench nozzles; automated fire suppression quoted on request; the standard burner and valve train are replaced by the dual-fuel burner (item 3)',
   "Commissioning: 1 man-week; installation instructions for the buyer's contractors; start-up and operator training"]),
  dict(n=3, name='Dual-Fuel Burner Upgrade, 10 MMBtu/hr, LPG + Biogas', qty=1, unit=170000.0, bullets=[
   '10 MMBtu/hr maximum with 10:1 turndown; normal fire about 3.6 MMBtu/hr on press cake, with margin for wetter cake, LPG-only operation with the digester down, and the decanter option',
   'Dual-burner system: one LPG burner and one biogas burner, each with stainless combustor sleeve, integral combustion blower and filter, and independent air and gas actuators with position feedback',
   'Two NFPA 86 safety valve trains (LPG and flanged biogas) with dual safety shut-off valves, high and low gas pressure switches and gas meters; automatic changeover to LPG on loss of biogas',
   'Parallel-positioning air/fuel control with separate LPG and biogas fuel profiles, run in the PLC/HMI (item 8)',
   'Burner management panel, NEMA 4X fiberglass enclosure, two self-checking UV flame safeguards, high-temperature limits, combustion E-stop',
   'One week of combustion start-up and tuning on site']),
  dict(n=4, name='Exhaust Fan VFD, 60 HP', qty=1, unit=10395.0, bullets=[
   'Variable frequency drive for the XF-36 exhaust fan: 480V/3-phase/60Hz, variable-torque rated, NEMA 12 enclosure in the MCC with filtered forced-air cooling',
   'Lockable main breaker, control transformer, door keypad, Ethernet/Modbus link to the PLC',
   'Fan speed trimmed on drum outlet draft, so the exhaust airflow follows the drying load and can be capped at the cyclone maximum in the decanter case',
   'Programming included in item 8']),
  dict(n=5, name='HE-36 Cyclone', qty=1, unit=13570.0, bullets=[
   'Dryer exhaust collector, budget selection for 6,342 ACFM at 230°F (HE-36 operating range 6,175 to 7,600 CFM)',
   "Final cyclone picked with MCE's cyclone sizing calculator after the sample test, once cake solids and solids capture, and so the exhaust flow, are confirmed",
   '36" diameter, 25.5" x 10.75" tangential inlet, 10" flanged discharge, mount pads and inspection port; fines rejoin the dried product']),
  dict(n=6, name='HE-36 Cyclone – 304 Stainless Construction', qty=1, unit=8000.0, bullets=[
   '304 stainless construction of the cyclone for the wet, ammonia-laden dryer exhaust']),
  dict(n=7, name='FT-12 Airlock', qty=1, unit=12895.0, bullets=[
   'Rotary airlock under the cyclone discharge; fines rejoin the dried product']),
 ]),
 ('2C. CONTROLS', 'Controls', [
  dict(n=8, name='Automation and Controls (PLC / HMI)', qty=1, unit=89950.0, bullets=[
   'Required with the dual-fuel burner: the PLC hosts the parallel-positioning fuel profiles for LPG and biogas and the automatic changeover logic',
   'PLC programming of infeed, outfeed and product conveyance, burner modulation (BMS) and dryer temperature control; links to the dewatering unit, fan VFD, biogas skid and plant system',
   '21.5" HMI with modeled equipment interface, data logging of temperatures and component hours, visualization, e-mailed PDF reports and mobile data access',
   'On-site programming for 1 man-week; additional days at $1,350/day plus expenses']),
 ]),
 ('2D. BIOGAS CONDITIONING', 'Biogas Conditioning', [
  dict(n=9, name='Biogas Conditioning Skid, 500 ppm Inlet – Budget Allowance', qty=1, unit=SKID or 0.0, bullets=[
   'For 195 scfm (7,455 Nm³/day) of biogas at 500 ppm H2S or less (bulk H2S removal in the digester by others)',
   'Iron-oxide polishing vessels to under 100 ppm, gas cooler and moisture knockout, booster blower to 2 psig',
   'Inlet and outlet flame arresters, pressure control, inlet and outlet gas analyzers (CH4, H2S, O2)',
   'Local control panel linked to the burner BMS; first charge of iron-oxide media; process design MCE-LETEK-BGS-001',
   ('Budget allowance from our component estimate for this design (accuracy about +/-30%); firmed up into a fixed price once the biogas analysis is available'
    if SKID else 'Budget allowance to follow')]),
 ]),
]
OPTIONS = [
 dict(opt='A', name='Reconditioned Decanter Centrifuge and HE-47 304 SS Cyclone, in lieu of the screw presses and HE-36 cyclone (items 1, 5 and 6)', qty=1, unit=287450.0, net=-46620.0, bullets=[
  'If the sample test shows the solids are too fine for a screw press',
  'Reconditioned decanter centrifuge $262,500; HE-47 cyclone in 304 stainless for the higher airflow (range 10,825 to 12,600 CFM) $24,950',
  'Cake about 20% TS instead of 30 to 35%: dryer duty about 6.3 MMBtu/hr (biogas covers about 96%, the rest LPG) and exhaust about 11,200 ACFM; polymer is more likely to be needed',
  'Availability and lead time confirmed when a specific reconditioned unit is selected']),
 dict(opt='B', name='RECOMMENDED: 304 Stainless Steel Drum System, in lieu of the A36 drum system (item 2)', qty=1, unit=847000.0, net=358000.0, bullets=[
  '304 stainless drum shell and flights, feed screw, drop-out box and airlock in place of A36',
  'Our recommended balance of cost and service life for this digestate (ammonia, chlorides, pH about 8); estimated shell life of 3/8" A36 on this service is 7 to 10 years',
  'Stainless pricing subject to mill prices at order']),
 dict(opt='C', name='316L Stainless Steel Drum System, in lieu of the A36 drum system (item 2) – alternative to Option B', qty=1, unit=911500.0, net=422500.0, bullets=[
  'Same scope as Option B, in 316L: the molybdenum gives better resistance to chloride pitting (about 3,000 mg/L chlorides in this digestate)',
  '$64,500 more than Option B; stainless pricing subject to mill prices at order']),
 dict(opt='D', name='Exhaust Stack, 304 Stainless', qty=1, unit=23500.0, net=23500.0, bullets=[
  '24" OD, 10 ga welded-seam flanged sections; discharge about 35 ft above grade (final height set at approval drawings once the cyclone is selected)',
  'Fan outlet transition and side-inlet tee; base stand with base plate and condensate drain; open vertical discharge',
  'Two 4" sampling ports at 90° located to EPA Method 1, plus a thermocouple port; guy ring with three guy wires and turnbuckles; stainless bolting',
  'Sized for both the press and decanter cases (about 2,100 to 3,700 fpm exit velocity); foundation, anchors, sampling platform and ladder, and installation by others']),
]
BY_OTHERS = [
 'Anaerobic digester, bulk H2S removal in the digester, and the biogas and LPG supply to the skid and burner',
 'Digestate feed tank and its mixer; polymer make-up system if the sample test shows it is needed (quoted after the test)',
 'Treatment and disposal of the liquid fraction to the NOM-001 limits',
 'Dried product storage and bagging; quench and fire water supply',
 'Exhaust scrubber, if the air permit requires one; exhaust stack unless Option D is taken',
 'Buildings, concrete and foundations, and structural support for the equipment',
 'Installation, millwright and electrical labor, and site labor for start-up beyond the MCE commissioning, combustion start-up and programming in items 2, 3 and 8; utilities',
 'Permits, including the air permit',
]
FREIGHT = [
 ('Freight', 'FOB origin, MCE Stuart, FL or Newkirk, OK shop (assigned at order based on shop load and demand); freight door to door to Merida quoted at time '
             'of shipment, or shipped freight collect. The April 2026 estimate for a comparable shipment from Stuart was about $27,000.'),
 ('Delivery', '18 to 22 weeks after approval drawings, to be confirmed by production at time of order.'),
 ('Sample test', 'The screw press line is conditional on a test of a sample of the digestate (about 20 litres); the same test confirms cake solids, solids capture and polymer for the decanter route (Option A), and the sample can be analysed for the NOM-001 parameters.'),
 ('Approval drawings', 'General arrangement drawings and plant layout issued for LETEK approval before fabrication.'),
 ('Installation', 'By others. Included: 1 man-week of dryer commissioning (item 2), one week of combustion start-up (item 3) and 1 man-week of on-site '
                  'programming (item 8; additional programming days at $1,350/day plus expenses). Additional commissioning or start-up days quoted on request.'),
]
TERMS = ("Payment: 50% down with order, 30% on approval drawings, 15% before shipment, 5% on start-up. Payment terms are as stated on this quote and on "
 "the invoice. Past-due balances may be reported to business credit bureaus, including Dun & Bradstreet and Experian. Prices are in US dollars and "
 "exclude taxes, duties, freight and installation. This is a budgetary proposal, valid 60 days from the date of issue; stainless options are subject "
 "to mill prices at order. Warranty per MCE standard terms and conditions.")

def money(v): return ('-' if v < 0 else '') + '${:,.2f}'.format(abs(v))
items = [it for _, _, its in SECTIONS for it in its]
TOTAL = sum(it['qty'] * it['unit'] for it in items)
REC_TOTAL = TOTAL + OPTIONS[1]['net']
json.dump(dict(ref=REF, issue_date=ISSUE, total=money(TOTAL), total_with_option_B=money(REC_TOTAL), skid=SKID, summary=SUMMARY, intro=INTRO,
               design=DESIGN, liquid=[LIQ_HEAD] + LIQ, liquid_note=LIQNOTE, sections=SECTIONS, options=OPTIONS, by_others=BY_OTHERS,
               freight=FREIGHT, terms=TERMS), open(HERE/'quote_data_revC.json', 'w'), indent=1)

# ---- page furniture (MCE Equipment Proposal template) ----
OUT = HERE/'MCE_Proposal_-_LETEK_DCG_-_Merida_128.7MTD_Digestate_Dryer_RevC.pdf'
PW, PH = letter; LM = 0.5*inch; W = PW - 2*LM
INK = colors.HexColor('#1A1A1A'); BAR = colors.HexColor('#262626'); ORANGE = colors.HexColor('#F26A10')
GREY = colors.HexColor('#666666'); LIGHT = colors.HexColor('#9A9A9A'); RULE = colors.HexColor('#D9D9D9'); BOX = colors.HexColor('#F2F2F2')
body = ParagraphStyle('body', fontName='Helvetica', fontSize=8.4, leading=11.6, textColor=INK)
bold = ParagraphStyle('bold', parent=body, fontName='Helvetica-Bold')
bul = ParagraphStyle('bul', parent=body, fontSize=8.4, leading=12, leftIndent=11, bulletIndent=2, spaceBefore=0.8, bulletFontSize=6)
lab = ParagraphStyle('lab', fontName='Helvetica-Bold', fontSize=6.6, leading=8, textColor=GREY)
labr = ParagraphStyle('labr', parent=lab, alignment=TA_RIGHT); labc = ParagraphStyle('labc', parent=lab, alignment=TA_CENTER)
num = ParagraphStyle('num', parent=body, alignment=TA_RIGHT); numc = ParagraphStyle('numc', parent=body, alignment=TA_CENTER)
numb = ParagraphStyle('numb', parent=bold, alignment=TA_RIGHT)
bar_l = ParagraphStyle('barl', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.white)
bar_r = ParagraphStyle('barr', fontName='Helvetica-Oblique', fontSize=7.4, leading=11, textColor=colors.HexColor('#CFCFCF'), alignment=TA_RIGHT)
note = ParagraphStyle('note', fontName='Helvetica-Oblique', fontSize=7.6, leading=10, textColor=GREY, alignment=TA_RIGHT)
small = ParagraphStyle('small', parent=body, fontSize=7.6, leading=10, textColor=GREY)

im = Image.open(REPO/'renderer'/'assets'/'mce-logo.png').convert('RGBA'); im.thumbnail((300, 300))
flat = Image.new('RGB', im.size, 'black'); flat.paste(im, mask=im.split()[3])     # logo on the black band, stored as JPEG
lb = io.BytesIO(); flat.save(lb, 'JPEG', quality=85); lb.seek(0); LOGO = ImageReader(lb)

def page(c, doc):
    c.saveState()
    top = PH - 0.08*inch; band = 1.11*inch
    c.setFillColor(colors.black); c.rect(0, top - band, PW, band, stroke=0, fill=1)
    c.setFillColor(ORANGE); c.rect(0, top - band - 0.045*inch, PW, 0.045*inch, stroke=0, fill=1)
    lw = 1.82*inch; lh = lw * im.size[1] / im.size[0]
    c.drawImage(LOGO, 0.55*inch, top - band/2 - lh/2, width=lw, height=lh)
    c.setFillColor(colors.white); c.setFont('Helvetica-Bold', 20); c.drawRightString(PW - LM, top - 0.43*inch, 'EQUIPMENT PROPOSAL')
    c.setFillColor(ORANGE); c.setFont('Helvetica-Bold', 7.4); c.drawRightString(PW - LM, top - 0.64*inch, SUBTITLE)
    c.setFillColor(colors.white); c.setFont('Helvetica', 6.6)
    c.drawRightString(PW - LM, top - 0.82*inch, f'Proposal {REF} · {ISSUE} · Page {doc.page}')
    c.setStrokeColor(RULE); c.setLineWidth(0.6); c.line(LM, 0.5*inch, PW - LM, 0.5*inch)
    c.setStrokeColor(ORANGE); c.setLineWidth(2); c.line(LM, 0.33*inch, LM + 0.17*inch, 0.33*inch)
    c.setFillColor(colors.HexColor('#555555')); c.setFont('Helvetica-Bold', 6.4); c.drawString(LM + 0.27*inch, 0.31*inch, 'MIDWEST CUSTOM ENGINEERING')
    x = LM + 0.27*inch + c.stringWidth('MIDWEST CUSTOM ENGINEERING', 'Helvetica-Bold', 6.4) + 7
    c.setFillColor(LIGHT); c.setFont('Helvetica', 6.4); c.drawString(x, 0.31*inch, 'PRECISION. QUALITY. INTEGRITY.')
    c.drawRightString(PW - LM, 0.31*inch, 'Stuart, FL · 772-200-4060 · midwestcustomengineering.com')
    c.restoreState()

import re
def esc(t):   # escape, keep 'item 5' / 'Option B' together, and draw the process arrows from the base-14 Symbol font
    t = str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = re.sub(r'\b(items?|Options?) (?=[0-9A-D]\b)', r'\1&nbsp;', t)
    return t.replace(' › ', ' <font name="Symbol">\u2192</font> ')
def bar(left, right=''):
    t = Table([['', Paragraph(esc(left), bar_l), Paragraph(esc(right), bar_r)]], colWidths=[0.06*inch, W*0.6, W*0.4 - 0.06*inch], rowHeights=[0.25*inch])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), ORANGE), ('BACKGROUND', (1, 0), (-1, 0), BAR), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('LEFTPADDING', (1, 0), (1, 0), 10), ('RIGHTPADDING', (2, 0), (2, 0), 8), ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))
    return t
def ruled(rows, widths, head=True, pad=5):
    t = Table(rows, colWidths=widths, repeatRows=1 if head else 0)
    st = [('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, -1), 0.6, RULE), ('LEFTPADDING', (0, 0), (-1, -1), 6),
          ('RIGHTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), pad), ('BOTTOMPADDING', (0, 0), (-1, -1), pad + 1)]
    if head: st += [('TOPPADDING', (0, 0), (-1, 0), 6), ('BOTTOMPADDING', (0, 0), (-1, 0), 5)]
    t.setStyle(TableStyle(st)); return t
def cell(title, bullets):
    return [Paragraph(esc(title), bold)] + [Paragraph(esc(b), bul, bulletText='•') for b in bullets]

S = [Spacer(1, 2), bar('PROPOSAL SUMMARY')]
summ = Table([[Paragraph(h, lab) for h, _ in SUMMARY], [[Paragraph(esc(x), body) for x in v] for _, v in SUMMARY]], colWidths=[W/3]*3)
summ.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), BOX), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 12),
                          ('RIGHTPADDING', (0, 0), (-1, -1), 10), ('TOPPADDING', (0, 0), (-1, 0), 10), ('BOTTOMPADDING', (0, -1), (-1, -1), 12)]))
S += [summ, Spacer(1, 10), Paragraph(esc(INTRO), body), Spacer(1, 10)]

S += [bar('1. DESIGN BASIS', 'MCE Dryer HMB Calculator, MCE-HMB-2026-002 Rev C')]
S += [ruled([[Paragraph(x, lab) for x in ('PARAMETER', 'DESIGN VALUE', 'NOTES')]] +
            [[Paragraph(esc(p), bold), Paragraph(esc(v), bold), Paragraph(esc(n), body)] for p, v, n in DESIGN], [1.45*inch, 2.25*inch, W - 3.7*inch]), Spacer(1, 8)]
liq = ruled([[Paragraph(x, lab) for x in LIQ_HEAD]] + [[Paragraph(esc(r[0]), bold)] + [Paragraph(esc(x), body) for x in r[1:]] for r in LIQ]
            + [[Paragraph(esc(LIQNOTE), small), '', '']], [2.3*inch, (W - 2.3*inch)/2, (W - 2.3*inch)/2], pad=3.5)
liq.setStyle(TableStyle([('SPAN', (0, -1), (-1, -1))]))
S += [liq, Spacer(1, 10)]

IW = [0.42*inch, W - 2.96*inch, 0.5*inch, 1.02*inch, 1.02*inch]   # template column geometry
for title, short, its in SECTIONS:
    rows = [[Paragraph(x, s) for x, s in (('ITEM', lab), ('DESCRIPTION', lab), ('QTY', labr), ('UNIT PRICE', labr), ('EXTENDED', labr))]]
    for it in its:
        rows.append([Paragraph(str(it['n']), bold), cell(it['name'], it['bullets']), Paragraph(str(it['qty']), num),
                     Paragraph(money(it['unit']), num), Paragraph(money(it['qty'] * it['unit']), num)])
    need = ruled(rows[:2], IW, pad=6).wrap(W, PH)[1] + 0.4*inch          # keep the bar with the header and first item
    S += [CondPageBreak(need), bar(title, 'USD · taxes and freight excluded'), ruled(rows, IW, pad=6), Spacer(1, 10)]

def span(its): return f"item {its[0]['n']}" if len(its) == 1 else f"items {its[0]['n']}–{its[-1]['n']}"
trows = [[Paragraph(f'{short} – {span(its)}', body), Paragraph(money(sum(i['qty'] * i['unit'] for i in its)), num)] for _, short, its in SECTIONS]
trows.append([Paragraph('<b>Total — priced lines as quoted</b>', body), Paragraph(money(TOTAL), numb)])
tt = Table(trows, colWidths=[3.25*inch, 1.4*inch], hAlign='RIGHT')
tt.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -2), 0.6, RULE), ('LINEABOVE', (0, -1), (-1, -1), 0.9, INK), ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 7), ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6)]))
S += [KeepTogether([tt, Spacer(1, 4), Paragraph(f'Options and freight are not included in this total. With the recommended 304 stainless drum system (Option B): {money(REC_TOTAL)}.', note)]), Spacer(1, 14)]

orows = [[Paragraph(x, s) for x, s in (('OPT', lab), ('DESCRIPTION', lab), ('QTY', labr), ('UNIT PRICE', labr), ('NET ADDER', labr))]]
for o in OPTIONS:
    orows.append([Paragraph(o['opt'], bold), cell(o['name'], o['bullets']), Paragraph(str(o['qty']), num), Paragraph(money(o['unit']), num), Paragraph(money(o['net']), num)])
S += [CondPageBreak(ruled(orows[:2], IW, pad=6).wrap(W, PH)[1] + 0.4*inch), bar('OPTIONS AND ADDERS', 'Not included in the total'), ruled(orows, IW, pad=6), Spacer(1, 10)]

S += [KeepTogether([bar('3. FURNISHED BY OTHERS'), Spacer(1, 4)] + [Paragraph(esc(b), bul, bulletText='•') for b in BY_OTHERS]), Spacer(1, 12)]
S += [CondPageBreak(1.6*inch), bar('4. FREIGHT, DELIVERY AND SCHEDULE'),
       ruled([[Paragraph('ITEM', lab), Paragraph('BASIS', lab)]] + [[Paragraph(esc(a), bold), Paragraph(esc(b), body)] for a, b in FREIGHT], [2.85*inch, W - 2.85*inch]), Spacer(1, 12)]
sig = Table([[Paragraph('PREPARED BY', lab), Paragraph('FOR LETEK DCG', lab)],
             [[Paragraph('<b>Jason Shipley</b>', body), Paragraph('President, Midwest Custom Engineering, Inc.', body),
               Paragraph('jason@usemce.com · 772-200-4060 · cell 620-200-9109', body)],
              [Paragraph('Accepted: ________________________________', body), Spacer(1, 10), Paragraph('Name / Title: _____________________________', body),
               Spacer(1, 10), Paragraph('Date: _________________   PO #: _________________', body)]]], colWidths=[W*0.52, W*0.48])
sig.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 1), (-1, 1), 5)]))
S += [KeepTogether([bar('5. COMMERCIAL TERMS'), Spacer(1, 6), Paragraph(esc(TERMS), body), Spacer(1, 14), sig])]

doc = BaseDocTemplate(str(OUT), pagesize=letter, leftMargin=LM, rightMargin=LM, topMargin=1.42*inch, bottomMargin=0.68*inch,
                      title=f'MCE Proposal {REF} - LETEK DCG - Chicken Manure Digestate Dryer', author='Midwest Custom Engineering, Inc.')
doc.addPageTemplates([PageTemplate('p', [Frame(LM, 0.68*inch, W, PH - 2.1*inch, id='f', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=page)])
doc.build(S)
print('total', money(TOTAL), '| with option B', money(REC_TOTAL), '| skid', SKID)
print('written', OUT.name, OUT.stat().st_size, 'bytes')
