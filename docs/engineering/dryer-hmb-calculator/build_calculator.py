import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

OUT='/home/user/CRM/docs/engineering/dryer-hmb-calculator/MCE_Dryer_HMB_Calculator.xlsx'
wb=openpyxl.Workbook()
F_LABEL=Font(name='Arial',size=10); F_B=Font(name='Arial',size=10,bold=True)
F_IN=Font(name='Arial',size=10,color='0000FF'); F_LINK=Font(name='Arial',size=10,color='008000')
F_H=Font(name='Arial',size=13,bold=True); F_S=Font(name='Arial',size=10,bold=True,color='FFFFFF')
F_NOTE=Font(name='Arial',size=9,italic=True,color='555555')
FILL_S=PatternFill('solid',fgColor='575D5E'); FILL_Y=PatternFill('solid',fgColor='FFFF00'); FILL_H=PatternFill('solid',fgColor='E4E4E4')
FILL_O=PatternFill('solid',fgColor='FF6602')
thin=Side(style='thin',color='C8C7C7'); BOX=Border(top=thin,bottom=thin,left=thin,right=thin)
N0='#,##0'; N1='#,##0.0'; N2='#,##0.00'; N3='0.000'; P0='0%'; P1='0.0%'; N4='0.0000'

def sec(ws,r,text,c1=1,c2=8):
    ws.cell(r,c1,text).font=F_S
    for c in range(c1,c2+1): ws.cell(r,c).fill=FILL_S
def hdr(ws,r,cols,c1=1):
    for i,t in enumerate(cols):
        c=ws.cell(r,c1+i,t); c.font=F_B; c.fill=FILL_H; c.border=BOX; c.alignment=Alignment(wrap_text=True,vertical='center')
def widths(ws,w):
    for i,x in enumerate(w,1): ws.column_dimensions[get_column_letter(i)].width=x

# ===================== README =====================
ws=wb.active; ws.title='README'
widths(ws,[3,110])
rows=["MCE DRYER HEAT & MASS BALANCE CALCULATOR  ·  Rev A  ·  8 Sep 2026",
"",
"What this is: a rebuilt, formula-driven replacement for the calculation half of Prozus report NT-HMB-2025-001 Rev 0 (the Input/CALC/COMB/FLOW/DESIGN/Burner/Emiss. sheets). Every number recalculates from the Inputs sheet. Nothing is pasted.",
"It follows MCE's own quoting method (Drying Rates Calculator, Feb 2026 notes): theoretical Btu per lb water from product inlet temperature, 1,750 Btu/lb with losses for a rotary drum, drum airflow at 350 fpm face velocity, 10 in WC fan static, 5,000 fpm duct velocity, and adds a rigorous energy balance beside it so the two can be compared on every job.",
"",
"HOW TO USE",
"1. Enter the job on the Inputs sheet. Blue cells are inputs; black cells are formulas; green cells pull from another sheet; yellow cells are model data MCE still has to fill in.",
"2. Read the HMB sheet: mass balance, MCE duty vs rigorous duty, combustion, airflow, energy closure (must be zero).",
"3. Read the Equipment sheet: selected dryer model, burner, fan, duct, cyclone inlet, airlocks, annual fuel.",
"4. Flow sheet is the live schematic: burner, make-up air, mixed inlet gas, feed, drum, exhaust and cyclone, fan and stack, product, fines and the optional reactor, each block showing its current numbers. Summary sheet is the one-page hand-off for quoting. Metric sheet mirrors the key results in SI units. Emissions sheet gives potential-to-emit.",
"4b. Biochar Reactor sheet sizes a slow-pyrolysis or torrefaction rotary reactor on the dryer product (or a manual feed): char yield, volatiles energy, autothermal check, auxiliary fuel or surplus heat, reactor length by residence time and by indirect heat flux. Set the coupling switch on Inputs to Yes to credit the surplus against dryer fuel.",
"4c. Drum length is sized, not just checked: the HMB sheet gives the length required at the selected diameter for the residence-time and fill targets, and the Summary shows whether to extend past the standard length.",
"5. Dryer Models: ten standard single-pass sizes plus a custom row; ten triple-pass rows on the same shells with a placeholder airflow factor (yellow) plus a custom row; Z8 eight-pass rows from the original workbook. A model is selected automatically as the smallest of the chosen type that meets both airflow and evaporation with the design margin. Burners are sized to the heat loading; a burner cap is optional per row.",
"",
"WHAT WAS WRONG IN THE ORIGINAL (kept here so it is not repeated)",
"- CALC F4:F15, H4, I39:I45, B47, D48 were pasted values from a 9,000 lb/hr-evaporation job while Input said 1,333 lb/hr; burner, fan, duct and emissions were 6.5x too big.",
"- The enthalpy 'iteration' for inlet temperature never converged (flag read INLET TEMP IS NOT CORRECT). Replaced by a closed-form gas-mass balance from the chosen inlet temperature.",
"- Five different dryer models were named for one case. Replaced by one selection from the model table.",
"- Drum hold-up used 1.5 minutes of product. Replaced by residence time input.",
"- Cyclone efficiency 99.965% and PM10 = 0.007% of PM. Replaced by inputs with realistic defaults to be confirmed against AP-42.",
"- The Prozus rotary dryer / thermal reactor sheets are not carried over: they are on a different basis (35% MC, feed at 100 C, solids to 375 C in the dryer) and their fuel figure is 1.9x high. Their case is recorded on the Cases sheet so it can be rerun here.",
"",
"ASSUMPTIONS AND SOURCES",
"- 1,750 Btu/lb rotary drum energy factor, 1,500 infrared, 1,875 flash tube: Jason Shipley, Drying Rates Calculator and 7 Feb 2026 meeting notes.",
"- Theoretical energy 1.01 x (212 - T_in) + 970.4 Btu/lb: Drying Rates Calculator.",
"- Fuel table HHV, density and excess air: original Input sheet F5:I10. Stoichiometric air for dry wood 5.82 lb/lb from the original COMB sheet (C 47.5 / H 5.4 / O 34.7). Other fuels: standard values, see comments.",
"- Single-pass standard sizes 3x12, 3x20, 4x20, 5x25, 6x30, 7x35, 8x40, 10x50, 12x60, 13x60, any size on request, burner sized to the heat loading, drum inlet up to 900 F: J. Shipley, 9 Sep 2026. Triple-pass rows use the same shells; Baker-Rullman ratings to be loaded when available (site not reachable from the build session).",
"- Z8 eight-pass sizes and ACFM max: original Input sheet K8:L18.",
"- Airlock capacities: original DESIGN sheet K8:N19.",
"- Emission factors are placeholders marked for confirmation against EPA AP-42 for the actual fuel and material.",
"",
"UNITS: imperial throughout; the Metric sheet converts. Moisture contents are wet basis unless labeled otherwise.",
"Prepared by MCE Engineering with Claude. Internal tool, not a customer document."]
for i,t in enumerate(rows,1):
    c=ws.cell(i,2,t); c.font=F_H if i==1 else (F_B if t.isupper() and t else F_LABEL); c.alignment=Alignment(wrap_text=True,vertical='top')
ws.row_dimensions[1].height=22

# ===================== INPUTS =====================
wi=wb.create_sheet('Inputs'); widths(wi,[2,38,14,12,60])
wi['B1']='INPUTS  ·  blue = enter, black = calculated, green = from another sheet'; wi['B1'].font=F_H
I={}  # name -> address
r=3
def inp(name,label,val,unit,note='',fmt=None,formula=False):
    global r
    wi.cell(r,2,label).font=F_LABEL
    c=wi.cell(r,3,val); c.font=F_LABEL if formula else F_IN; c.border=BOX
    if fmt: c.number_format=fmt
    wi.cell(r,4,unit).font=F_LABEL
    if note: wi.cell(r,5,note).font=F_NOTE
    I[name]=f"Inputs!$C${r}"; r+=1
