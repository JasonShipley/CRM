"""LETEK Rev C process flow diagram (MCE-LETEK-PFD-001 Rev C): whole plant from digester to stack, screw press base and
decanter option, with the stream table. Writes pfd_revC.html (browser view) and MCE-LETEK-PFD-001_RevC_Process_Flow.pdf (reportlab + svglib,
standard fonts, small enough to e-mail). Dryer streams are the MCE Dryer HMB Calculator runs (case_letek_revC_press30.json, case_letek_revC_decanter20.json,
full solids capture); liquid fraction ranges, biogas and equipment match quote 20261019-LETEK-C."""
import base64, io, pathlib
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
DOC = 'MCE-LETEK-PFD-001'; REV = 'C'; DATE = 'Oct 19, 2026'; QREF = '20261019-LETEK-C'

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

im = Image.open(REPO/'renderer'/'assets'/'mce-logo.png').convert('RGBA'); im.thumbnail((320, 320))
buf = io.BytesIO(); im.save(buf, 'PNG'); LOGO = base64.b64encode(buf.getvalue()).decode()

def sm(n, x, y):  # stream marker
    return (f'<g class="sm"><rect x="{x-8}" y="{y-8}" width="16" height="16" transform="rotate(45 {x} {y})"/>'
            f'<text x="{x}" y="{y+3.5}">{n}</text></g>')

