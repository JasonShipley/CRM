"""LETEK Rev C process flow diagram (MCE-LETEK-PFD-001 Rev C): whole plant from digester to stack, screw press base and
decanter option, with the stream table. Writes pfd_revC.html and prints MCE-LETEK-PFD-001_RevC_Process_Flow.pdf with headless
Chromium. Dryer streams are the MCE Dryer HMB Calculator runs (case_letek_revC_press30.json, case_letek_revC_decanter20.json,
full solids capture); liquid fraction ranges, biogas and equipment match quote 20261019-LETEK-C."""
import base64, io, pathlib, subprocess
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
DOC = 'MCE-LETEK-PFD-001'; REV = 'C'; DATE = 'Oct 19, 2026'; QREF = '20261019-LETEK-C'
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

# Basis: 128.7 MT/day at 8% TS
FEED_LBHR = 128.7 * 2204.62 / 24          # 11,822 lb/hr
SOLIDS = FEED_LBHR * 0.08                 # 946 lb/hr
PRODUCT, PRODUCT_WATER = 1113, 167        # lb/hr at 15% moisture, both cases (HMB)
CASE = {  # HMB calculator outputs, full solids capture
 'press': dict(name='Screw press (base)', ts=0.30, cake=3153, evap=2040, duty=3.57, rig=3.24, acfm=6342, bhp=18.4,
               comb=821, makeup=2797, inlet=3651, lpg_alone=179, cyclone='HE-36', liq_mtd='101 to 111', cap='60 to 80%, no polymer, 30 to 35% TS cake',
               liq_ts='2.0 to 3.8%'),
 'dec':   dict(name='Decanter (option)', ts=0.20, cake=4729, evap=3616, duty=6.33, rig=5.70, acfm=11242, bhp=32.7,
               comb=1456, makeup=4958, inlet=6471, lpg_alone=318, cyclone='HE-47', liq_mtd='82 to 93', cap='70 to 90%',
               liq_ts='1.2 to 3.3%'),
}
BIOGAS_SCFM, BIOGAS_MMBTU_HR = 195, 145.77 / 24      # 6.07 MMBtu/hr average
LPG_BTU_LB = 19900

def f(v, d=0): return f'{v:,.{d}f}'

for c in CASE.values():
    c['water_in'] = c['cake'] - SOLIDS
    c['liq_full'] = FEED_LBHR - c['cake']
    c['bg_scfm'] = min(BIOGAS_SCFM, BIOGAS_SCFM * c['duty'] / BIOGAS_MMBTU_HR)
    c['lpg_makeup'] = max(0.0, c['duty'] - BIOGAS_MMBTU_HR) * 1e6 / LPG_BTU_LB
    c['cover'] = BIOGAS_MMBTU_HR / c['duty']
P, D = CASE['press'], CASE['dec']
assert abs((P['cake'] - PRODUCT) - P['evap']) < 2 and abs((D['cake'] - PRODUCT) - D['evap']) < 2   # water balance closes

im = Image.open(REPO/'renderer'/'assets'/'mce-logo.png').convert('RGBA'); im.thumbnail((520, 520))
buf = io.BytesIO(); im.save(buf, 'PNG'); LOGO = base64.b64encode(buf.getvalue()).decode()

def sm(n, x, y):  # stream marker
    return (f'<g class="sm"><rect x="{x-8}" y="{y-8}" width="16" height="16" transform="rotate(45 {x} {y})"/>'
            f'<text x="{x}" y="{y+3.5}">{n}</text></g>')

