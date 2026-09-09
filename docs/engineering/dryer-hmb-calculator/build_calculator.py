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
"4. Metric sheet mirrors the key results in SI units. Emissions sheet gives potential-to-emit.",
"5. Dryer Models: single-pass XD Series rows are filled from MCE documents. Triple-pass rows are empty and waiting for MCE drum data. Z8 eight-pass rows carry the ACFM table from the original workbook. A model is selected automatically as the smallest of the chosen type that meets both airflow and evaporation with the design margin.",
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
"- XD-36 Mk.2 3 ft x 20 ft, 2.5 MMBtu/hr burner: MCE quote to LETEK DCG, Mar 2026; overall dims from the Mk.2 brochure. XD-60 Mk.2 5 ft x 30 ft: GA drawing Apr 2026. XD-72 Mk.2 6 ft dia: Feb 2026 notes (length and burner to confirm). XD-96 Mk.1 8 ft x 40 ft, 30 MMBtu/hr max: operating manual Rev 0.0.",
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
inp('job','Job / customer','Example: wood shavings dryer (case from NT-HMB-2025-001 track B)','', 'Text only')
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
inp('restime','Drum residence time',15,'min','Hold-up check only; 10–30 min typical single pass',N0)
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
inp('tgin','Dryer inlet gas temperature',600,'°F','Design choice. 500–700 °F wood shavings; 900–1,200 °F manure/sludge; original iterated to 588 °F',N0)
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
inp('burnerflux','Burner face heat release',1200,'Btu/hr per in²','Drying Rates Calculator',N0)
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
row(wh,H,'fuelcf','Fuel volume',f'={H["fuel"]}/INDEX(Inputs!$I$13:$I$18,MATCH({L("fuel")},Inputs!$G$13:$G$18,0))/60','ft³/min',N1,note='Gas fuels: ft³/min at standard; solid fuels: bulk ft³/min')
row(wh,H,'cair','Combustion air',f'={H["fuel"]}*{L("stoich")}*(1+{L("xs")})','lb/hr')
row(wh,H,'poc','Products of combustion',f'={H["fuel"]}+{H["cair"]}','lb/hr')
row(wh,H,'pocw','Water in products of combustion',f'={H["fuel"]}*{L("h2ofuel")}+{H["cair"]}*{L("hum")}','lb/hr')
row(wh,H,'tflame','Adiabatic products temperature, approx.',f'={L("tamb")}+{H["qdesign"]}*{L("etacomb")}/(0.27*{H["poc"]})','°F',N0,note='cp 0.27 average; sanity only')
sec(wh,r,'DRYER GAS FLOW',2,5); r+=1
row(wh,H,'mgas','Hot gas to dryer at inlet temperature',f'={H["qdesign"]}*{L("etacomb")}/(0.24*({L("tgin")}-{L("tamb")}))','lb/hr',bold=True,note='Products of combustion plus dilution air, dry basis')
row(wh,H,'mdil','Dilution (make-up) air',f'={H["mgas"]}-{H["poc"]}','lb/hr',note='Must be positive; if negative the inlet temperature is above what this fuel and excess air can give')
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
row(wh,H,'holdvol','Material in drum at residence time',f'={L("wet")}/60*{L("restime")}/{L("bdwet")}','ft³',N1)
row(wh,H,'holdpct','Drum fill',f'=IF({H["vol"]}>0,{H["holdvol"]}/{H["vol"]},"n/a")','fraction',P1,note='Original FLOW used 1.5 minutes of product and read 0.1%; 5–15% is normal')
wh.freeze_panes='B3'