sec(wi,r,'JOB',2,5); r+=1
inp('job','Case name','Case 2 Reserve (example)','', 'Shows on the Flow sheet, top left')
inp('customer','Customer','Stall Master','','Flow sheet header, centre')
inp('location','Customer location','Spring Hill, Florida','','')
inp('prep','Prepared by','NC','','')
inp('docno','Document number','MCE-HMB-2026-001','','')
inp('rev','Revision','0','','')
inp('date','Date','=TODAY()','','Formula; overwrite with a fixed date when issued','mm/dd/yyyy',True)
inp('material','Material','Wood shavings','','')
sec(wi,r,'MATERIAL AND THROUGHPUT',2,5); r+=1
inp('wet','Wet feed rate',3000,'lb/hr','Enter wet feed OR set to =C? from dry product below; this is the governing input',N0)
inp('mcin','Moisture in, wet basis',0.50,'','Fraction, e.g. 0.50',P1)
inp('mcout','Moisture out, wet basis',0.10,'','',P1)
inp('tin','Product temperature in',60,'°F','Drying Rates Calculator uses 40 °F for winter feed; 60 °F typical')
inp('tout','Product temperature out',200,'°F','Dried material discharge temperature')
inp('cp','Specific heat of dry solids',0.35,'Btu/lb·°F','Dry wood 0.32–0.40; original sheets used 0.55 (wet) and 0.23 (Prozus)',N2)
inp('bd','Bulk density, dried product',8,'lb/ft³','Used for airlock and screw sizing',N1)
inp('bdwet','Bulk density, wet feed',12,'lb/ft³','',N1)
inp('restime','Drum residence time target',15,'min','Sizes the drum length; 10–30 min single pass, longer for fluffy or sticky product',N0)
inp('fill','Drum fill target',0.10,'fraction of drum volume','5–15% normal; sets the length needed for the residence time',P0)
sec(wi,r,'SITE',2,5); r+=1
inp('elev','Elevation',1200,'ft','')
inp('tamb','Ambient temperature',60,'°F','')
inp('hum','Ambient humidity',0.010,'lb H2O/lb dry air','Florida summer ~0.015; original had 0.002',N3)
sec(wi,r,'DRYER AND FUEL',2,5); r+=1
inp('dtype','Dryer type','Single-pass rotary drum','','Pick from list (dropdown): Single-pass rotary drum, Triple-pass rotary drum, Z8 eight-pass, Infrared, Flash tube')
inp('efactor','MCE energy factor','=INDEX($H$5:$H$9,MATCH(C{0},$G$5:$G$9,0))'.format(r-1),'Btu/lb water','From the dryer type table at right',N0,True)
inp('fuel','Fuel','Natural Gas','','Pick from list (dropdown): see fuel table at right')
fuelrow=r-1
inp('hhv','Fuel heating value','=INDEX($H$13:$H$18,MATCH(C{0},$G$13:$G$18,0))'.format(fuelrow),'Btu/lb','',N0,True)
inp('xs','Excess air at burner','=INDEX($J$13:$J$18,MATCH(C{0},$G$13:$G$18,0))'.format(fuelrow),'fraction','',P0,True)
inp('stoich','Stoichiometric air','=INDEX($K$13:$K$18,MATCH(C{0},$G$13:$G$18,0))'.format(fuelrow),'lb air/lb fuel','',N2,True)
inp('h2ofuel','Water formed per lb fuel','=INDEX($L$13:$L$18,MATCH(C{0},$G$13:$G$18,0))'.format(fuelrow),'lb H2O/lb fuel','Includes fuel moisture for wood',N2,True)
inp('co2fuel','CO2 per lb fuel','=INDEX($M$13:$M$18,MATCH(C{0},$G$13:$G$18,0))'.format(fuelrow),'lb/lb fuel','',N2,True)
inp('tgin','Dryer inlet gas temperature',900,'°F','Design choice, up to the maximum below. Lower it for heat-sensitive product.',N0)
inp('tgmax','Maximum drum inlet gas temperature',900,'°F','MCE design limit, J. Shipley 9 Sep 2026',N0)
inp('tgout','Dryer exhaust gas temperature',180,'°F','Original 180 °F; 200–230 °F for high-moisture feeds',N0)
inp('etacomb','Combustion efficiency',0.90,'fraction','Original Input H3',P0)
inp('shell','Shell and radiation loss',0.03,'fraction of fired duty','',P0)
inp('leak','Air in-leakage at seals',0.10,'fraction of hot gas','Adds to exhaust volume only',P0)
inp('fuelcost','Fuel cost',8.00,'$/MMBtu','Assumption for the annual line; change per site',N2)
sec(wi,r,'AIR HANDLING AND MARGINS',2,5); r+=1
inp('facev','Drum face velocity for airflow rating',350,'fpm','MCE rule: drum cross-section × 350 fpm = design ACFM (7 Feb 2026 notes)',N0)
inp('sp','Fan static pressure',10,'in WC','MCE rule of thumb for drum + duct + cyclone',N1)
inp('fanef','Fan static efficiency',0.65,'fraction','',P0)
inp('ductv','Duct velocity',5000,'fpm','≥5,000 fpm wood and alfalfa; 4,500 for products under 12 lb/ft³',N0)
inp('cycv','Cyclone inlet velocity',3300,'fpm','For the inlet-area line; final cyclone from the MCE cyclone calculator',N0)
inp('convey','Minimum conveying air',3,'lb air/lb product','Original Input A26',N1)
inp('bmargin','Burner sizing margin',0.20,'fraction','',P0)
inp('smargin','Model selection margin on airflow and evaporation',0.15,'fraction','',P0)
inp('mindia','Minimum drum diameter (0 = automatic)',0,'ft','Force a larger drum than the automatic pick, e.g. 10 for an XD-120',N1)
inp('burnerflux','Burner face heat release',1200,'Btu/hr per in²','Drying Rates Calculator',N0)
inp('tpfactor','Triple-pass airflow factor vs single-pass of same OD',1.0,'fraction','PLACEHOLDER until the Baker-Rullman spec table is loaded; 1.0 rates a triple-pass drum like a single-pass of the same OD',N2)
sec(wi,r,'BIOCHAR REACTOR COUPLING',2,5); r+=1
inp('couple','Credit reactor surplus heat against dryer fuel?','No','','Yes or No. Yes takes the surplus from the Biochar Reactor sheet off the purchased fuel')
sec(wi,r,'OPERATION',2,5); r+=1
inp('hrsday','Hours per day',24,'h','',N0)
inp('daysyr','Days per year',312,'d','',N0)
inp('hrsyr','Annual operating hours','=C{0}*C{1}'.format(r-2,r-1),'h/yr','',N0,True)
# Reference tables (right side)
wi['G3']='DRYER TYPE'; wi['G3'].font=F_B; wi['H3']='Energy factor Btu/lb'; wi['H3'].font=F_B; wi['I3']='Note'; wi['I3'].font=F_B
types=[('Single-pass rotary drum',1750,'MCE standard, confirmed J. Shipley 9 Sep 2026'),('Triple-pass rotary drum',1750,'MCE standard, confirmed J. Shipley 9 Sep 2026'),('Z8 eight-pass',1750,'MCE standard, confirmed J. Shipley 9 Sep 2026'),('Infrared',1500,'7 Feb 2026 notes'),('Flash tube',1875,'1,850–1,900 per notes')]
for i,(a,b,c) in enumerate(types):
    wi.cell(5+i,7,a).font=F_LABEL; x=wi.cell(5+i,8,b); x.font=F_IN; x.number_format=N0; wi.cell(5+i,9,c).font=F_NOTE
wi['G11']='FUEL TABLE'; wi['G11'].font=F_B
hdr(wi,12,['Fuel','HHV Btu/lb','lb/ft³','Excess air','Stoich air lb/lb','H2O lb/lb fuel','CO2 lb/lb fuel','Source'],7)
fuels=[('Natural Gas',22800,0.044,0.25,16.33,2.25,2.75,'Original Input F6:I6; stoich from original CALC G25'),
       ('Propane',19900,0.048,0.30,15.7,1.63,3.0,'Original Input F8:I8; stoich standard'),
       ('#2 Fuel Oil',18500,55.6,0.50,14.3,1.14,3.2,'Original Input F9:I9; stoich standard'),
       ('Biomass (wet, 8,500)',8500,15,1.0,5.9,0.9,1.74,'Original Input F7:I7 had 200% excess air; reduced to 100%, confirm'),
       ('Dry Wood',8000,12,1.3,5.82,0.58,1.74,'Original Input F10:I10; stoich, H2O, CO2 from original COMB L32, L42+L54, L41'),
       ('Biogas 55% CH4',12000,0.070,0.15,7.5,1.0,2.0,'Placeholder for dual-fuel jobs; enter analysis when known')]
for i,f in enumerate(fuels):
    for j,v in enumerate(f):
        c=wi.cell(13+i,7+j,v); c.font=F_IN if 0<j<7 else (F_NOTE if j==7 else F_LABEL); c.border=BOX
        if j in (1,): c.number_format=N0
        if j==3: c.number_format=P0
wi.column_dimensions['G'].width=24; wi.column_dimensions['H'].width=12; wi.column_dimensions['I'].width=10
for col in 'JKLM': wi.column_dimensions[col].width=13
wi.column_dimensions['N'].width=60
dv1=DataValidation(type='list',formula1='=$G$5:$G$9',allow_blank=False); wi.add_data_validation(dv1); dv1.add(I['dtype'].split('!')[1].replace('$',''))
dv2=DataValidation(type='list',formula1='=$G$13:$G$18',allow_blank=False); wi.add_data_validation(dv2); dv2.add(I['fuel'].split('!')[1].replace('$',''))
dv3=DataValidation(type='list',formula1='"Yes,No"',allow_blank=False); wi.add_data_validation(dv3); dv3.add(I['couple'].split('!')[1].replace('$',''))
wi.freeze_panes='B3'

# ===================== HMB =====================
wh=wb.create_sheet('HMB'); widths(wh,[2,46,16,14,60])
wh['B1']='HEAT AND MASS BALANCE  ·  imperial'; wh['B1'].font=F_H
H={}; r=3
def row(ws,D,name,label,formula,unit,fmt=N0,note='',bold=False,link=False):
    global r
    ws.cell(r,2,label).font=F_B if bold else F_LABEL
    c=ws.cell(r,3,formula); c.font=F_LINK if link else (F_B if bold else F_LABEL); c.number_format=fmt; c.border=BOX
    ws.cell(r,4,unit).font=F_LABEL
    if note: ws.cell(r,5,note).font=F_NOTE
    D[name]=f"{ws.title}!$C${r}"; r+=1