SVG = f"""<svg viewBox="0 0 1040 520" xmlns="http://www.w3.org/2000/svg" font-family="Inter, Liberation Sans, Arial, sans-serif">
<defs>
 <marker id="ak" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#141617"/></marker>
 <marker id="ab" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#1F6FB2"/></marker>
 <marker id="ao" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#E35A00"/></marker>
</defs>
<style>
 .eq{{fill:#fff;stroke:#141617;stroke-width:1.6}} .oth{{fill:#F5F5F5;stroke:#8A8F90;stroke-width:1.2;stroke-dasharray:5 3}}
 .t{{font-size:10.5px;fill:#141617}} .tb{{font-size:11px;font-weight:600;fill:#141617}} .ts{{font-size:9px;fill:#575D5E}}
 .tag{{font-size:9.5px;font-weight:700;fill:#E35A00;letter-spacing:.04em}}
 .ln{{fill:none;stroke:#141617;stroke-width:2}} .gas{{fill:none;stroke:#1F6FB2;stroke-width:2}} .fuel{{fill:none;stroke:#E35A00;stroke-width:2}}
 .sm rect{{fill:#141617}} .sm text{{font-size:9px;font-weight:700;fill:#fff;text-anchor:middle}}
 .mid{{text-anchor:middle}} .end{{text-anchor:end}}
</style>

<!-- digester and biogas -->
<rect class="oth" x="12" y="18" width="134" height="62" rx="6"/>
<text class="tb mid" x="79" y="44">Anaerobic digester</text><text class="ts mid" x="79" y="58">existing, by others</text>
<text class="ts mid" x="79" y="70">bulk H2S removal by others</text>
<path class="fuel" d="M146 36 H268" marker-end="url(#ao)"/>{sm(4, 207, 36)}
<text class="ts mid" x="207" y="25">raw biogas</text>
<rect class="eq" x="270" y="12" width="196" height="58" rx="3"/>
<text class="tag" x="280" y="27">BGS-001</text><text class="tb" x="280" y="41">Biogas conditioning skid</text>
<text class="ts" x="280" y="54">iron oxide H2S polish, cooler/knockout,</text><text class="ts" x="280" y="65">blower to 2 psig, flame arresters, analyzers</text>
<path class="fuel" d="M466 36 H505 V188" marker-end="url(#ao)"/>{sm(5, 505, 110)}
<path class="fuel" d="M505 36 V14 H600" marker-end="url(#ao)"/>
<text class="ts" x="604" y="11">surplus biogas to flare /</text><text class="ts" x="604" y="22">other users (by others)</text>

<!-- LPG -->
<rect class="oth" x="560" y="104" width="112" height="40" rx="6"/>
<text class="tb mid" x="616" y="121">LPG supply</text><text class="ts mid" x="616" y="134">by others</text>
<path class="fuel" d="M575 144 V188" marker-end="url(#ao)"/>{sm(6, 575, 166)}

<!-- burner -->
<rect class="eq" x="462" y="190" width="120" height="58" rx="3"/>
<text class="tag" x="470" y="205">B-101</text><text class="tb" x="470" y="219">Dual-fuel burner</text>
<text class="ts" x="470" y="231">10 MMBtu/hr, LPG + biogas</text><text class="ts" x="470" y="242">10:1 turndown</text>
<path class="gas" d="M380 202 H460" marker-end="url(#ab)"/><text class="t end" x="376" y="205">Combustion air</text>{sm(7, 418, 202)}
<path class="gas" d="M380 236 H460" marker-end="url(#ab)"/><text class="t end" x="376" y="239">Make-up air</text>{sm(8, 418, 236)}

<!-- drum -->
<path class="eq" d="M600 186 H812 Q822 186 822 196 V240 Q822 250 812 250 H600 Q590 250 590 240 V196 Q590 186 600 186Z"/>
<rect x="606" y="182" width="8" height="72" fill="#575D5E"/><rect x="800" y="182" width="8" height="72" fill="#575D5E"/>
<path class="ln" d="M582 219 H590"/>
<text class="tag" x="626" y="204">D-101</text><text class="tb" x="626" y="218">XD-72 Mk.2 rotary drum</text>
<text class="ts" x="626" y="231">7 ft x 35 ft, co-current, single pass</text><text class="ts" x="626" y="242">900 F in / 230 F out</text>
{sm(9, 636, 172)}

<!-- drop-out box -->
<path class="eq" d="M824 168 H892 V262 L868 292 H848 L824 262Z"/>
<text class="tag" x="830" y="184">DB-101</text><text class="ts" x="830" y="197">drop-out</text><text class="ts" x="830" y="208">box</text>
<circle class="eq" cx="858" cy="306" r="11"/><text class="tag" x="874" y="309">RV-101</text>
<path class="ln" d="M858 292 V295"/>
<path class="ln" d="M858 317 V436" marker-end="url(#ak)"/>{sm(10, 858, 352)}
<rect class="oth" x="790" y="438" width="170" height="44" rx="6"/>
<text class="tb mid" x="875" y="456">Dried product, 15% moisture</text><text class="ts mid" x="875" y="470">to storage / bagging (by others)</text>

<!-- exhaust: drop-out box to cyclone, fan, stack -->
<path class="gas" d="M858 168 V112 H912" marker-end="url(#ab)"/>{sm(11, 880, 112)}
<path class="eq" d="M914 100 H954 V156 L940 206 H928 L914 156Z"/>
<text class="tag end" x="908" y="150">CY-101</text><text class="ts end" x="908" y="162">cyclone</text>
<circle class="eq" cx="934" cy="219" r="9"/><text class="tag" x="948" y="222">RV-102</text>
<path class="ln" d="M934 206 V210"/>
<path class="ln" d="M934 228 V400 H860" marker-end="url(#ak)"/>{sm(12, 934, 330)}
<text class="ts" x="940" y="378">fines rejoin</text><text class="ts" x="940" y="389">the product</text>
<path class="gas" d="M934 100 V64 H970" marker-end="url(#ab)"/>
<circle class="eq" cx="986" cy="64" r="15"/><path d="M993 64 L981 56 L981 72Z" fill="#141617"/>
<text class="tag" x="972" y="94">F-101</text><text class="ts" x="963" y="105">XF-36, 60 HP</text>
<rect class="eq" x="1012" y="8" width="16" height="64"/><path class="gas" d="M1001 64 H1012"/>
<text class="tag end" x="1008" y="20">ST-101</text>{sm(13, 1020, 84)}

<!-- feed and dewatering -->
<path class="ln" d="M60 80 V300" marker-end="url(#ak)"/>{sm(1, 60, 190)}
<text class="ts" x="70" y="160">liquid digestate</text><text class="ts" x="70" y="171">128.7 MT/day, 8% TS</text>
<path class="oth" d="M18 302 H112 V378 Q112 388 102 388 H28 Q18 388 18 378Z"/>
<path d="M65 296 V350 M52 350 H78" stroke="#8A8F90" stroke-width="2"/>
<text class="tb mid" x="65" y="402">Feed tank + mixer</text><text class="ts mid" x="65" y="414">by others</text>
<path class="ln" d="M112 360 H146"/>
<circle class="eq" cx="160" cy="360" r="13"/><path d="M167 360 L154 352 L154 368Z" fill="#141617"/>
<text class="ts mid" x="160" y="386">feed pump</text>
<path class="ln" d="M173 360 H206" marker-end="url(#ak)"/>
<rect class="eq" x="208" y="326" width="150" height="66" rx="3"/>
<text class="tag" x="216" y="341">SP-101/102</text><text class="tb" x="216" y="355">2 x screw press</text>
<text class="ts" x="216" y="368">option: reconditioned</text><text class="ts" x="216" y="379">decanter centrifuge</text>
<path class="ln" d="M358 340 H402 V272 H430" marker-end="url(#ak)"/>{sm(2, 380, 340)}
<text class="ts" x="366" y="328">cake</text>
<rect class="eq" x="432" y="262" width="166" height="20" rx="2"/>
<text class="tag" x="440" y="276">SC-101</text><text class="ts" x="486" y="276">dryer feed screw</text>
<path class="ln" d="M598 262 V252" marker-end="url(#ak)"/>
<path class="ln" d="M283 392 V436" marker-end="url(#ak)"/>{sm(3, 283, 414)}
<rect class="oth" x="178" y="438" width="210" height="44" rx="6"/>
<text class="tb mid" x="283" y="456">Liquid fraction</text><text class="ts mid" x="283" y="470">to treatment to NOM-001 (by others)</text>

<!-- why the exhaust changes -->
<rect x="420" y="306" width="350" height="134" rx="4" fill="#FFF1E8" stroke="#E35A00" stroke-width="1"/>
<text class="tb" x="432" y="325">Why the exhaust airflow depends on the dewatering route</text>
<text class="t" x="432" y="343">The decanter has no air stream of its own. The airflow is the dryer</text>
<text class="t" x="432" y="357">exhaust (stream 11): combustion gas, make-up air and the water</text>
<text class="t" x="432" y="371">evaporated from the cake. Decanter cake is wetter (20% vs 30% TS),</text>
<text class="t" x="432" y="385">so the dryer evaporates {f(D['evap'])} instead of {f(P['evap'])} lb/hr of water, and</text>
<text class="t" x="432" y="399">the burner fires {D['duty']:.1f} instead of {P['duty']:.1f} MMBtu/hr, which takes more air.</text>
<text class="t" x="432" y="413">Exhaust rises from {f(P['acfm'])} to {f(D['acfm'])} ACFM, so the cyclone steps up</text>
<text class="t" x="432" y="427">from an {P['cyclone']} to an {D['cyclone']}. The 7 ft drum and 60 HP fan cover both.</text>

<!-- legend -->
<g transform="translate(420 458)">
 <path class="ln" d="M0 6 H26"/><text class="ts" x="32" y="9">solids / liquid</text>
 <path class="gas" d="M112 6 H138"/><text class="ts" x="144" y="9">air / gas</text>
 <path class="fuel" d="M206 6 H232"/><text class="ts" x="238" y="9">fuel gas</text>
 <rect class="oth" x="296" y="0" width="22" height="12" rx="2"/><text class="ts" x="324" y="9">by others</text>
 <g transform="translate(0 20)"><rect x="-6" y="-6" width="12" height="12" transform="rotate(45)" fill="#141617"/><text class="ts" x="14" y="4">stream number, see stream table</text></g>
</g>
</svg>"""