SVG = f"""<svg viewBox="0 0 1040 520" xmlns="http://www.w3.org/2000/svg" font-family="Liberation Sans, Arial, Helvetica, sans-serif">
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
<path class="fuel" d="M146 36 H268" marker-end="url(#ao)"/>{sm(4, 200, 36)}
<text class="ts mid" x="200" y="25">raw biogas</text>
<path class="fuel" d="M240 36 V96 H296" marker-end="url(#ao)"/>
<text class="ts" x="300" y="93">surplus to digester flare /</text><text class="ts" x="300" y="104">other users (by others)</text>
<rect class="eq" x="270" y="12" width="196" height="58" rx="3"/>
<text class="tag" x="280" y="27">BGS-001</text><text class="tb" x="280" y="41">Biogas conditioning skid</text>
<text class="ts" x="280" y="54">iron oxide H2S polish, cooler/knockout,</text><text class="ts" x="280" y="65">blower to 2 psig, flame arresters, analyzers</text>
<path d="M446 70 V112" fill="none" stroke="#141617" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#ak)"/>
<text class="ts mid" x="446" y="125">condensate to lagoon</text><text class="ts mid" x="446" y="136">(by others)</text>
<path class="fuel" d="M466 36 H505 V188" marker-end="url(#ao)"/>{sm(5, 505, 150)}

<!-- LPG -->
<rect class="oth" x="560" y="104" width="112" height="40" rx="6"/>
<text class="tb mid" x="616" y="121">LPG supply</text><text class="ts mid" x="616" y="134">by others</text>
<path class="fuel" d="M575 144 V164 H540 V188" marker-end="url(#ao)"/>{sm(6, 557, 164)}

<!-- burner -->
<rect class="eq" x="430" y="190" width="128" height="58" rx="3"/>
<text class="tag" x="438" y="205">B-101</text><text class="tb" x="438" y="219">Dual-fuel burner</text>
<text class="ts" x="438" y="231">10 MMBtu/hr, 10:1 turndown</text><text class="ts" x="438" y="242">LPG + biogas</text>
<path class="gas" d="M380 202 H428" marker-end="url(#ab)"/><text class="t end" x="372" y="205">Combustion air</text>{sm(7, 402, 202)}
<path class="gas" d="M380 236 H428" marker-end="url(#ab)"/><text class="t end" x="372" y="239">Make-up air</text>{sm(8, 402, 236)}
<path class="gas" d="M558 219 H588" marker-end="url(#ab)"/>{sm(9, 572, 219)}

<!-- drum -->
<path class="eq" d="M600 186 H812 Q822 186 822 196 V240 Q822 250 812 250 H600 Q590 250 590 240 V196 Q590 186 600 186Z"/>
<rect x="606" y="182" width="8" height="72" fill="#575D5E"/><rect x="800" y="182" width="8" height="72" fill="#575D5E"/>
<text class="tag" x="626" y="204">D-101</text><text class="tb" x="626" y="218">XD-72 Mk.2 rotary drum</text>
<text class="ts" x="626" y="231">7 ft x 35 ft, co-current, single pass</text><text class="ts" x="626" y="242">900 F in / 230 F out</text>
<path d="M740 160 V182" fill="none" stroke="#141617" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#ak)"/>
<text class="ts" x="690" y="155">quench water (by others)</text>

<!-- drop-out box -->
<path class="eq" d="M824 168 H892 V262 L868 292 H848 L824 262Z"/>
<text class="tag" x="830" y="184">DB-101</text><text class="ts" x="830" y="197">drop-out</text><text class="ts" x="830" y="208">box</text>
<circle class="eq" cx="858" cy="306" r="11"/><text class="tag" x="874" y="309">RV-101</text>
<path class="ln" d="M858 292 V295"/>
<path class="ln" d="M858 317 V436" marker-end="url(#ak)"/>{sm(10, 858, 418)}
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
<text class="tag" x="972" y="94">F-101</text><text class="ts" x="963" y="105">XF-36, 60 HP</text><text class="ts" x="963" y="116">on VFD</text>
<rect class="eq" x="1012" y="8" width="16" height="64"/><path class="gas" d="M1001 64 H1012" marker-end="url(#ab)"/>
<text class="tag end" x="1008" y="20">ST-101 stack (option)</text>
<rect class="oth" x="806" y="28" width="124" height="32" rx="4"/><text class="ts mid" x="868" y="41">exhaust scrubber, if the</text><text class="ts mid" x="868" y="53">permit requires: by others</text>{sm(13, 1020, 84)}

<!-- feed and dewatering -->
<path class="ln" d="M60 80 V300" marker-end="url(#ak)"/>{sm(1, 60, 190)}
<text class="ts" x="70" y="160">liquid digestate</text><text class="ts" x="70" y="171">128.7 MT/day, 8% TS</text>
<path class="oth" d="M18 302 H112 V378 Q112 388 102 388 H28 Q18 388 18 378Z"/>
<path d="M88 296 V350 M75 350 H101" stroke="#8A8F90" stroke-width="2"/>
<text class="tb mid" x="65" y="402">Feed tank + mixer</text><text class="ts mid" x="65" y="414">by others</text>
<path class="ln" d="M112 360 H146"/>
<circle class="eq" cx="160" cy="360" r="13"/><path d="M167 360 L154 352 L154 368Z" fill="#141617"/>
<text class="ts mid" x="160" y="386">feed pump</text>
<path class="ln" d="M173 360 H206" marker-end="url(#ak)"/>
<path d="M283 300 V324" fill="none" stroke="#141617" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#ak)"/>
<text class="ts mid" x="283" y="295">polymer, if the test needs it</text>
<rect class="eq" x="208" y="326" width="150" height="66" rx="3"/>
<text class="tag" x="216" y="341">SP-101/102</text><text class="tb" x="216" y="355">2 x screw press</text>
<text class="ts" x="216" y="368">option: reconditioned</text><text class="ts" x="216" y="379">decanter centrifuge</text>
<path class="ln" d="M358 340 H402 V272 H430" marker-end="url(#ak)"/>{sm(2, 380, 340)}
<text class="ts" x="366" y="324">cake</text>
<rect class="eq" x="432" y="262" width="166" height="20" rx="2"/>
<text class="tag" x="440" y="276">SC-101</text><text class="ts" x="486" y="276">dryer feed screw</text>
<path class="ln" d="M598 262 V252" marker-end="url(#ak)"/>
<path class="ln" d="M283 392 V436" marker-end="url(#ak)"/>{sm(3, 283, 414)}
<rect class="oth" x="178" y="438" width="210" height="44" rx="6"/>
<text class="tb mid" x="283" y="456">Liquid fraction</text><text class="ts mid" x="283" y="470">treated to NOM-001 limits by others</text>

<!-- why the exhaust changes -->
<rect x="414" y="306" width="366" height="162" rx="4" fill="#FFF1E8" stroke="#E35A00" stroke-width="1"/>
<text class="tb" x="426" y="325">Why the exhaust airflow depends on the dewatering route</text>
<text class="t" x="426" y="343">The decanter has no air stream of its own. The airflow is the dryer</text>
<text class="t" x="426" y="357">exhaust (stream 11): combustion gas, make-up air and the water</text>
<text class="t" x="426" y="371">evaporated from the cake. Decanter cake is wetter (20% vs 30% TS),</text>
<text class="t" x="426" y="385">so the dryer evaporates {f(D['evap'])} instead of {f(P['evap'])} lb/hr of water.</text>
<text class="t" x="426" y="399">The burner fires {D['duty']:.1f} instead of {P['duty']:.1f} MMBtu/hr, and holding 900 F</text>
<text class="t" x="426" y="413">into the drum takes {f(D['inlet'])} instead of {f(P['inlet'])} SCFM of hot gas, mostly</text>
<text class="t" x="426" y="427">make-up air. Exhaust rises {D['acfm']/P['acfm']-1:.0%}, like the water, from {f(P['acfm'])} to</text>
<text class="t" x="426" y="441">{f(D['acfm'])} ACFM, so the cyclone steps up from an {P['cyclone']} to an {D['cyclone']}.</text>
<text class="t" x="426" y="455">The 7 ft drum and 60 HP fan cover both, with the fan on its VFD.</text>

<!-- legend -->
<g transform="translate(414 480)">
 <path class="ln" d="M0 6 H26"/><text class="ts" x="32" y="9">solids / liquid</text>
 <path class="gas" d="M112 6 H138"/><text class="ts" x="144" y="9">air / gas</text>
 <path class="fuel" d="M206 6 H232"/><text class="ts" x="238" y="9">fuel gas</text>
 <rect class="oth" x="296" y="0" width="22" height="12" rx="2"/><text class="ts" x="324" y="9">by others</text>
 <g transform="translate(0 22)"><rect x="-6" y="-6" width="12" height="12" transform="rotate(45)" fill="#141617"/><text class="ts" x="14" y="4">stream number, see stream table</text>
 <path d="M200 0 H226" fill="none" stroke="#141617" stroke-width="1.5" stroke-dasharray="4 3"/><text class="ts" x="232" y="4">utility / optional</text></g>
</g>
</svg>"""