def L(n): return I[n]
sec(wh,r,'MASS BALANCE',2,5); r+=1
row(wh,H,'wet','Wet feed',f'={L("wet")}','lb/hr',link=True)
row(wh,H,'solids','Dry solids',f'={L("wet")}*(1-{L("mcin")})','lb/hr')
row(wh,H,'win','Water in with feed',f'={L("wet")}*{L("mcin")}','lb/hr')
row(wh,H,'prod','Dried product',f'={H["solids"]}/(1-{L("mcout")})','lb/hr',bold=True)
row(wh,H,'wout','Water remaining in product',f'={H["prod"]}-{H["solids"]}','lb/hr')
row(wh,H,'evap','Water evaporated',f'={H["win"]}-{H["wout"]}','lb/hr',bold=True,note='Governs everything below')
row(wh,H,'evapgal','Water evaporated',f'={H["evap"]}/8.345','gal/hr',N1)
row(wh,H,'tph','Product',f'={H["prod"]}/2000','TPH',N2)
sec(wh,r,'MCE METHOD (Drying Rates Calculator)',2,5); r+=1
row(wh,H,'theo','Theoretical energy per lb water',f'=1.01*(212-{L("tin")})+970.4','Btu/lb',N1,note='Sensible to 212 °F plus latent 970.4')
row(wh,H,'efac','Energy factor with losses',f'={L("efactor")}','Btu/lb',link=True)
row(wh,H,'qmce','Total Btu of system (MCE)',f'={H["evap"]}*{H["efac"]}','Btu/hr',bold=True,note='The number quoting has always used')
row(wh,H,'qmceMM','Total Btu of system (MCE)',f'={H["qmce"]}/1000000','MMBtu/hr',N2)
sec(wh,r,'RIGOROUS BALANCE (check on the MCE factor)',2,5); r+=1
row(wh,H,'qsol','Heat dry solids',f'={H["solids"]}*{L("cp")}*({L("tout")}-{L("tin")})','Btu/hr')
row(wh,H,'qwp','Heat water remaining in product',f'={H["wout"]}*1.0*({L("tout")}-{L("tin")})','Btu/hr')
row(wh,H,'qws','Heat evaporated water to 212 °F',f'={H["evap"]}*1.01*(212-{L("tin")})','Btu/hr')
row(wh,H,'qlat','Vaporize',f'={H["evap"]}*970.4','Btu/hr')
row(wh,H,'qsup','Superheat vapor to exhaust temperature',f'={H["evap"]}*0.45*({L("tgout")}-212)','Btu/hr',note='Negative if exhaust is below 212 °F, as in the original')
row(wh,H,'qprod','Product heating requirement',f'=SUM({H["qsol"].split("!")[1]}:{H["qsup"].split("!")[1]})','Btu/hr',bold=True)
row(wh,H,'gasfrac','Share of released heat given up by the gas',f'={L("etacomb")}*({L("tgin")}-{L("tgout")})/({L("tgin")}-{L("tamb")})','fraction',N3,note='(T_in − T_exhaust)/(T_in − T_ambient) × combustion efficiency')
row(wh,H,'qfired','Fired duty, rigorous',f'={H["qprod"]}/({H["gasfrac"]}-{L("shell")})','Btu/hr',bold=True,note='Closed form; replaces the unconverged iteration in the original CALC')
row(wh,H,'qfiredMM','Fired duty, rigorous',f'={H["qfired"]}/1000000','MMBtu/hr',N2)
row(wh,H,'btulb','Btu per lb water, rigorous',f'={H["qfired"]}/{H["evap"]}','Btu/lb',N0,bold=True)
row(wh,H,'btuchk','Check against MCE factor',f'=IF(ABS({H["btulb"]}/{H["efac"]}-1)<=0.15,"WITHIN 15% OF MCE FACTOR",IF({H["btulb"]}>{H["efac"]},"RIGOROUS IS HIGHER: raise inlet temp or accept higher fuel","RIGOROUS IS LOWER: MCE factor is conservative here"))','',note='Original FLOW G8 showed 11,788 Btu/lb and nobody looked')
row(wh,H,'qdesign','Design fired duty used downstream',f'=MAX({H["qmce"]},{H["qfired"]})','Btu/hr',bold=True,note='Larger of the two, by policy')
sec(wh,r,'COMBUSTION',2,5); r+=1
row(wh,H,'fuel','Fuel rate',f'={H["qdesign"]}/{L("hhv")}','lb/hr',N1,bold=True)
row(wh,H,'credit','Reactor surplus heat credited',f'=IF({L("couple")}="Yes",MAX(0,MIN({H["qdesign"]},\'Biochar Reactor\'!$C$40)),0)','Btu/hr',N0,note='From the Biochar Reactor sheet when coupling is Yes')
row(wh,H,'qpurch','Purchased fuel duty',f'={H["qdesign"]}-{H["credit"]}','Btu/hr',N0,bold=True)
row(wh,H,'fuelp','Purchased fuel rate',f'={H["qpurch"]}/{L("hhv")}','lb/hr',N1,bold=True)
row(wh,H,'fuelcf','Fuel volume (all fired)',f'={H["fuel"]}/INDEX(Inputs!$I$13:$I$18,MATCH({L("fuel")},Inputs!$G$13:$G$18,0))/60','ft³/min',N1,note='Gas fuels: ft³/min at standard; solid fuels: bulk ft³/min')
row(wh,H,'cair','Combustion air',f'={H["fuel"]}*{L("stoich")}*(1+{L("xs")})','lb/hr')
row(wh,H,'poc','Products of combustion',f'={H["fuel"]}+{H["cair"]}','lb/hr')
row(wh,H,'pocw','Water in products of combustion',f'={H["fuel"]}*{L("h2ofuel")}+{H["cair"]}*{L("hum")}','lb/hr')
row(wh,H,'tflame','Adiabatic products temperature, approx.',f'={L("tamb")}+{H["qdesign"]}*{L("etacomb")}/(0.27*{H["poc"]})','°F',N0,note='cp 0.27 average; sanity only')
sec(wh,r,'DRYER GAS FLOW',2,5); r+=1
row(wh,H,'mgas','Hot gas to dryer at inlet temperature',f'={H["qdesign"]}*{L("etacomb")}/(0.24*({L("tgin")}-{L("tamb")}))','lb/hr',bold=True,note='Products of combustion plus dilution air, dry basis')
row(wh,H,'mdil','Dilution (make-up) air',f'={H["mgas"]}-{H["poc"]}','lb/hr',note='Must be positive; if negative the inlet temperature is above what this fuel and excess air can give')
row(wh,H,'tinchk','Inlet temperature vs MCE maximum',f'=IF({L("tgin")}<={L("tgmax")},"OK","INLET ABOVE MCE MAXIMUM - lower it")','')
row(wh,H,'dilchk','Dilution check',f'=IF({H["mdil"]}<0,"INLET TEMP TOO HIGH FOR THIS FUEL / EXCESS AIR","OK")','')
row(wh,H,'mleak','Air in-leakage',f'={H["mgas"]}*{L("leak")}','lb/hr')
row(wh,H,'exdry','Exhaust dry gas',f'={H["mgas"]}+{H["mleak"]}','lb/hr')
row(wh,H,'exw','Exhaust water vapor',f'={H["pocw"]}+({H["mdil"]}+{H["mleak"]})*{L("hum")}+{H["evap"]}','lb/hr')
row(wh,H,'extot','Exhaust total',f'={H["exdry"]}+{H["exw"]}','lb/hr',bold=True)
row(wh,H,'exww','Exhaust humidity',f'={H["exw"]}/{H["exdry"]}','lb H2O/lb dry gas',N3)
row(wh,H,'pratio','Elevation pressure ratio',f'=(1-0.0000068754*{L("elev")})^5.2559','',N4,note='Standard atmosphere')
row(wh,H,'rhod','Dry gas density at exhaust temperature and elevation',f'=0.0765*530/(460+{L("tgout")})*{H["pratio"]}','lb/ft³',N4)
row(wh,H,'rhov','Water vapor density at exhaust temperature and elevation',f'=0.0476*530/(460+{L("tgout")})*{H["pratio"]}','lb/ft³',N4)
row(wh,H,'acfm','Exhaust volume at exhaust temperature',f'={H["exdry"]}/{H["rhod"]}/60+{H["exw"]}/{H["rhov"]}/60','ACFM',N0,bold=True,note='Sizes the fan, cyclone and duct')
row(wh,H,'scfm','Exhaust volume, standard',f'={H["exdry"]}/0.075/60+{H["exw"]}/0.0467/60','SCFM',N0)
row(wh,H,'scfmin','Hot gas to dryer, standard volume',f'={H["mgas"]}/0.075/60','SCFM',N0)
row(wh,H,'scfmdil','Make-up air, standard volume',f'={H["mdil"]}/0.075/60','SCFM',N0)
row(wh,H,'cairacfm','Combustion air volume at ambient',f'={H["cair"]}/(0.0765*530/(460+{L("tamb")})*{H["pratio"]})/60','ACFM',N0)
row(wh,H,'fuelburn','Product burned as fuel',f'=IF(OR({L("fuel")}="Dry Wood",{L("fuel")}="Biomass (wet, 8,500)"),{H["fuelp"]},0)','lb/hr',N1,note='When the dryer burns its own product')
row(wh,H,'netprod','Net dry product after fuel',f'={H["prod"]}-{H["fuelburn"]}','lb/hr',N0)
row(wh,H,'acfmin','Inlet gas volume at inlet temperature',f'=({H["mgas"]}/(0.0765*530/(460+{L("tgin")})*{H["pratio"]})+{H["pocw"]}/(0.0476*530/(460+{L("tgin")})*{H["pratio"]}))/60','ACFM',N0,note='Furnace outlet duct')
row(wh,H,'conveyr','Conveying air ratio',f'={H["exdry"]}/{H["prod"]}','lb air/lb product',N1)
row(wh,H,'conveyc','Conveying check',f'=IF({H["conveyr"]}>={L("convey")},"CONVEYING CAN OCCUR","CONVEYING CANNOT OCCUR: add recycle or raise airflow")','')
sec(wh,r,'ENERGY CLOSURE (must be zero)',2,5); r+=1
row(wh,H,'ein','Fuel energy in',f'={H["qdesign"]}','Btu/hr')
row(wh,H,'ecomb','Combustion inefficiency',f'={H["qdesign"]}*(1-{L("etacomb")})','Btu/hr')
row(wh,H,'eprod','To product (heating and evaporation)',f'={H["qprod"]}*{H["qdesign"]}/{H["qfired"]}','Btu/hr',note='Scaled when the MCE duty governs; the extra heat is real margin, not a balance error')
row(wh,H,'eshell','Shell loss',f'={H["qdesign"]}*{L("shell")}','Btu/hr')
row(wh,H,'eexh','Exhaust sensible heat, dry gas',f'={H["mgas"]}*0.24*({L("tgout")}-{L("tamb")})','Btu/hr')
row(wh,H,'eres','Residual',f'={H["ein"]}-{H["ecomb"]}-{H["eprod"]}-{H["eshell"]}-{H["eexh"]}','Btu/hr',N0,bold=True,note='Zero when the MCE and rigorous duties agree; otherwise equals the margin the MCE factor carries')
row(wh,H,'eresp','Residual as share of fuel',f'={H["eres"]}/{H["ein"]}','',P1)
sec(wh,r,'DRUM CHECKS (selected model from Equipment sheet)',2,5); r+=1
row(wh,H,'model','Selected dryer',"=Equipment!$C$5",'',link=True)
row(wh,H,'vol','Drum volume',"=Equipment!$C$8",'ft³',N0,link=True)
row(wh,H,'load','Evaporative loading',f'=IF({H["vol"]}>0,{H["evap"]}/{H["vol"]},"n/a")','lb/hr·ft³',N2,bold=True,note='Single-pass practice 3–8 on biomass, 2–5 on sludge and manure')
row(wh,H,'holdvol','Material in drum at residence time target',f'={L("wet")}/60*{L("restime")}/{L("bdwet")}','ft³',N1)
row(wh,H,'holdpct','Drum fill at standard length',f'=IF({H["vol"]}>0,{H["holdvol"]}/{H["vol"]},"n/a")','fraction',P1,note='Original FLOW used 1.5 minutes of product and read 0.1%; 5–15% is normal')
row(wh,H,'restd','Residence time at standard length and fill target',f'=IF({H["vol"]}>0,{H["vol"]}*{L("fill")}/({L("wet")}/60/{L("bdwet")}),"n/a")','min',N1)
row(wh,H,'volreq','Drum volume required for residence target at fill target',f'={H["holdvol"]}/{L("fill")}','ft³',N0)
row(wh,H,'lenreq','Drum length required at selected diameter',"=IF(ISNUMBER(Equipment!$C$5),"+H["volreq"]+"/(PI()/4*Equipment!$C$5^2),\"n/a\")",'ft',N1,bold=True,note='Extend the drum past the standard length when this is longer')
row(wh,H,'lensel','Drum length to quote',"=IF(ISNUMBER(Equipment!$C$6),MAX(Equipment!$C$6,CEILING("+H["lenreq"]+",1)),\"n/a\")",'ft',N0,bold=True)
row(wh,H,'lennote','Length note',"=IF(ISNUMBER(Equipment!$C$6),IF("+H["lenreq"]+">Equipment!$C$6,\"EXTEND DRUM \"&TEXT("+H["lenreq"]+"-Equipment!$C$6,\"0.0\")&\" ft FOR RETENTION TIME\",\"STANDARD LENGTH GIVES THE RETENTION TIME\"),\"\")",'')
wh.freeze_panes='B3'