def row(n, desc, a, b, cls=''):
    return f'<tr class="{cls}"><td class="n">{n}</td><td>{desc}</td><td>{a}</td><td>{b}</td></tr>'

ROWS = ''.join([
 row(1, 'Liquid digestate to dewatering', f'{f(FEED_LBHR)} lb/hr (128.7 MT/day, about 34,000 gal/day), 8% TS, {f(SOLIDS)} lb/hr solids', 'same'),
 row(2, 'Dewatered cake to dryer (design: full solids capture)', f"{f(P['cake'])} lb/hr at 30% TS ({f(P['water_in'])} lb/hr water)", f"{f(D['cake'])} lb/hr at 20% TS ({f(D['water_in'])} lb/hr water)"),
 row(3, 'Liquid fraction to treatment (by others)', f"{P['liq_mtd']} MT/day at typical capture ({P['cap']}), {P['liq_ts']} TS. "
     f"{f(P['liq_full'])} lb/hr ({f(P['liq_full']*24/2204.62,1)} MT/day) at full capture", f"{D['liq_mtd']} MT/day at typical capture ({D['cap']}), {D['liq_ts']} TS. "
     f"{f(D['liq_full'])} lb/hr ({f(D['liq_full']*24/2204.62,1)} MT/day) at full capture"),
 row(4, 'Raw biogas from digester', f'{BIOGAS_SCFM} scfm (7,455 Nm3/day), 55% CH4, 500 ppm H2S or less; {BIOGAS_MMBTU_HR:.2f} MMBtu/hr average', 'same'),
 row(5, 'Conditioned biogas to burner (H2S under 100 ppm, 2 psig)', f"about {f(P['bg_scfm'])} scfm ({P['duty']:.2f} MMBtu/hr); about {f(BIOGAS_SCFM-P['bg_scfm'])} scfm surplus to flare / other users",
     f"all {BIOGAS_SCFM} scfm ({BIOGAS_MMBTU_HR:.2f} MMBtu/hr, covers about {D['cover']:.0%} of the duty)"),
 row(6, 'LPG to burner (start-up, make-up, digester down)', f"none at average biogas; {f(P['lpg_alone'])} lb/hr on LPG alone",
     f"about {f(D['lpg_makeup'])} lb/hr make-up at average biogas; {f(D['lpg_alone'])} lb/hr on LPG alone"),
 row(7, 'Combustion air, 85 F', f"{f(P['comb'])} ACFM", f"{f(D['comb'])} ACFM"),
 row(8, 'Make-up (dilution) air, 85 F', f"{f(P['makeup'])} SCFM", f"{f(D['makeup'])} SCFM"),
 row(9, 'Mixed gas into drum, 900 F', f"{f(P['inlet'])} SCFM", f"{f(D['inlet'])} SCFM"),
 row(10, 'Dried product, 180 F', f'{f(PRODUCT)} lb/hr at 15% moisture ({f(SOLIDS)} solids + {PRODUCT_WATER} water); 12.1 MT/day at full capture', 'same'),
 row(11, 'Dryer exhaust to cyclone, 230 F', f"<b>{f(P['acfm'])} ACFM</b>, carrying {f(P['evap'])} lb/hr evaporated water", f"<b>{f(D['acfm'])} ACFM</b>, carrying {f(D['evap'])} lb/hr evaporated water"),
 row(12, 'Cyclone fines (rejoin product)', 'included in stream 10', 'included in stream 10'),
 row(13, 'Exhaust to stack', f"{f(P['acfm'])} ACFM at about 230 F; 12 in WC fan static, about {P['bhp']:.0f} bhp", f"{f(D['acfm'])} ACFM; about {D['bhp']:.0f} bhp"),
 row('', '<b>Dryer duty</b> (MCE basis / rigorous)', f"{P['duty']:.2f} / {P['rig']:.2f} MMBtu/hr", f"{D['duty']:.2f} / {D['rig']:.2f} MMBtu/hr", 'sum'),
 row('', '<b>Cyclone</b> (MCE cyclone calculator)', f"{P['cyclone']}, range 6,175 to 7,600 CFM", f"{D['cyclone']}, range 10,825 to 12,600 CFM", 'sum'),
])