STREAM_ROWS = []
def row(n, desc, a, b, cls=''):
    STREAM_ROWS.append((n, desc, a, b, cls))
    return f'<tr class="{cls}"><td class="n">{n}</td><td>{desc}</td><td>{a}</td><td>{b}</td></tr>'

ROWS = ''.join([
 row(1, 'Liquid digestate to dewatering', f'{f(FEED_LBHR)} lb/hr (128.7 MT/day, about 34,000 gal/day), 8% TS, {f(SOLIDS)} lb/hr solids', 'same'),
 row(2, 'Dewatered cake to dryer (design: full solids capture)', f"{f(P['cake'])} lb/hr at 30% TS ({f(P['water_in'])} lb/hr water)", f"{f(D['cake'])} lb/hr at 20% TS ({f(D['water_in'])} lb/hr water)"),
 row(3, 'Liquid fraction to treatment (by others)', f"{P['liq_mtd']} MT/day at typical capture ({P['cap']}), {P['liq_ts']} TS. "
     f"{f(P['liq_full'])} lb/hr ({f(P['liq_full']*24/2204.62,1)} MT/day) at full capture", f"{D['liq_mtd']} MT/day at typical capture ({D['cap']}), {D['liq_ts']} TS. "
     f"{f(D['liq_full'])} lb/hr ({f(D['liq_full']*24/2204.62,1)} MT/day) at full capture"),
 row(4, 'Raw biogas from digester', f'{BIOGAS_SCFM} scfm (7,455 Nm3/day), 55% CH4, 500 ppm H2S or less; {BIOGAS_MMBTU_HR:.2f} MMBtu/hr average', 'same'),
 row(5, 'Conditioned biogas to burner (H2S under 100 ppm, 2 psig)', f"about {f(P['bg_scfm'])} scfm ({P['duty']:.2f} MMBtu/hr); the other {f(BIOGAS_SCFM-P['bg_scfm'])} scfm goes to the digester flare / other users ahead of the skid",
     f"all {BIOGAS_SCFM} scfm ({BIOGAS_MMBTU_HR:.2f} MMBtu/hr, covers about {D['cover']:.0%} of the duty)"),
 row(6, 'LPG to burner (start-up, make-up, digester down)', f"none at average biogas; {f(P['lpg_alone'])} lb/hr on LPG alone",
     f"about {f(D['lpg_makeup'])} lb/hr make-up at average biogas (more if the biogas heating value is lower; analysis pending); {f(D['lpg_alone'])} lb/hr on LPG alone"),
 row(7, 'Combustion air, 85 F', f"{f(P['comb'])} ACFM", f"{f(D['comb'])} ACFM"),
 row(8, 'Make-up (dilution) air, 85 F', f"{f(P['makeup'])} SCFM", f"{f(D['makeup'])} SCFM"),
 row(9, 'Mixed gas into drum, 900 F', f"{f(P['inlet'])} SCFM", f"{f(D['inlet'])} SCFM"),
 row(10, 'Dried product, 180 F', f'{f(PRODUCT)} lb/hr at 15% moisture ({f(SOLIDS)} solids + {PRODUCT_WATER} water); 12.1 MT/day at full capture', 'same'),
 row(11, 'Dryer exhaust to cyclone, 230 F', f"<b>{f(P['acfm'])} ACFM</b>, carrying {f(P['evap'])} lb/hr evaporated water", f"<b>{f(D['acfm'])} ACFM</b>, carrying {f(D['evap'])} lb/hr evaporated water"),
 row(12, 'Cyclone fines (rejoin product)', 'included in stream 10', 'included in stream 10'),
 row(13, 'Exhaust to stack', f"{f(P['acfm'])} ACFM at about 230 F; 12 in WC fan static, about {P['bhp']:.0f} bhp", f"{f(D['acfm'])} ACFM; about {D['bhp']:.0f} bhp"),
 row('', '<b>Dryer duty</b> (design / rigorous check)', f"{P['duty']:.2f} / {P['rig']:.2f} MMBtu/hr", f"{D['duty']:.2f} / {D['rig']:.2f} MMBtu/hr", 'sum'),
 row('', '<b>Cyclone</b> (MCE cyclone calculator)', f"{P['cyclone']} budget pick, range 6,175 to 7,600 CFM; final pick after the sample test", f"{D['cyclone']} budget pick, range 10,825 to 12,600 CFM; final pick after the sample test", 'sum'),
])