# ===================== DRYER MODELS =====================
wm=wb.create_sheet('Dryer Models'); widths(wm,[2,10,30,9,9,10,10,12,12,13,13,12,12,13,14,10,60])
wm['B1']='DRYER MODELS  ·  one table, three types  ·  yellow = MCE to fill'; wm['B1'].font=F_H
wm['B2']='Reference evaporative loading for the volume-limited rating, lb/hr·ft³:'; wm['B2'].font=F_LABEL
wm['K2']='Single-pass'; wm['L2']=6.0; wm['M2']='Triple-pass'; wm['N2']=8.0; wm['O2']='Z8'; wm['P2']=8.0
for a in ('L2','N2','P2'): wm[a].font=F_IN; wm[a].number_format=N1
wm['B3']='Burners are sized to the heat loading, so drums rate on volume × reference loading; enter a burner cap only if a drum has a fixed burner. Design ACFM for single-pass = cross-section × face velocity. Triple-pass rows use the same shells times the triple-pass factor on Inputs until Baker-Rullman ratings are entered (yellow). Z8 uses the entered ACFM.'; wm['B3'].font=F_NOTE
hdr(wm,5,['Type','Model','Dia ft','Length ft','Cross-section ft²','Volume ft³','Design ACFM','Burner cap MMBtu/hr (optional)','Evap at burner cap lb/hr','Evap at volume loading lb/hr','Rated evap lb/hr','Meets job? (row)','Burner at rated evap MMBtu/hr','Overall L×W×H in','Fan hp','Source / status'],2)
sizes=[(3,12),(3,20),(4,20),(5,25),(6,30),(7,35),(8,40),(10,50),(12,60),(13,60)]
M=[]
for d,l in sizes:
    M.append(('Single-pass rotary drum',f"XD-{d*12} ({d}'×{l}')",d,l,None,None,'','','MCE standard size, J. Shipley 9 Sep 2026; burner sized to heat loading'))
M.append(('Single-pass rotary drum','Custom single-pass (enter dia × length)',None,None,None,None,'','','Any size can be built; enter drum OD and length'))
for d,l in sizes:
    M.append(('Triple-pass rotary drum',f"TP-{d*12} ({d}'×{l}')",d,l,'F',None,'','','MCE will match the Baker-Rullman triple-pass models; ACFM = OD cross-section × face velocity × triple-pass factor until their ratings are entered'))
M.append(('Triple-pass rotary drum','Custom triple-pass (enter dia × length)',None,None,'F',None,'','','Any size can be built'))
z8=[("6'x24'",6,24,7000),("8'x35'",8,35,18000),("10'x40'",10,40,32000),("10'x50'",10,50,40000),("12'x50'",12,50,55000),("12'x60'",12,60,65000),("12'x70'",12,70,75000),("13'x60'",13,60,80000),("14'x70'",14,70,90000),("15'x70'",15,70,100000)]
for n,d,l,a in z8:
    M.append(('Z8 eight-pass',f'Z8 {n}',d,l,a,None,'','','Original Input K8:L18 ACFM max'))
first=6
for i,(typ,model,dia,ln,acfm,burner,dims,fan,src) in enumerate(M):
    rr=first+i
    wm.cell(rr,2,typ).font=F_LABEL; wm.cell(rr,3,model).font=F_B
    for col,val,fill in ((4,dia,dia is None),(5,ln,ln is None)):
        c=wm.cell(rr,col,val); c.font=F_IN; c.border=BOX
        if fill: c.fill=FILL_Y
    c=wm.cell(rr,6,f'=IF(OR(D{rr}="",E{rr}=""),"",PI()/4*D{rr}^2)'); c.number_format=N1; c.border=BOX
    c=wm.cell(rr,7,f'=IF(OR(D{rr}="",E{rr}=""),"",F{rr}*E{rr})'); c.number_format=N0; c.border=BOX
    if typ.startswith('Single'):
        c=wm.cell(rr,8,f'=IF(F{rr}="","",F{rr}*{L("facev")})'); c.number_format=N0; c.border=BOX
    elif acfm=='F':
        c=wm.cell(rr,8,f'=IF(F{rr}="","",F{rr}*{L("facev")}*{L("tpfactor")})'); c.number_format=N0; c.border=BOX; c.fill=FILL_Y
    else:
        c=wm.cell(rr,8,acfm); c.font=F_IN; c.number_format=N0; c.border=BOX
        if acfm is None: c.fill=FILL_Y
    c=wm.cell(rr,9,burner); c.font=F_IN; c.number_format=N1; c.border=BOX
    ref={'Single-pass rotary drum':'$L$2','Triple-pass rotary drum':'$N$2','Z8 eight-pass':'$P$2'}[typ]
    c=wm.cell(rr,10,f'=IF(I{rr}="","",I{rr}*1000000/{L("efactor")})'); c.number_format=N0; c.border=BOX
    c=wm.cell(rr,11,f'=IF(G{rr}="","",G{rr}*{ref})'); c.number_format=N0; c.border=BOX
    c=wm.cell(rr,12,f'=IF(K{rr}="","",IF(J{rr}="",K{rr},MIN(J{rr},K{rr})))'); c.number_format=N0; c.border=BOX
    c=wm.cell(rr,13,f'=IF(AND(B{rr}={L("dtype")},H{rr}<>"",L{rr}<>"",D{rr}>={L("mindia")},H{rr}>=HMB!$C$52*(1+{L("smargin")}),L{rr}>={H["evap"]}*(1+{L("smargin")})),ROW(),99999)'); c.number_format=N0; c.border=BOX
    c=wm.cell(rr,14,f'=IF(L{rr}="","",L{rr}*{L("efactor")}/1000000)'); c.number_format=N1; c.border=BOX
    wm.cell(rr,15,dims).font=F_IN; wm.cell(rr,16,fan).font=F_IN; wm.cell(rr,16).fill=FILL_Y
    wm.cell(rr,17,src).font=F_NOTE
last=first+len(M)-1
# patch: the airflow reference must point at HMB acfm row; compute its address
acfm_addr=H['acfm'].split('!')[1]
for rr in range(first,last+1):
    wm.cell(rr,13).value=wm.cell(rr,13).value.replace('HMB!$C$52',f'HMB!{acfm_addr}')
wm.freeze_panes='D6'

# ===================== EQUIPMENT =====================
we=wb.create_sheet('Equipment'); widths(we,[2,46,16,14,62])
we['B1']='EQUIPMENT SELECTION  ·  imperial'; we['B1'].font=F_H
E={}; r=3
sec(we,r,'DRYER',2,5); r+=1
rng=lambda col: f"'Dryer Models'!${col}${first}:${col}${last}"
row(we,E,'sel','Selected dryer (smallest of the chosen type that meets airflow and evaporation with margin)',f'=IFERROR(INDEX({rng("C")},MATCH(MIN({rng("M")}),{rng("M")},0)),"NO MODEL OF THIS TYPE MEETS THE JOB - fill ratings or pick another type")','',bold=True)
row(we,E,'seldia','Drum diameter',f'=IFERROR(INDEX({rng("D")},MATCH(MIN({rng("M")}),{rng("M")},0)),"")','ft',N1)
row(we,E,'sellen','Drum length',f'=IFERROR(INDEX({rng("E")},MATCH(MIN({rng("M")}),{rng("M")},0)),"")','ft',N1)
row(we,E,'selvol','Drum volume',f'=IFERROR(INDEX({rng("G")},MATCH(MIN({rng("M")}),{rng("M")},0)),0)','ft³',N0)
row(we,E,'selacfm','Model design airflow',f'=IFERROR(INDEX({rng("H")},MATCH(MIN({rng("M")}),{rng("M")},0)),"")','ACFM',N0)
row(we,E,'selevap','Model rated evaporation',f'=IFERROR(INDEX({rng("L")},MATCH(MIN({rng("M")}),{rng("M")},0)),"")','lb/hr',N0)
row(we,E,'selburn','Model maximum burner',f'=IFERROR(IF(INDEX({rng("I")},MATCH(MIN({rng("M")}),{rng("M")},0))="","not entered",INDEX({rng("I")},MATCH(MIN({rng("M")}),{rng("M")},0))),"")','MMBtu/hr',N1)
row(we,E,'selbrated','Burner at model rated evaporation',f'=IFERROR(INDEX({rng("N")},MATCH(MIN({rng("M")}),{rng("M")},0)),"")','MMBtu/hr',N1,note='What the drum can use at reference loading; the job burner below is what it needs')
row(we,E,'lenq','Drum length to quote (standard or extended for retention)',f'={H["lensel"]}','ft',N0,bold=True,link=True)
row(we,E,'useacfm','Airflow utilization',f'=IF(ISNUMBER({E["selacfm"]}),{H["acfm"]}/{E["selacfm"]},"")','',P0)
row(we,E,'useevap','Evaporation utilization',f'=IF(ISNUMBER({E["selevap"]}),{H["evap"]}/{E["selevap"]},"")','',P0)
sec(we,r,'BURNER',2,5); r+=1
row(we,E,'bduty','Fired duty, design',f'={H["qdesign"]}/1000000','MMBtu/hr',N2,link=True)
row(we,E,'bsize','Burner size with margin',f'={E["bduty"]}*(1+{L("bmargin")})','MMBtu/hr',N2,bold=True)
row(we,E,'bchk','Burner vs model maximum',f'=IF(AND(ISNUMBER({E["selburn"]}),{E["selburn"]}>0),IF({E["bsize"]}<={E["selburn"]},"WITHIN MODEL BURNER RATING","EXCEEDS MODEL BURNER RATING - next size or bigger burner"),"model burner rating not entered")','')
row(we,E,'bsqin','Burner face area at flux',f'={E["bsize"]}*1000000/{L("burnerflux")}','in²',N0,note='Drying Rates Calculator method')
row(we,E,'b4812','48 in × 12 in burners',f'={E["bsqin"]}/576','count',N1)
row(we,E,'b340','3.375 in × 40 in burners',f'={E["bsqin"]}/135','count',N1)
row(we,E,'bmop','Oven-pack style burner index (MMBtu/hr × 100)',f'=ROUNDUP({E["bsize"]}*100,-1)','',N0,note='470 MOP was picked for 5.7 MMBtu/hr in Feb 2026; confirm against the vendor curve')
sec(we,r,'FAN, DUCT, CYCLONE',2,5); r+=1
row(we,E,'facfm','Exhaust fan volume',f'={H["acfm"]}','ACFM',N0,link=True)
row(we,E,'ftemp','At temperature',f'={L("tgout")}','°F',N0,link=True)
row(we,E,'fbhp','Fan brake horsepower',f'={E["facfm"]}*{L("sp")}/(6356*{L("fanef")})','bhp',N1,note='Original DESIGN B29 used ACFM×18×5.2/33000×1.75')
row(we,E,'fhp','Fan motor',f'=INDEX(Tables!$B$4:$B$21,COUNTIF(Tables!$B$4:$B$21,"<"&{E["fbhp"]}*1.15)+1)','hp',N0,bold=True,note='Next standard motor above bhp × 1.15')
row(we,E,'ductd','Exhaust duct diameter at duct velocity',f'=SQRT({E["facfm"]}/{L("ductv")}*4/PI())*12','in',N1)
row(we,E,'ductsel','Exhaust duct, even inches',f'=CEILING({E["ductd"]},2)','in',N0,bold=True)
row(we,E,'ductv','Actual velocity in selected duct',f'={E["facfm"]}/(PI()/4*({E["ductsel"]}/12)^2)','fpm',N0)
row(we,E,'indd','Furnace-to-drum duct at inlet temperature',f'=CEILING(SQRT({H["acfmin"]}/{L("ductv")}*4/PI())*12,2)','in',N0)
row(we,E,'cycin','Cyclone inlet area at inlet velocity',f'={E["facfm"]}/{L("cycv")}*144','in²',N0,note='Hand ACFM and temperature to the MCE cyclone calculator for the model')
row(we,E,'cycd','Cyclone barrel, Lapple proportions (inlet = D/2 × D/4)',f'=SQRT({E["facfm"]}/{L("cycv")}/0.125)*12','in',N0,note='Indicative only')
sec(we,r,'MATERIAL HANDLING',2,5); r+=1
row(we,E,'pcfm','Dried product volume',f'={H["prod"]}/{L("bd")}/60','ft³/min',N2)
row(we,E,'wcfm','Wet feed volume',f'={L("wet")}/{L("bdwet")}/60','ft³/min',N2)
row(we,E,'alout','Discharge airlock (smallest with capacity ≥ product volume at 30% fill)',f'=IFERROR(INDEX(Tables!$E$4:$E$13,COUNTIF(Tables!$H$4:$H$13,"<"&{E["pcfm"]})+1),"none in table")','',N0,bold=True)
row(we,E,'alin','Infeed airlock (≥ wet feed volume)',f'=IFERROR(INDEX(Tables!$E$4:$E$13,COUNTIF(Tables!$H$4:$H$13,"<"&{E["wcfm"]})+1),"none in table")','',N0,bold=True)
row(we,E,'screw','Infeed screw (≥ wet feed ft³/hr at 30% fill)',f'=IFERROR(INDEX(Tables!$J$4:$J$13,COUNTIF(Tables!$M$4:$M$13,"<"&{E["wcfm"]}*60)+1),"none in table")','in',N0)
sec(we,r,'ANNUAL',2,5); r+=1
row(we,E,'hrs','Operating hours',f'={L("hrsyr")}','h/yr',N0,link=True)
row(we,E,'prodyr','Dried product',f'={H["prod"]}*{E["hrs"]}/2000','tons/yr',N0)
row(we,E,'wateryr','Water removed',f'={H["evap"]}*{E["hrs"]}/2000','tons/yr',N0)
row(we,E,'fuelyr','Purchased fuel',f'={H["fuelp"]}*{E["hrs"]}/2000','tons/yr',N0)
row(we,E,'mmbtuyr','Purchased fuel energy',f'={H["qpurch"]}*{E["hrs"]}/1000000','MMBtu/yr',N0)
row(we,E,'fuelcost','Fuel cost',f'={E["mmbtuyr"]}*{L("fuelcost")}','$/yr','$#,##0')
row(we,E,'fuelton','Fuel cost per ton of product',f'=IF({E["prodyr"]}>0,{E["fuelcost"]}/{E["prodyr"]},0)','$/ton','$#,##0.00',bold=True)
we.freeze_panes='B3'
wh[H['model'].split('!')[1].replace('$','')].value='='+E['sel']
wh[H['vol'].split('!')[1].replace('$','')].value='='+E['selvol']