EQUIP = [
 ('', 'Feed tank and mixer', 'By others. Good mixing ahead of dewatering is essential; mixer sized after the sample test.'),
 ('SP-101/102', 'Dewatering, base', '2 screw presses with chopper feed pumps and controls, subject to a sample test. Option: reconditioned decanter centrifuge.'),
 ('SC-101', 'Dryer feed screw', '2 HP. The dewatering unit discharges by chute onto the feed screw (no storage hopper).'),
 ('B-101', 'Dual-fuel burner', '10 MMBtu/hr, LPG + biogas, two NFPA 86 trains, automatic changeover to LPG on loss of biogas.'),
 ('D-101', 'XD-72 Mk.2 rotary drum', '7 ft x 35 ft, co-current single pass, A36 (316L option), 20 HP drive. Design gas capacity about 13,470 ACFM.'),
 ('DB-101 / RV-101', 'Drop-out box and product airlock', 'Heavy duty drop-out box; airlock 1.5 HP.'),
 ('CY-101 / RV-102', 'Cyclone and fines airlock', 'HE-36 in 304 SS (HE-47 with the decanter); FT-12 airlock. Fines rejoin the product.'),
 ('F-101', 'Exhaust fan', 'XF-36, 60 HP, 12 in WC; ducting up to 60 ft. Air permit scrubber, if required, by others.'),
 ('BGS-001', 'Biogas conditioning skid', 'For 195 scfm at 500 ppm H2S or less: iron oxide vessels, gas cooler and knockout, blower, flame arresters, analyzers, control panel.'),
 ('', 'Automation', 'PLC / HMI with LPG and biogas fuel profiles, dryer temperature control, links to dewatering, skid and plant.'),
]
EQ = ''.join(f'<tr><td class="tagc">{t}</td><td><b>{n}</b></td><td>{d}</td></tr>' for t, n, d in EQUIP)

HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>LETEK Rev C Process Flow</title>
<style>
@page {{ size: 11in 8.5in; margin: 0.35in 0.4in; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: Inter, 'Liberation Sans', Arial, sans-serif; color: #141617; font-size: 9.5px; line-height: 1.35; }}
.page {{ page-break-after: always; }} .page:last-child {{ page-break-after: auto; }}
.hd {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #141617; padding-bottom: 6px; margin-bottom: 8px; }}
.hd img {{ height: 40px; }}
.hd .ti {{ text-align: right; }}
.hd h1 {{ margin: 0; font-size: 17px; font-weight: 700; letter-spacing: .02em; text-transform: uppercase; }}
.hd .sub {{ color: #E35A00; font-weight: 600; font-size: 10.5px; letter-spacing: .06em; text-transform: uppercase; }}
.hd .meta {{ color: #575D5E; font-size: 9px; }}
svg {{ width: 100%; height: auto; display: block; }}
.ft {{ display: flex; justify-content: space-between; color: #575D5E; font-size: 8.5px; border-top: 1px solid #C8C7C7; padding-top: 4px; margin-top: 6px; }}
h2 {{ font-size: 11px; text-transform: uppercase; letter-spacing: .08em; background: #575D5E; color: #fff; padding: 3px 8px; margin: 6px 0 4px; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ background: #E4E4E4; text-align: left; font-weight: 600; padding: 3px 5px; border-bottom: 1.5px solid #141617; }}
td {{ padding: 2.5px 5px; border-bottom: 0.5px solid #C8C7C7; vertical-align: top; }}
td.n {{ font-weight: 700; text-align: center; width: 26px; }}
tr.sum td {{ background: #FFF1E8; }}
td.tagc {{ font-weight: 700; color: #E35A00; white-space: nowrap; width: 96px; }}
.notes {{ color: #575D5E; font-size: 8.8px; margin-top: 5px; }}
.notes p {{ margin: 2px 0; }}
</style></head><body>
<section class="page">
 <div class="hd"><img src="data:image/png;base64,{LOGO}" alt="MCE"><div class="ti"><h1>Process flow diagram</h1>
  <div class="sub">LETEK DCG - chicken manure digestate drying - 128.7 MT/day</div>
  <div class="meta">{DOC} Rev {REV} - {DATE} - for budgetary proposal {QREF}</div></div></div>
 {SVG}
 <h2>Key numbers by dewatering route (dryer at full solids capture)</h2>
 <table class="key"><thead><tr><th></th><th>Cake to dryer</th><th>Water evaporated</th><th>Dryer duty</th><th>Biogas covers</th><th>Exhaust (stream 11)</th><th>Fan</th><th>Cyclone</th><th>Liquid fraction (typical capture)</th></tr></thead><tbody>
 <tr><td><b>Screw press (base)</b></td><td>{f(P['cake'])} lb/hr, 30% TS</td><td>{f(P['evap'])} lb/hr</td><td>{P['duty']:.2f} MMBtu/hr</td><td>about {P['cover']:.0%}</td><td><b>{f(P['acfm'])} ACFM</b></td><td>about {P['bhp']:.0f} bhp</td><td>{P['cyclone']}</td><td>{P['liq_mtd']} MT/day</td></tr>
 <tr><td><b>Decanter (option)</b></td><td>{f(D['cake'])} lb/hr, 20% TS</td><td>{f(D['evap'])} lb/hr</td><td>{D['duty']:.2f} MMBtu/hr</td><td>about {D['cover']:.0%}</td><td><b>{f(D['acfm'])} ACFM</b></td><td>about {D['bhp']:.0f} bhp</td><td>{D['cyclone']}</td><td>{D['liq_mtd']} MT/day</td></tr>
 </tbody></table>
 <div class="ft"><span>Midwest Custom Engineering, Inc. - 6526 S Kanner Hwy #215, Stuart, FL 34997 - usemce.com</span><span>{DOC} Rev {REV} - page 1 of 2</span></div>
</section>
<section class="page">
 <div class="hd"><img src="data:image/png;base64,{LOGO}" alt="MCE"><div class="ti"><h1>Stream table and equipment</h1>
  <div class="sub">Screw press base and decanter option</div>
  <div class="meta">{DOC} Rev {REV} - {DATE} - for budgetary proposal {QREF}</div></div></div>
 <h2>Streams</h2>
 <table><thead><tr><th>#</th><th style="width:24%">Stream</th><th>Screw press, 30% TS cake (base)</th><th>Decanter, 20% TS cake (option)</th></tr></thead><tbody>{ROWS}</tbody></table>
 <h2>Equipment</h2>
 <table><tbody>{EQ}</tbody></table>
 <div class="notes">
  <p>Basis: 128.7 MT/day of liquid digestate at 8% TS, 24 h/day; grit and sand handled separately. Dryer streams are from the MCE Dryer HMB Calculator (MCE-HMB-2026-002 Rev C)
  at full solids capture, which sets the largest dryer load; at typical capture the cake, evaporation and exhaust are lower and more solids leave with the liquid fraction.
  Air and LPG figures are on the calculator's propane basis; biogas firing changes them only slightly.</p>
  <p>Cake solids, solids capture and polymer demand are to be confirmed by a test of a digestate sample. The liquid fraction composition (ammoniacal nitrogen about 3,500 mg/L,
  chlorides about 3,000 mg/L, pH about 8; total N, COD, BOD, total P, oils and grease by laboratory analysis) is given in the proposal.</p>
 </div>
 <div class="ft"><span>Midwest Custom Engineering, Inc. - 6526 S Kanner Hwy #215, Stuart, FL 34997 - usemce.com</span><span>{DOC} Rev {REV} - page 2 of 2</span></div>
</section>
</body></html>"""

(HERE/'pfd_revC.html').write_text(HTML)
OUT = HERE/f'{DOC}_Rev{REV}_Process_Flow.pdf'
subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer', f'--print-to-pdf={OUT}',
                (HERE/'pfd_revC.html').as_uri()], check=True, capture_output=True)
print('written', OUT.name, OUT.stat().st_size, 'bytes')