EQUIP = [
 ('', 'Feed tank and mixer', 'By others. Good mixing ahead of dewatering is essential; mixer sized after the sample test.'),
 ('SP-101/102', 'Dewatering, base', '2 screw presses in parallel with the chopper feed pump, VFD drives and basic controls, subject to a sample test. Option: reconditioned decanter centrifuge.'),
 ('SC-101', 'Dryer feed screw', '2 HP. The dewatering unit discharges by chute onto the feed screw (no storage hopper).'),
 ('B-101', 'Dual-fuel burner', '10 MMBtu/hr, LPG + biogas, two NFPA 86 trains, automatic changeover to LPG on loss of biogas.'),
 ('D-101', 'XD-72 Mk.2 rotary drum', '7 ft x 35 ft, co-current single pass, A36 (304 SS option recommended), 20 HP drive. Design gas capacity about 13,470 ACFM.'),
 ('DB-101 / RV-101', 'Drop-out box and product airlock', 'Heavy duty drop-out box; airlock 1.5 HP.'),
 ('CY-101 / RV-102', 'Cyclone and fines airlock', 'HE-36 in 304 SS (HE-47 with the decanter); FT-12 airlock. Fines rejoin the product.'),
 ('F-101', 'Exhaust fan and VFD', 'XF-36, 60 HP inverter-duty, 12 in WC, on a 60 HP VFD trimmed on drum outlet draft, so the exhaust airflow follows the drying load; ducting up to 60 ft.'),
 ('ST-101', 'Exhaust stack (option)', '24 in OD 304 SS, 10 ga, discharge about 35 ft above grade, EPA Method 1 sampling ports, guyed. Exhaust scrubber, if the air permit requires one, by others.'),
 ('BGS-001', 'Biogas conditioning skid', 'For 195 scfm at 500 ppm H2S or less: iron oxide vessels, gas cooler and knockout, blower, flame arresters, analyzers, control panel.'),
 ('', 'Automation', 'PLC / HMI with LPG and biogas fuel profiles, dryer temperature control, links to dewatering, skid and plant.'),
]
EQ = ''.join(f'<tr><td class="tagc">{t}</td><td><b>{n}</b></td><td>{d}</td></tr>' for t, n, d in EQUIP)