# ===================== TABLES =====================
wt=wb.create_sheet('Tables'); widths(wt,[2,12,3,12,10,10,8,12,3,12,12,8,12,12])
wt['B1']='REFERENCE TABLES'; wt['B1'].font=F_H
wt['B3']='Std motor hp'; wt['B3'].font=F_B
for i,h in enumerate([5,7.5,10,15,20,25,30,40,50,60,75,100,125,150,200,250,300,350]): wt.cell(4+i,2,h).font=F_IN
hdr(wt,3,['Airlock size','cf/rev','rpm','fill','cf/min'],5)
al=[(1212,0.68,25),(1616,1.69,43),(2020,3.2,25),(2040,6.4,20),(2424,5.94,25),(3030,11.2,35),(3636,19.9,32),(4242,32.1,30),(4848,48,24),(6060,93,20)]
al.sort(key=lambda x:x[0]*x[1]*x[2])
for i,(s,cfr,rpm) in enumerate(al):
    rr=4+i; wt.cell(rr,5,s).font=F_IN; wt.cell(rr,6,cfr).font=F_IN; wt.cell(rr,7,rpm).font=F_IN; wt.cell(rr,8,f'=F{rr}*G{rr}*0.3'); wt.cell(rr,8).number_format=N1
wt.cell(4+len(al),5,'Source: original DESIGN K8:N19, 30% fill').font=F_NOTE
hdr(wt,3,['Screw size in','cf/hr/rpm','rpm','cf/hr @30%'],10)
sc=[(4,1.35,70),(6,4.91,60),(9,17.98,55),(12,42.5,50),(14,68.64,50),(16,102.96,35),(18,148.8,45),(20,207.24,40),(24,359.7,40),(30,712.8,35)]
for i,(s,c,rpm) in enumerate(sc):
    rr=4+i; wt.cell(rr,10,s).font=F_IN; wt.cell(rr,11,c).font=F_IN; wt.cell(rr,12,rpm).font=F_IN; wt.cell(rr,13,f'=K{rr}*L{rr}*0.3'); wt.cell(rr,13).number_format=N0
wt.cell(4+len(sc),10,'Source: original DESIGN K22:N32').font=F_NOTE

# ===================== EMISSIONS =====================
wx=wb.create_sheet('Emissions'); widths(wx,[2,44,14,12,14,12,12,60])
wx['B1']='EMISSIONS ESTIMATE  ·  potential to emit  ·  factors are placeholders to confirm against EPA AP-42'; wx['B1'].font=F_H
X={}; r=3
sec(wx,r,'INPUTS (blue)',2,8); r+=1
def xin(name,label,val,unit,note,fmt=N2):
    global r
    wx.cell(r,2,label).font=F_LABEL; c=wx.cell(r,3,val); c.font=F_IN; c.number_format=fmt; c.border=BOX; wx.cell(r,4,unit).font=F_LABEL; wx.cell(r,8,note).font=F_NOTE
    X[name]=f"Emissions!$C${r}"; r+=1
xin('nox','NOx factor',0.10,'lb/MMBtu','NG ~0.1; wood ~0.22; original COMB used 5.5% fuel N to NOx')
xin('co','CO factor',0.08,'lb/MMBtu','NG ~0.08; wood ~0.6')
xin('so2','SO2 factor',0.0006,'lb/MMBtu','NG ~0.0006; wood 0.025',N4)
xin('voc','VOC factor',0.9,'lb/OD ton product','Original Emiss. I29 (softwood shavings); AP-42 by species')
xin('pm','PM uncontrolled',3.0,'lb/OD ton product','Rotary wood dryer AP-42 range ~1–6; original used product×(1−0.99965)')
xin('cyc','Cyclone collection efficiency',0.90,'fraction','Original 99.965% is not achievable with a cyclone',P1)
xin('pm10','PM10 share of PM',0.70,'fraction','Original 0.007%',P1)
xin('hap','HAP share of VOC',0.15,'fraction','Original Emiss. I33',P1)
sec(wx,r,'RESULTS',2,8); r+=1
hdr(wx,r,['Pollutant','lb/hr','tons/yr at operating hours','tons/yr PTE (8,760 h)','lb/OD ton','lb/MMBtu'],2); r+=1
odton=f'({H["solids"]}/2000)'
lines=[('CO2',f'={H["fuel"]}*{L("co2fuel")}'),('NOx',f'={H["qdesign"]}/1000000*{X["nox"]}'),('CO',f'={H["qdesign"]}/1000000*{X["co"]}'),('SO2',f'={H["qdesign"]}/1000000*{X["so2"]}'),
       ('VOC',f'={X["voc"]}*{odton}'),('HAPs',f'={X["hap"]}*{X["voc"]}*{odton}'),('PM after cyclone',f'={X["pm"]}*{odton}*(1-{X["cyc"]})'),('PM10 after cyclone',f'={X["pm"]}*{odton}*(1-{X["cyc"]})*{X["pm10"]}')]
for name,f in lines:
    wx.cell(r,2,name).font=F_LABEL; c=wx.cell(r,3,f); c.number_format=N2; c.border=BOX
    wx.cell(r,4,f'=C{r}*{L("hrsyr")}/2000').number_format=N2; wx.cell(r,5,f'=C{r}*8760/2000').number_format=N2
    wx.cell(r,6,f'=C{r}/{odton}').number_format=N3; wx.cell(r,7,f'=C{r}/({H["qdesign"]}/1000000)').number_format=N4
    for cc in (4,5,6,7): wx.cell(r,cc).border=BOX
    r+=1


# ===================== BIOCHAR REACTOR =====================
wr=wb.create_sheet('Biochar Reactor'); widths(wr,[2,50,16,14,62])
wr['B1']='BIOCHAR REACTOR  ·  slow pyrolysis / torrefaction option  ·  imperial'; wr['B1'].font=F_H
wr['B2']='Mass and energy balance for an indirect-fired rotary reactor. Blue = input. Volatiles are burned in an afterburner; surplus heat can be credited to the dryer (Inputs: coupling = Yes).'; wr['B2'].font=F_NOTE
R={}; r=4
def rin(name,label,val,unit,note='',fmt=N0):
    global r
    wr.cell(r,2,label).font=F_LABEL; c=wr.cell(r,3,val); c.font=F_IN; c.number_format=fmt; c.border=BOX; wr.cell(r,4,unit).font=F_LABEL
    if note: wr.cell(r,5,note).font=F_NOTE
    R[name]=f"'Biochar Reactor'!$C${r}"; r+=1
sec(wr,r,'INPUTS',2,5); r+=1
rin('src','Feed source','Dryer product','','Dryer product (takes rate and moisture from HMB) or Manual (enter below)')
rin('feedm','Manual feed rate, wet',2000,'lb/hr','Used only when source = Manual')
rin('mcm','Manual feed moisture, wet basis',0.10,'','',P1)
rin('tfeed','Feed temperature',150,'°F','Dryer product arrives hot; ambient if from storage')
rin('hhv','Feed heating value, dry basis',8000,'Btu/lb','Wood ~8,000–8,600 dry')
rin('ash','Ash, dry basis',0.02,'','',P1)
rin('treac','Reactor solids temperature',932,'°F','500 °C = 932 °F slow pyrolysis; torrefaction 480–570 °F')
rin('yield','Char yield, dry basis',0.28,'fraction of dry feed','MCE default, confirmed J. Shipley 9 Sep 2026. See table at right; Prozus report assumed 1.0, which is why its 67% product was wrong',P0)
rin('hhvchar','Char heating value',12500,'Btu/lb','Wood char 11,500–13,500 dry')
rin('qrxn','Reaction heat',100,'Btu/lb dry feed','MCE default, confirmed J. Shipley 9 Sep 2026; + endothermic, wood slow pyrolysis roughly 0 to +200')
rin('cps','Specific heat, dry feed',0.35,'Btu/lb·°F','',N2)
rin('tgas','Volatile gas temperature leaving reactor',900,'°F','')
rin('loss','Reactor shell loss',0.05,'fraction of demand','Indirect fired, insulated',P0)
rin('etaab','Afterburner combustion efficiency',0.90,'fraction','Share of volatile energy recovered as hot gas',P0)
rin('tfg','Afterburner flue gas temperature',1600,'°F','Sets the gas volume available to the reactor jacket and dryer')
rin('tjout','Jacket gas outlet temperature',700,'°F','Flue gas leaves the reactor jacket above the solids temperature')
rin('res','Residence time',30,'min','Slow pyrolysis 20–60 min; torrefaction 15–30')
rin('fillr','Reactor fill',0.15,'fraction','',P0)
rin('bdr','Feed bulk density',8,'lb/ft³','',N1)
rin('diar','Reactor drum diameter',5,'ft','Pick; length is sized below. Go up a size if L/D exceeds 10',N1)
rin('flux','Allowable indirect shell heat flux',4000,'Btu/hr·ft²','MCE default, confirmed J. Shipley 9 Sep 2026; indirect rotary reactors 2,000–6,000')
# yield table
wr['G4']='CHAR YIELD GUIDE (wood, dry basis)'; wr['G4'].font=F_B
hdr(wr,5,['Solids temp °F','Yield'],7)
for i,(t,y) in enumerate([(480,0.85),(570,0.70),(750,0.40),(840,0.33),(932,0.28),(1100,0.24),(1300,0.21)]):
    wr.cell(6+i,7,t).font=F_IN; c=wr.cell(6+i,8,y); c.font=F_IN; c.number_format=P0