# ===================== DRYER MODELS =====================
wm=wb.create_sheet('Dryer Models'); widths(wm,[2,10,24,9,9,10,10,12,12,13,13,12,12,14,11,44])
wm['B1']='DRYER MODELS  ·  one table, three types  ·  yellow = MCE to fill'; wm['B1'].font=F_H
wm['B2']='Reference evaporative loading for the volume-limited rating, lb/hr·ft³:'; wm['B2'].font=F_LABEL
wm['K2']='Single-pass'; wm['L2']=6.0; wm['M2']='Triple-pass'; wm['N2']=8.0; wm['O2']='Z8'; wm['P2']=8.0
for a in ('L2','N2','P2'): wm[a].font=F_IN; wm[a].number_format=N1
wm['B3']='Rated evaporation = MIN(burner ÷ energy factor, volume × reference loading). Blank burner = volume-limited only. Design ACFM for single-pass = cross-section × face velocity; triple-pass and Z8 use the entered ACFM.'; wm['B3'].font=F_NOTE
hdr(wm,5,['Type','Model','Dia ft','Length ft','Cross-section ft²','Volume ft³','Design ACFM','Max burner MMBtu/hr','Rated evap (burner) lb/hr','Rated evap (volume) lb/hr','Rated evap lb/hr','Meets job? (row)','Overall L×W×H in','Fan hp','Source / status'],2)
M=[]
M+= [('Single-pass rotary drum','XD-36 Mk.2',3,20,None,2.5,'413.9 × 84 × 100.5','','LETEK quote Mar 2026 (2.5 MMBtu MOP burner); Mk.2 brochure dims'),
     ('Single-pass rotary drum','XD-60 Mk.2',5,30,None,None,'','','GA drawing Apr 2026; burner rating to fill'),
     ('Single-pass rotary drum','XD-72 Mk.2',6,30,None,4.7,'','','6 ft dia and 470 MOP burner per 7 Feb 2026 notes; LENGTH TO CONFIRM'),
     ('Single-pass rotary drum','XD-96 Mk.2',8,40,None,30.0,'470 × 224 × 169','','8×40 drum and 30 MMBtu/hr max from XD-96 Mk.1 manual; Mk.2 length assumed same')]
for i in range(1,5):
    M.append(('Triple-pass rotary drum',f'TP-{i} (fill)',None,None,None,None,'','','MCE triple-pass drum data not found in Drive, QBO or email; fill model, OD, length, design ACFM, burner'))
z8=[("6'x24'",6,24,7000),("8'x35'",8,35,18000),("10'x40'",10,40,32000),("10'x50'",10,50,40000),("12'x50'",12,50,55000),("12'x60'",12,60,65000),("12'x70'",12,70,75000),("13'x60'",13,60,80000),("14'x70'",14,70,90000),("15'x70'",15,70,100000)]
for n,d,l,a in z8:
    M.append(('Z8 eight-pass',f'Z8 {n}',d,l,a,None,'','','Original Input K8:L18 ACFM max; burner to fill'))
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
    else:
        c=wm.cell(rr,8,acfm); c.font=F_IN; c.number_format=N0; c.border=BOX
        if acfm is None: c.fill=FILL_Y
    c=wm.cell(rr,9,burner); c.font=F_IN; c.number_format=N1; c.border=BOX
    if burner is None: c.fill=FILL_Y
    ref={'Single-pass rotary drum':'$L$2','Triple-pass rotary drum':'$N$2','Z8 eight-pass':'$P$2'}[typ]
    c=wm.cell(rr,10,f'=IF(I{rr}="","",I{rr}*1000000/{L("efactor")})'); c.number_format=N0; c.border=BOX
    c=wm.cell(rr,11,f'=IF(G{rr}="","",G{rr}*{ref})'); c.number_format=N0; c.border=BOX
    c=wm.cell(rr,12,f'=IF(K{rr}="","",IF(J{rr}="",K{rr},MIN(J{rr},K{rr})))'); c.number_format=N0; c.border=BOX
    c=wm.cell(rr,13,f'=IF(AND(B{rr}={L("dtype")},H{rr}<>"",L{rr}<>"",H{rr}>=HMB!$C$52*(1+{L("smargin")}),L{rr}>={H["evap"]}*(1+{L("smargin")})),ROW(),99999)'); c.number_format=N0; c.border=BOX
    wm.cell(rr,14,dims).font=F_IN; wm.cell(rr,15,fan).font=F_IN; wm.cell(rr,15).fill=FILL_Y
    wm.cell(rr,16,src).font=F_NOTE
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
row(we,E,'fuelyr','Fuel',f'={H["fuel"]}*{E["hrs"]}/2000','tons/yr',N0)
row(we,E,'mmbtuyr','Fuel energy',f'={H["qdesign"]}*{E["hrs"]}/1000000','MMBtu/yr',N0)
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
print('HMB acfm at',H['acfm'],' evap at',H['evap'])