KEY_HEAD = ['', 'Cake to dryer', 'Water evaporated', 'Dryer duty', 'Biogas available vs duty', 'Exhaust (stream 11)', 'Fan shaft power', 'Cyclone', 'Liquid fraction (typical capture)']
KEY = [[f'<b>{c["name"]}</b>', f"{f(c['cake'])} lb/hr, {c['ts']:.0%} TS", f"{f(c['evap'])} lb/hr", f"{c['duty']:.2f} MMBtu/hr", f"about {c['cover']:.0%}",
        f"<b>{f(c['acfm'])} ACFM</b>", f"about {c['bhp']:.0f} bhp", c['cyclone'], f"{c['liq_mtd']} MT/day"] for c in (P, D)]
NOTE = ("Basis: 128.7 MT/day of liquid digestate at 8% TS, 24 h/day; grit and sand handled separately. Dryer streams are from the MCE Dryer HMB Calculator "
        "(MCE-HMB-2026-002 Rev C) at full solids capture, the largest dryer load; air and LPG figures are on its propane basis. At typical press capture "
        "(60 to 80%) and 30 to 35% TS cake the exhaust is about 3,000 to 5,100 ACFM; the cyclone and fan control are confirmed after the sample test, which "
        "also sets cake solids, solids capture and polymer demand. Liquid fraction composition is given in the proposal.")
KEYROWS = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in KEY)

HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>MCE-LETEK-PFD-001 Rev C - Process Flow Diagram</title>
<style>
@page {{ size: 11in 8.5in; margin: 0.35in 0.4in; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: 'Liberation Sans', Arial, Helvetica, sans-serif; color: #141617; font-size: 9.5px; line-height: 1.35; }}
.page {{ page-break-after: always; }} .page:last-child {{ page-break-after: auto; }}
.hd {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #141617; padding-bottom: 6px; margin-bottom: 8px; }}
.hd img {{ height: 40px; }}
.hd .ti {{ text-align: right; }}
.hd h1 {{ margin: 0; font-size: 17px; font-weight: 700; letter-spacing: .02em; text-transform: uppercase; }}
.hd .sub {{ color: #E35A00; font-weight: 600; font-size: 10.5px; letter-spacing: .06em; text-transform: uppercase; }}
.hd .meta {{ color: #575D5E; font-size: 9px; }}
svg {{ width: 100%; height: auto; display: block; }}
.ft {{ display: flex; justify-content: space-between; color: #575D5E; font-size: 8.5px; border-top: 1px solid #C8C7C7; padding-top: 4px; margin-top: 6px; }}
h2 {{ font-size: 11px; text-transform: uppercase; letter-spacing: .08em; background: #575D5E; color: #fff; padding: 2px 8px; margin: 5px 0 3px; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ background: #E4E4E4; text-align: left; font-weight: 600; padding: 3px 5px; border-bottom: 1.5px solid #141617; }}
td {{ padding: 1.8px 5px; border-bottom: 0.5px solid #C8C7C7; vertical-align: top; }}
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
 <table class="key"><thead><tr>{''.join(f'<th>{h}</th>' for h in KEY_HEAD)}</tr></thead><tbody>{KEYROWS}</tbody></table>
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
 <div class="notes"><p>{NOTE}</p></div>
 <div class="ft"><span>Midwest Custom Engineering, Inc. - 6526 S Kanner Hwy #215, Stuart, FL 34997 - usemce.com</span><span>{DOC} Rev {REV} - page 2 of 2</span></div>
</section>
</body></html>"""

(HERE/'pfd_revC.html').write_text(HTML)
OUT = HERE/f'{DOC}_Rev{REV}_Process_Flow.pdf'

# PDF: the same SVG drawn by reportlab with the standard Helvetica fonts (nothing embedded, small enough to e-mail).
# svglib ignores SVG markers and font weights, so arrowheads are drawn explicitly and bold classes map to Helvetica-Bold.
import re
from reportlab import rl_config
rl_config.useA85 = 0   # binary streams: about 20% smaller than ASCII85
from svglib.svglib import svg2rlg
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, Image as RLImage

ARROW = {'ak': '#141617', 'ab': '#1F6FB2', 'ao': '#E35A00'}
def arrowheads(svg):
    def add(m):
        tag, mid = m.group(0), m.group(1)
        pts, x, y = [], 0.0, 0.0
        for cmd, nums in re.findall(r'([MLHV])\s*([-\d.\s]+)', re.search(r' d="([^"]+)"', tag).group(1)):
            v = [float(t) for t in nums.split()]
            if cmd in 'ML': x, y = v[0], v[1]
            elif cmd == 'H': x = v[0]
            else: y = v[0]
            pts.append((x, y))
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        L = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 or 1
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        bx, by = x1 - 7 * ux, y1 - 7 * uy
        tri = f'<path d="M{x1:.1f} {y1:.1f} L{bx - 3.5 * uy:.1f} {by + 3.5 * ux:.1f} L{bx + 3.5 * uy:.1f} {by - 3.5 * ux:.1f}Z" fill="{ARROW[mid]}" stroke="none"/>'
        return tag.replace(f' marker-end="url(#{mid})"', '') + tri
    return re.sub(r'<path[^>]* marker-end="url\(#(\w+)\)"[^>]*/>', add, svg)

svg = arrowheads(SVG).replace('font-family="Liberation Sans, Arial, Helvetica, sans-serif"', 'font-family="Helvetica"')
svg = svg.replace('font-weight:600', 'font-family:Helvetica-Bold').replace('font-weight:700', 'font-family:Helvetica-Bold')
tmp = HERE/'.pfd_revC_tmp.svg'; tmp.write_text(svg); drawing = svg2rlg(str(tmp)); tmp.unlink()

PAGE = landscape(letter); LM = 0.4*inch; TM = 0.35*inch; W = PAGE[0] - 2*LM
INK = colors.HexColor('#141617'); ORANGE = colors.HexColor('#E35A00'); GREY = colors.HexColor('#575D5E')
HEAD = colors.HexColor('#E4E4E4'); RULE = colors.HexColor('#C8C7C7'); SUMBG = colors.HexColor('#FFF1E8')
base = ParagraphStyle('b', fontName='Helvetica', fontSize=7.2, leading=9, textColor=INK)
bold = ParagraphStyle('bb', parent=base, fontName='Helvetica-Bold')
tagst = ParagraphStyle('t', parent=bold, textColor=ORANGE)
bar = ParagraphStyle('bar', parent=bold, fontSize=8.2, leading=10, textColor=colors.white)
note = ParagraphStyle('n', parent=base, fontSize=6.8, leading=8.6, textColor=GREY)
h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=13, leading=15, alignment=2, textColor=INK)
sub = ParagraphStyle('s', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=2, textColor=ORANGE)
meta = ParagraphStyle('m', fontName='Helvetica', fontSize=7, leading=9, alignment=2, textColor=GREY)
_flat = Image.new('RGB', im.size, 'white'); _flat.paste(im, mask=im.split()[3]); _flat.thumbnail((240, 240))   # logo flattened onto white as JPEG for the PDF
im_buf = io.BytesIO(); _flat.save(im_buf, 'JPEG', quality=88)

def header(title, subtitle):
    im_buf.seek(0)
    logo = RLImage(io.BytesIO(im_buf.read()), width=1.45*inch, height=1.45*inch*im.size[1]/im.size[0])
    t = Table([[logo, [Paragraph(title.upper(), h1), Paragraph(subtitle.upper(), sub),
                       Paragraph(f'{DOC} Rev {REV} - {DATE} - for budgetary proposal {QREF}', meta)]]], colWidths=[2*inch, W - 2*inch])
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LINEBELOW', (0, 0), (-1, 0), 2.2, INK), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                           ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    return [t, Spacer(1, 6)]
def section(text):
    t = Table([[Paragraph(text.upper(), bar)]], colWidths=[W])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), GREY), ('TOPPADDING', (0, 0), (-1, -1), 1.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5)]))
    return [Spacer(1, 3), t, Spacer(1, 2)]
def grid(rows, widths, head=True, shade=()):
    t = Table(rows, colWidths=widths, repeatRows=1 if head else 0)
    st = [('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, -1), 0.4, RULE), ('TOPPADDING', (0, 0), (-1, -1), 1.6),
          ('BOTTOMPADDING', (0, 0), (-1, -1), 2), ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]
    if head: st += [('BACKGROUND', (0, 0), (-1, 0), HEAD), ('LINEBELOW', (0, 0), (-1, 0), 1.1, INK)]
    st += [('BACKGROUND', (0, r), (-1, r), SUMBG) for r in shade]
    t.setStyle(TableStyle(st)); return t
def footer(c, doc):
    c.saveState(); c.setFont('Helvetica', 6.5); c.setFillColor(GREY); c.setStrokeColor(RULE); c.setLineWidth(0.6)
    c.line(LM, 0.42*inch, PAGE[0] - LM, 0.42*inch)
    c.drawString(LM, 0.3*inch, 'Midwest Custom Engineering, Inc. - 6526 S Kanner Hwy #215, Stuart, FL 34997 - usemce.com')
    c.drawRightString(PAGE[0] - LM, 0.3*inch, f'{DOC} Rev {REV} - page {doc.page} of 2'); c.restoreState()

sc = W / drawing.width; drawing.scale(sc, sc); drawing.width *= sc; drawing.height *= sc
P_ = lambda t, st=base: Paragraph(str(t), st)
S = header('Process flow diagram', 'LETEK DCG - chicken manure digestate drying - 128.7 MT/day') + [drawing]
S += section('Key numbers by dewatering route (dryer at full solids capture)')
S += [grid([[P_(h, bold) for h in KEY_HEAD]] + [[P_(c) for c in r] for r in KEY], [1.15*inch] + [(W - 1.15*inch) / 8] * 8)]
S += [PageBreak()] + header('Stream table and equipment', 'Screw press base and decanter option') + section('Streams')
rows = [[P_('#', bold), P_('Stream', bold), P_('Screw press, 30% TS cake (base)', bold), P_('Decanter, 20% TS cake (option)', bold)]]
rows += [[P_(n, bold), P_(d), P_(a), P_(b)] for n, d, a, b, _ in STREAM_ROWS]
S += [grid(rows, [0.3*inch, 2.35*inch, (W - 2.65*inch) / 2, (W - 2.65*inch) / 2], shade=[i + 1 for i, r in enumerate(STREAM_ROWS) if r[4] == 'sum'])]
S += section('Equipment') + [grid([[P_(t, tagst), P_(n, bold), P_(d)] for t, n, d in EQUIP], [1.05*inch, 1.9*inch, W - 2.95*inch], head=False)]
S += [Spacer(1, 4), Paragraph(NOTE, note)]
doc = SimpleDocTemplate(str(OUT), pagesize=PAGE, leftMargin=LM, rightMargin=LM, topMargin=TM, bottomMargin=0.55*inch,
                        title=f'{DOC} Rev {REV} - Process Flow Diagram', author='Midwest Custom Engineering, Inc.')
doc.build(S, onFirstPage=footer, onLaterPages=footer)
print('written', OUT.name, OUT.stat().st_size, 'bytes')