wr.cell(13,7,'Torrefaction 480–570 °F keeps 70–85%; slow pyrolysis 840–1,100 °F gives 24–33%. Confirm on a sample.').font=F_NOTE
wr.column_dimensions['G'].width=16; wr.column_dimensions['H'].width=10
sec(wr,r,'MASS BALANCE',2,5); r+=1
def rrow(name,label,f,unit,fmt=N0,bold=False,note=''):
    global r
    wr.cell(r,2,label).font=F_B if bold else F_LABEL; c=wr.cell(r,3,f); c.number_format=fmt; c.border=BOX; c.font=F_B if bold else F_LABEL; wr.cell(r,4,unit).font=F_LABEL
    if note: wr.cell(r,5,note).font=F_NOTE
    R[name]=f"'Biochar Reactor'!$C${r}"; r+=1
rrow('feed','Feed, wet',f'=IF({R["src"]}="Dryer product",{H["prod"]},{R["feedm"]})','lb/hr')
rrow('mc','Feed moisture',f'=IF({R["src"]}="Dryer product",{L("mcout")},{R["mcm"]})','',P1)
rrow('dry','Dry feed',f'={R["feed"]}*(1-{R["mc"]})','lb/hr')
rrow('water','Water in feed',f'={R["feed"]}*{R["mc"]}','lb/hr')
rrow('char','Biochar out',f'={R["dry"]}*{R["yield"]}','lb/hr',bold=True)
rrow('chartph','Biochar out',f'={R["char"]}/2000','TPH',N2)
rrow('vol','Volatiles + gas',f'={R["dry"]}-{R["char"]}','lb/hr')
rrow('yieldwet','Char as share of wet feed',f'={R["char"]}/{R["feed"]}','',P1)
sec(wr,r,'ENERGY',2,5); r+=1
rrow('qheat','Heat dry feed to reactor temperature',f'={R["dry"]}*{R["cps"]}*({R["treac"]}-{R["tfeed"]})','Btu/hr')
rrow('qwat','Evaporate and superheat feed moisture',f'={R["water"]}*(1.01*(212-{R["tfeed"]})+970.4+0.45*({R["tgas"]}-212))','Btu/hr')
rrow('qr','Reaction heat',f'={R["dry"]}*{R["qrxn"]}','Btu/hr')
rrow('qvol','Heat volatiles to gas outlet temperature (above solids)',f'={R["vol"]}*0.45*MAX(0,{R["tgas"]}-{R["treac"]})','Btu/hr')
rrow('qdem','Reactor heat demand incl. shell loss',f'=({R["qheat"]}+{R["qwat"]}+{R["qr"]}+{R["qvol"]})*(1+{R["loss"]})','Btu/hr',bold=True)
rrow('qdemMM','Reactor heat demand',f'={R["qdem"]}/1000000','MMBtu/hr',N2)
rrow('evol','Energy in volatiles (HHV basis)',f'={R["dry"]}*{R["hhv"]}*(1-{R["ash"]})-{R["char"]}*{R["hhvchar"]}','Btu/hr',note='Feed energy minus char energy; the standard estimate for pyrolysis gas plus tar')
rrow('evolMM','Energy in volatiles',f'={R["evol"]}/1000000','MMBtu/hr',N2)
rrow('eab','Hot gas from afterburner',f'={R["evol"]}*{R["etaab"]}','Btu/hr')
rrow('jfrac','Share of afterburner heat usable in the jacket',f'=({R["tfg"]}-{R["tjout"]})/({R["tfg"]}-{L("tamb")})','fraction',N3,note='Gas cools from flue temperature to jacket outlet; the rest leaves with the gas')
rrow('ejacket','Heat deliverable to reactor through jacket',f'={R["eab"]}*{R["jfrac"]}','Btu/hr')
rrow('aux','Auxiliary fuel needed at reactor',f'=MAX(0,{R["qdem"]}-{R["ejacket"]})','Btu/hr',bold=True,note='Zero means autothermal on its own volatiles')
rrow('surplus','Surplus heat available to dryer',f'=MAX(0,{R["eab"]}-{R["qdem"]})','Btu/hr',bold=True,note='Afterburner gas beyond reactor demand; credited on HMB when coupling = Yes')
rrow('surplusMM','Surplus heat available to dryer',f'={R["surplus"]}/1000000','MMBtu/hr',N2)
rrow('auto','Status',f'=IF({R["aux"]}=0,"AUTOTHERMAL: volatiles cover the reactor","NEEDS "&TEXT({R["aux"]}/1000000,"0.00")&" MMBtu/hr AUXILIARY FUEL")','')
rrow('fg','Afterburner flue gas mass',f'={R["eab"]}/(0.27*({R["tfg"]}-{L("tamb")}))','lb/hr',note='Includes combustion and dilution air to hold the flue temperature')
rrow('fgacfm','Afterburner flue gas volume at flue temperature',f'={R["fg"]}/(0.0765*530/(460+{R["tfg"]}))/60','ACFM')
sec(wr,r,'REACTOR SIZING',2,5); r+=1
rrow('vreq','Reactor volume for residence time at fill',f'={R["feed"]}/60/{R["bdr"]}*{R["res"]}/{R["fillr"]}','ft³',N0)
rrow('area','Cross-section at chosen diameter',f'=PI()/4*{R["diar"]}^2','ft²',N1)
rrow('lreq','Reactor length for residence time',f'={R["vreq"]}/{R["area"]}','ft',N1,bold=True)
rrow('shell','Shell area at that length',f'=PI()*{R["diar"]}*{R["lreq"]}','ft²',N0)
rrow('fluxa','Indirect heat flux at that shell area',f'={R["qdem"]}/{R["shell"]}','Btu/hr·ft²',N0,bold=True)
rrow('lflux','Reactor length for allowable heat flux',f'={R["qdem"]}/{R["flux"]}/(PI()*{R["diar"]})','ft',N1,bold=True)
rrow('lsel','Reactor length to quote (larger of the two)',f'=CEILING(MAX({R["lreq"]},{R["lflux"]}),1)','ft',N0,bold=True)
rrow('ld','Length to diameter',f'={R["lsel"]}/{R["diar"]}','',N1,note='4–10 typical for rotary reactors; go up a diameter if above 10')
rrow('fluxchk','Heat transfer check',f'=IF({R["fluxa"]}<={R["flux"]},"RESIDENCE TIME GOVERNS THE LENGTH","HEAT FLUX GOVERNS: length set by shell area")','')
wr.freeze_panes='B4'
_c=wh[H['credit'].split('!')[1].replace('$','')]; _c.value=_c.value.replace("'Biochar Reactor'!$C$40",R['surplus'])

# ===================== FLOW (customer schematic) =====================
from openpyxl.drawing.image import Image as XLImage
wf=wb.create_sheet('Flow',2)
NC,NR=70,48; CW=2.6; RH=16.5
for c in range(1,NC+1): wf.column_dimensions[get_column_letter(c)].width=CW
for r_ in range(1,NR+1): wf.row_dimensions[r_].height=RH
wf.sheet_view.showGridLines=False
F_T=Font(name='Arial',size=16,bold=True); F_V=Font(name='Arial',size=12,bold=True); F_U=Font(name='Arial',size=9); F_HDR=Font(name='Arial',size=9,bold=True); F_INFO=Font(name='Arial',size=11); F_INFOB=Font(name='Arial',size=11,bold=True)
YEL=PatternFill('solid',fgColor='FFFF00'); thin_k=Side(style='thin',color='000000')
def M(c0,r0,c1,r1): wf.merge_cells(start_row=r0+1,start_column=c0+1,end_row=r1+1,end_column=c1+1)
def T(c,r,v,font=F_LABEL,al='left',fmt=None):
    x=wf.cell(r+1,c+1,v); x.font=font; x.alignment=Alignment(horizontal=al,vertical='center'); 
    if fmt: x.number_format=fmt
    return x
def vbox(c0,r0,w,title,lines):
    # header row + one row per (formula,unit,fmt); value right-aligned bold over w-4 cols, unit over 4 cols
    M(c0,r0,c0+w-1,r0); h=T(c0,r0,title,F_HDR,'center'); h.fill=YEL
    for cc in range(c0,c0+w): wf.cell(r0+1,cc+1).fill=YEL
    for i,(f,unit,fmt) in enumerate(lines):
        rr=r0+1+i
        M(c0,rr,c0+w-5,rr); T(c0,rr,f,F_V,'right',fmt); M(c0+w-4,rr,c0+w-1,rr); T(c0+w-4,rr,' '+unit,F_U,'left')
    r1=r0+len(lines)
    for rr in range(r0,r1+1):
        for cc in range(c0,c0+w):
            x=wf.cell(rr+1,cc+1); x.border=Border(top=thin_k if rr==r0 else None,bottom=thin_k if rr==r1 else None,left=thin_k if cc==c0 else None,right=thin_k if cc==c0+w-1 else None)
# header / title
T(2,0,'Prepared by:',F_U); M(6,0,16,0); T(6,0,f'={L("prep")}',F_U)
M(26,0,44,0); T(26,0,f'={L("customer")}',Font(name='Arial',size=10,bold=True),'center'); M(26,1,44,1); T(26,1,f'={L("location")}',Font(name='Arial',size=10,bold=True),'center')
M(58,0,68,0); T(58,0,f'={L("date")}',F_U,'right','mm/dd/yyyy')
M(2,2,16,2); T(2,2,f'={L("job")}',Font(name='Arial',size=14,bold=True))
M(20,2,52,2); T(20,2,'DEHYDRATION SYSTEM MASS-ENERGY BALANCE',F_T,'center')
wf.row_dimensions[3].height=20
# info lines
M(4,4,7,4); T(4,4,f'={L("wet")}/2000',F_INFOB,'right',N2); M(9,4,26,4); T(9,4,f'=" TPH wet "&{L("material")}',F_INFO)
M(4,5,7,5); T(4,5,f'={L("wet")}/({L("bdwet")}*27)',F_INFO,'right',N2); M(9,5,26,5); T(9,5,f'=" C.Y./hr @ "&TEXT({L("bdwet")}*27,"0")&" lb/C.Y. and "&TEXT({L("mcin")},"0%")&" moisture"',F_INFO)
M(4,6,7,6); T(4,6,f'=IF(ISNUMBER({E["seldia"]}),TEXT({E["seldia"]},"0")&"x"&TEXT({H["lensel"]},"0"),"")',F_INFOB,'right'); M(9,6,26,6); T(9,6,f'=" "&{L("dtype")}&" · "&{E["sel"]}',F_INFO)
T(2,7,'Elevation',Font(name='Arial',size=10,bold=True),'right'); M(4,7,7,7); T(4,7,f'={L("elev")}',F_INFO,'right',N0); M(9,7,26,7); T(9,7,' feet (above sea level)',F_INFO)
# value boxes
vbox(2,9,11,'Fuel to Burner',[(f'={L("fuel")}','',None),(f'={L("hhv")}','Btu/lb',N0),(f'={H["fuelp"]}','lb/hr',N0),(f'={H["qpurch"]}/1000000','MMBtu/hr',N2)])
M(26,9,31,9); T(26,9,f'={H["btulb"]}',Font(name='Arial',size=12,bold=True,italic=True),'right',N0); M(32,9,44,9); T(32,9," Btu's/lb evaporation (rigorous)",Font(name='Arial',size=12,bold=True,italic=True))
vbox(14,12,9,'Make-Up Air',[(f'={H["scfmdil"]}','SCFM',N0),(f'={L("tamb")}','deg F',N0)])
vbox(27,12,10,'Mixed Inlet Gases',[(f'={H["scfmin"]}','SCFM',N0),(f'={L("tgin")}','deg F',N0)])
vbox(2,25,11,'Combustion Air',[(f'={H["cairacfm"]}','ACFM',N0),(f'={L("tamb")}','deg F',N0),(f'={L("xs")}','X-S air',P0)])
vbox(23,23,11,'Wet Feed',[(f'={L("mcin")}','moisture',P1),(f'={H["solids"]}','lb/hr solids',N0),(f'={H["win"]}','lb/hr water',N0),(f'={L("wet")}','lb/hr total',N0)])
M(37,25,47,25); T(37,25,'EVAPORATION RATE',Font(name='Arial',size=10,bold=True),'center')
M(37,26,41,26); T(37,26,f'={H["evap"]}',F_V,'right',N0); M(42,26,47,26); T(42,26,' LB/HR H2O',F_U)
M(36,28,52,28); T(36,28,f'={E["sel"]}&"  ·  "&TEXT({H["lensel"]},"0")&" ft long  ·  "&TEXT({E["bsize"]},"0.0")&" MMBtu/hr burner"',Font(name='Arial',size=9,italic=True),'center')
vbox(55,3,11,'Exhaust Gases',[(f'={H["acfm"]}','ACFM',N0),(f'={E["fhp"]}','hp fan',N0)])
vbox(55,7,11,'Dryer Outlet Gases',[(f'={H["acfm"]}','ACFM',N0),(f'={L("tgout")}','deg F',N0)])
vbox(55,31,11,'Dry Material',[(f'={L("mcout")}','moisture',P1),(f'={H["solids"]}','lb/hr solids',N0),(f'={H["wout"]}','lb/hr water',N0),(f'={H["prod"]}','lb/hr total',N0),(f'={L("tout")}','deg F',N0)])
vbox(38,29,10,'Dry Fuel (product burned)',[(f'={H["fuelburn"]}','lb/hr total',N0)])
vbox(38,33,10,'Net Dry Product',[(f'={H["netprod"]}','lb/hr total',N0)])
# footer
M(2,46,30,46); T(2,46,f'={L("docno")}&"  Rev "&{L("rev")}&"   ·   FLOW"',F_U)
M(31,46,50,46); T(31,46,'MIDWEST CUSTOM ENGINEERING, INC.  ·  Stuart, FL  ·  usemce.com',Font(name='Arial',size=9,bold=True),'center')
M(58,46,68,46); T(58,46,'Page 1/1',F_U,'right')
# logo (openpyxl creates the drawing part; shapes are appended after save)
img=XLImage('/home/user/CRM/docs/engineering/dryer-hmb-calculator/mce_logo.png'); img.width=330; img.height=int(330*img.height/img.width) if False else 101
img.anchor='C38'; wf.add_image(img)
D='/home/user/CRM/docs/engineering/dryer-hmb-calculator/'
im=XLImage(D+'img_dryer.png'); im.width=int(19*23); im.height=int(19*23*503/1245); im.anchor=get_column_letter(34)+'17'; wf.add_image(im)
im=XLImage(D+'img_cyclone.png'); im.height=int(15*22); im.width=int(15*22*414/1288); im.anchor=get_column_letter(58)+'15'; wf.add_image(im)
im=XLImage(D+'img_fan.png'); im.width=int(7.5*23); im.height=int(7.5*23*729/900); im.anchor=get_column_letter(44)+'4'; wf.add_image(im)
wf.print_area='A1:BQ48'; wf.page_setup.orientation='landscape'; wf.page_setup.paperSize=1; wf.sheet_properties.pageSetUpPr.fitToPage=True; wf.page_setup.fitToWidth=1; wf.page_setup.fitToHeight=1
wf.page_margins.left=0.4; wf.page_margins.right=0.4; wf.page_margins.top=0.4; wf.page_margins.bottom=0.4
FLOW_SHAPES=dict(CW=CW,RH=RH)

# ===================== METRIC =====================
wmt=wb.create_sheet('Metric'); widths(wmt,[2,44,16,12,50])
wmt['B1']='METRIC SUMMARY  ·  converted from the imperial sheets'; wmt['B1'].font=F_H
r=3
def mrow(label,f,unit,fmt=N1,note=''):
    global r
    wmt.cell(r,2,label).font=F_LABEL; c=wmt.cell(r,3,f); c.number_format=fmt; c.border=BOX; c.font=F_LINK; wmt.cell(r,4,unit).font=F_LABEL
    if note: wmt.cell(r,5,note).font=F_NOTE
    r+=1
sec(wmt,r,'MASS',2,5); r+=1
mrow('Wet feed',f'={L("wet")}/2.20462','kg/h',N0); mrow('Wet feed',f'={L("wet")}/2.20462/1000','t/h',N3)
mrow('Dried product',f'={H["prod"]}/2.20462','kg/h',N0); mrow('Water evaporated',f'={H["evap"]}/2.20462','kg/h',N0)
mrow('Moisture in / out (wet basis)',f'=TEXT({L("mcin")},"0.0%")&" / "&TEXT({L("mcout")},"0.0%")','')
sec(wmt,r,'ENERGY',2,5); r+=1
mrow('Theoretical energy per kg water',f'={H["theo"]}*2.326','kJ/kg',N0); mrow('MCE energy factor',f'={H["efac"]}*2.326','kJ/kg',N0)
mrow('Design fired duty',f'={H["qdesign"]}*1.05506/1000000','GJ/h',N3); mrow('Design fired duty',f'={H["qdesign"]}*0.293071/1000','kW',N0)
mrow('Fuel rate',f'={H["fuel"]}/2.20462','kg/h',N1); mrow('Fuel heating value',f'={L("hhv")}*2.326','kJ/kg',N0)
sec(wmt,r,'TEMPERATURES',2,5); r+=1
mrow('Product in / out',f'=TEXT(({L("tin")}-32)*5/9,"0")&" / "&TEXT(({L("tout")}-32)*5/9,"0")','°C')
mrow('Gas in / out',f'=TEXT(({L("tgin")}-32)*5/9,"0")&" / "&TEXT(({L("tgout")}-32)*5/9,"0")','°C')
sec(wmt,r,'GAS',2,5); r+=1
mrow('Hot gas to dryer',f'={H["mgas"]}/2.20462','kg/h',N0); mrow('Exhaust total',f'={H["extot"]}/2.20462','kg/h',N0)
mrow('Exhaust volume at exhaust temperature',f'={H["acfm"]}*1.69901','m³/h',N0); mrow('Exhaust volume, normal (0 °C, 1 atm)',f'={H["scfm"]}*1.69901*273.15/294.26','Nm³/h',N0)
sec(wmt,r,'EQUIPMENT',2,5); r+=1
mrow('Selected dryer',f'={E["sel"]}',''); mrow('Drum diameter × length',f'=IF(ISNUMBER({E["seldia"]}),TEXT({E["seldia"]}*0.3048,"0.00")&" × "&TEXT({E["sellen"]}*0.3048,"0.0"),"")','m')
mrow('Burner size with margin',f'={E["bsize"]}*0.293071','MW',N2); mrow('Fan motor',f'={E["fhp"]}*0.7457','kW',N1); mrow('Exhaust duct',f'={E["ductsel"]}*25.4','mm',N0)
mrow('Fan static pressure',f'={L("sp")}*249.09','Pa',N0)


# ===================== SUMMARY =====================
wsum=wb.create_sheet('Summary',1); widths(wsum,[2,44,18,12,52])
wsum['B1']='DRYER SIZING SUMMARY  ·  for quoting'; wsum['B1'].font=F_H
wsum['B2']=f'={L("job")}'; wsum['B2'].font=F_LINK
r=4
def srow(label,f,unit='',fmt=N0,bold=False,note=''):
    global r
    wsum.cell(r,2,label).font=F_B if bold else F_LABEL; c=wsum.cell(r,3,f); c.number_format=fmt; c.border=BOX; c.font=F_LINK; wsum.cell(r,4,unit).font=F_LABEL
    if note: wsum.cell(r,5,note).font=F_NOTE
    r+=1
sec(wsum,r,'PROCESS',2,5); r+=1
srow('Material',f'={L("material")}')
srow('Wet feed',f'={L("wet")}','lb/hr')
srow('Moisture in → out (wet basis)',f'=TEXT({L("mcin")},"0%")&" → "&TEXT({L("mcout")},"0%")')
srow('Dried product',f'={H["prod"]}','lb/hr',bold=True)
srow('Water evaporated',f'={H["evap"]}','lb/hr',bold=True)
srow('Dryer type',f'={L("dtype")}')
srow('Drum inlet / exhaust gas',f'=TEXT({L("tgin")},"0")&" / "&TEXT({L("tgout")},"0")','°F')
sec(wsum,r,'HEAT',2,5); r+=1
srow('Total Btu of system (MCE, '+'1,750 basis)',f'={H["qmceMM"]}','MMBtu/hr',N2,bold=True)
srow('Rigorous check',f'={H["qfiredMM"]}','MMBtu/hr',N2,note='')
srow('Btu per lb water, rigorous',f'={H["btulb"]}','Btu/lb')
srow('Check',f'={H["btuchk"]}')
srow('Fuel',f'={L("fuel")}')
srow('Purchased fuel',f'={H["fuelp"]}','lb/hr',N1)
srow('Reactor heat credited',f'={H["credit"]}/1000000','MMBtu/hr',N2)
sec(wsum,r,'DRYER',2,5); r+=1
srow('Model',f'={E["sel"]}',bold=True)
srow('Drum diameter',f'={E["seldia"]}','ft',N1)
srow('Standard length',f'={E["sellen"]}','ft',N1)
srow('Length to quote',f'={H["lensel"]}','ft',N0,bold=True)
srow('Length note',f'={H["lennote"]}')
srow('Residence time at quoted length and fill target',f'=IF(ISNUMBER({H["lensel"]}),{H["lensel"]}*PI()/4*{E["seldia"]}^2*{L("fill")}/({L("wet")}/60/{L("bdwet")}),"")','min',N1)
srow('Evaporative loading at standard length',f'={H["load"]}','lb/hr·ft³',N2)
srow('Airflow utilization',f'={E["useacfm"]}','',P0)
sec(wsum,r,'EQUIPMENT',2,5); r+=1
srow('Burner, with margin',f'={E["bsize"]}','MMBtu/hr',N2,bold=True)
srow('Burner face area',f'={E["bsqin"]}','in²')
srow('Exhaust fan',f'={E["facfm"]}','ACFM',N0,bold=True)
srow('Fan static / motor',f'=TEXT({L("sp")},"0.0")&" in WC / "&TEXT({E["fhp"]},"0")&" hp"')
srow('Exhaust duct',f'={E["ductsel"]}','in')
srow('Cyclone inlet area (for the cyclone calculator)',f'={E["cycin"]}','in²')
srow('Discharge / infeed airlock',f'={E["alout"]}&" / "&{E["alin"]}')
srow('Infeed screw',f'={E["screw"]}','in')
sec(wsum,r,'ANNUAL',2,5); r+=1
srow('Operating hours',f'={E["hrs"]}','h/yr')
srow('Dried product',f'={E["prodyr"]}','tons/yr')
srow('Purchased fuel energy',f'={E["mmbtuyr"]}','MMBtu/yr')
srow('Fuel cost',f'={E["fuelcost"]}','$/yr','$#,##0')
srow('Fuel cost per ton',f'={E["fuelton"]}','$/ton','$#,##0.00',bold=True)
wsum.cell(r+1,2,'Every value on this page is a link to Inputs, HMB, Equipment or Biochar Reactor. Change nothing here.').font=F_NOTE
wsum.print_area='B1:E'+str(r+1)

# ===================== CASES =====================
wc=wb.create_sheet('Cases'); widths(wc,[2,34,18,18,18,18])
wc['B1']='REFERENCE CASES  ·  copy a column into Inputs to rerun'; wc['B1'].font=F_H
hdr(wc,3,['Input','Track B (this file default)','Prozus track A','LETEK digestate case A','6x24 expected (2005 file)'],2)
cases=[('Material','Wood shavings','Biomass','Chicken manure digestate cake','Grapeskins'),
('Wet feed lb/hr',3000,3000,6430,4300),('Moisture in',0.50,0.35,0.70,0.50),('Moisture out',0.10,0.10,0.15,0.10),
('Product temp in °F',60,60,85,70),('Product temp out °F',200,176,180,160),('Dryer inlet gas °F',600,588,1100,600),('Exhaust gas °F',180,180,230,220),
('Energy factor',1750,1750,1750,1750),('Fuel','Natural Gas','Dry Wood','Biogas 55% CH4','Natural Gas'),
('Note','Original Input sheet basis','Prozus used feed at 100 °C and solids out at 375 °C; not reproduced','From LETEK PFD Rev A, 140 MT/day, 24 h','624DryerExpected20051205.xlsx: 8,400 ACFM, 3.5 MMBtu/h observed')]
for i,rowv in enumerate(cases):
    for j,v in enumerate(rowv):
        c=wc.cell(4+i,2+j,v); c.font=F_B if j==0 else F_IN; c.border=BOX
        if isinstance(v,float) and v<1: c.number_format=P0

wb.calculation.fullCalcOnLoad=True
wb.save(OUT); print('saved',OUT)

# ===================== POST-SAVE: SHAPES ON THE FLOW SHEET =====================
import zipfile, shutil, re, os
COL_EMU=int((FLOW_SHAPES['CW']*7+5)*9525); ROW_EMU=int(FLOW_SHAPES['RH']*12700)
def anc(c,r):
    ci=int(c); ri=int(r); return f'<xdr:col>{ci}</xdr:col><xdr:colOff>{int((c-ci)*COL_EMU)}</xdr:colOff><xdr:row>{ri}</xdr:row><xdr:rowOff>{int((r-ri)*ROW_EMU)}</xdr:rowOff>'
_id=[300]
def nid():
    _id[0]+=1; return _id[0]
def sp(c0,r0,c1,r1,prst,fill,line='000000',text=None,sz=1200,vert=None,flipV=False,lw=12700,bold=True):
    tx=''
    if text:
        va=' vert="vert270"' if vert else ''
        bp=f'<a:bodyPr anchor="ctr"{va} wrap="square" lIns="0" rIns="0"/>'
        tx=f'<xdr:txBody>{bp}<a:lstStyle/><a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="{sz}" b="{1 if bold else 0}"><a:solidFill><a:srgbClr val="000000"/></a:solidFill><a:latin typeface="Arial"/></a:rPr><a:t>{text}</a:t></a:r></a:p></xdr:txBody>'
    fl='<a:noFill/>' if fill is None else f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
    fv=' flipV="1"' if flipV else ''
    return (f'<xdr:twoCellAnchor><xdr:from>{anc(c0,r0)}</xdr:from><xdr:to>{anc(c1,r1)}</xdr:to>'
            f'<xdr:sp macro="" textlink=""><xdr:nvSpPr><xdr:cNvPr id="{nid()}" name="shape{_id[0]}"/><xdr:cNvSpPr/></xdr:nvSpPr>'
            f'<xdr:spPr><a:xfrm{fv}/><a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>{fl}<a:ln w="{lw}"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln></xdr:spPr>{tx}</xdr:sp><xdr:clientData/></xdr:twoCellAnchor>')
def ln(x0,y0,x1,y1,color='0000FF',arrow=False,lw=15875):
    c0,c1=min(x0,x1),max(x0,x1); r0,r1=min(y0,y1),max(y0,y1)
    flipH=x1<x0; flipV=y1<y0
    xf='<a:xfrm'+(' flipH="1"' if flipH else '')+(' flipV="1"' if flipV else '')+'/>'
    tail='<a:tailEnd type="triangle" w="med" len="med"/>' if arrow else ''
    return (f'<xdr:twoCellAnchor><xdr:from>{anc(c0,r0)}</xdr:from><xdr:to>{anc(c1,r1)}</xdr:to>'
            f'<xdr:cxnSp macro=""><xdr:nvCxnSpPr><xdr:cNvPr id="{nid()}" name="line{_id[0]}"/><xdr:cNvCxnSpPr/></xdr:nvCxnSpPr>'
            f'<xdr:spPr>{xf}<a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom><a:ln w="{lw}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>{tail}</a:ln></xdr:spPr></xdr:cxnSp><xdr:clientData/></xdr:twoCellAnchor>')
TAN='D6CDB4'; DRUM='EDEDDF'; CYC='DCE6F1'; BLUE='0000FF'; BLK='000000'
S=[]
# burner
S.append(sp(8,19.3,9,22.3,'rect',TAN)); S.append(sp(9,17,18,24.5,'rect',TAN,text='Burner',sz=1300))
# fuel line (black) and combustion air (blue) into burner stub
S.append(ln(5,13,5,20.3,BLK)); S.append(ln(5,20.3,8,20.3,BLK,True))
S.append(ln(4,25,4,21.5,BLUE)); S.append(ln(4,21.5,8,21.5,BLUE,True))
# inlet gas main line and the two drops
S.append(ln(18,20.8,33.2,20.8,BLUE,True)); S.append(ln(18.5,15,18.5,20.8,BLUE,True)); S.append(ln(32,15,32,20.8,BLUE,True))
# wet feed into dryer
S.append(ln(28,23,28,22.2,BLK)); S.append(ln(28,22.2,33.2,22.2,BLK,True))
# dryer body is the XD render image (added below); keep small inlet/outlet stubs so the lines land on metal
# dryer to cyclone
S.append(ln(51.6,20.6,55,20.6,BLK)); S.append(ln(55,20.6,55,17.8,BLK)); S.append(ln(55,17.8,57.6,17.8,BLK,True))
# cyclone
# cyclone top to fan, fan to exhaust
S.append(ln(60.8,14.6,60.8,12,BLUE)); S.append(ln(60.8,12,47,12,BLUE)); S.append(ln(47,12,47,10.4,BLUE,True))
S.append(ln(49.6,4.2,52.5,4.2,BLUE)); S.append(ln(52.5,4.2,52.5,1.6,BLUE,True))
# cyclone bottom to dry material; dry material to fuel / net product
S.append(ln(60.8,29.2,60.8,31,BLK,True)); S.append(ln(55,30.6,48,30.6,BLUE,True)); S.append(ln(55,34.6,48,34.6,BLUE,True))
SHAPES_XML=''.join(S)
def inject_shapes(path):
    tmp=path+'.tmp'
    with zipfile.ZipFile(path) as zin:
        names=zin.namelist()
        wbxml=zin.read('xl/workbook.xml').decode(); wbrels=zin.read('xl/_rels/workbook.xml.rels').decode()
        rid=re.search(r'<sheet[^>]*name="Flow"[^>]*r:id="(rId\d+)"',wbxml).group(1)
        rel=[m for m in re.findall(r'<Relationship[^>]*/>',wbrels) if f'Id="{rid}"' in m][0]
        target=re.search(r'Target="([^"]+)"',rel).group(1)
        sheetfile='xl/'+target.lstrip('/').replace('xl/','')
        relfile=sheetfile.replace('worksheets/','worksheets/_rels/')+'.rels'
        srels=zin.read(relfile).decode()
        drawing=re.search(r'Target="([^"]*drawing\d+\.xml)"',srels).group(1)
        dfile='xl/drawings/'+os.path.basename(drawing)
        dx=zin.read(dfile).decode()
        assert 'xmlns:a=' in dx, dx[:300]
        if 'xmlns:xdr=' not in dx:
            dx=dx.replace('<wsDr ','<wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" ',1)
        dx=dx.replace('</wsDr>',SHAPES_XML+'</wsDr>').replace('</xdr:wsDr>',SHAPES_XML+'</xdr:wsDr>')
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as zout:
            for n in names:
                zout.writestr(n, dx.encode() if n==dfile else zin.read(n))
    shutil.move(tmp,path); print('shapes injected into',dfile)
inject_shapes(OUT)

print('HMB acfm at',H['acfm'],' evap at',H['evap'])
