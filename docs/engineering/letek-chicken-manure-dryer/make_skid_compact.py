"""Compact reportlab version of the biogas conditioning skid design (MCE-LETEK-BGS-001) for e-mail delivery."""
import io
from pathlib import Path
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Flowable, PageBreak
HERE=Path(__file__).parent; REPO=HERE.parents[2]
OUT=HERE/'MCE-LETEK-BGS-001_Biogas_Conditioning_Skid.pdf'
NAVY=colors.HexColor('#0b2a4a'); RED=colors.HexColor('#c8102e'); GREY=colors.HexColor('#555555'); BLUE=colors.HexColor('#2a7fd4'); FILL=colors.HexColor('#eef3f8')
base=ParagraphStyle('b',fontName='Helvetica',fontSize=8.4,leading=10.6)
cell=ParagraphStyle('c',parent=base,fontSize=7.8,leading=9.6)
small=ParagraphStyle('s',parent=base,fontSize=7.6,leading=9.4,textColor=GREY)
h=ParagraphStyle('h',fontName='Helvetica-Bold',fontSize=11,leading=14,textColor=NAVY,spaceBefore=9,spaceAfter=3)
title=ParagraphStyle('t',fontName='Helvetica-Bold',fontSize=16,leading=19,textColor=NAVY)
note=ParagraphStyle('n',parent=base,backColor=colors.HexColor('#fff6e5'),borderPadding=(4,6,4,6),leftIndent=4)
def P(t,st=cell): return Paragraph(t,st)
def footer(c,doc):
    c.saveState(); c.setFont('Helvetica',7); c.setFillColor(GREY)
    c.drawString(0.6*inch,0.42*inch,'Midwest Custom Engineering, Inc.  -  Stuart, FL  -  usemce.com')
    c.drawRightString(letter[0]-0.6*inch,0.42*inch,'MCE-LETEK-BGS-001 Rev A  -  Confidential  -  page %d'%doc.page); c.restoreState()
doc=BaseDocTemplate(str(OUT),pagesize=letter,leftMargin=0.6*inch,rightMargin=0.6*inch,topMargin=0.55*inch,bottomMargin=0.65*inch,title='MCE-LETEK-BGS-001 Biogas Conditioning Skid',author='Midwest Custom Engineering, Inc.')
W=letter[0]-1.2*inch
doc.addPageTemplates([PageTemplate('p',[Frame(0.6*inch,0.65*inch,W,letter[1]-1.2*inch,id='f')],onPage=footer)])
def tbl(data,cw,head=True):
    t=Table(data,colWidths=cw,repeatRows=1 if head else 0)
    st=[('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#bbbbbb')),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),3),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]
    if head: st+=[('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef5'))]
    t.setStyle(TableStyle(st)); return t

class PFD(Flowable):
    def __init__(self,w): self.width=w; self.height=2.55*inch
    def draw(self):
        c=self.canv; s=self.width/980.0; H=self.height
        def X(x): return x*s
        def Y(y): return H-y*s*0.85
        c.setLineWidth(1.2); c.setStrokeColor(NAVY)
        def arrow(x1,y1,x2,y2,col=NAVY,dash=None):
            c.setStrokeColor(col); c.setFillColor(col)
            if dash: c.setDash(dash)
            c.line(X(x1),Y(y1),X(x2),Y(y2)); c.setDash()
            import math
            a=math.atan2(Y(y2)-Y(y1),X(x2)-X(x1)); L=5
            p=c.beginPath(); p.moveTo(X(x2),Y(y2)); p.lineTo(X(x2)-L*math.cos(a-0.4),Y(y2)-L*math.sin(a-0.4)); p.lineTo(X(x2)-L*math.cos(a+0.4),Y(y2)-L*math.sin(a+0.4)); p.close(); c.drawPath(p,fill=1,stroke=0)
        for x1,x2 in ((20,85),(125,170),(230,270),(330,370),(430,470),(530,570),(630,670),(730,770),(810,850),(900,960)): arrow(x1,150,x2,150)
        c.setStrokeColor(NAVY); c.setDash(4,3); c.line(X(650),Y(120),X(650),Y(70)); c.line(X(650),Y(70),X(500),Y(70)); c.setDash(); arrow(500,70,500,115)
        c.setDash(4,3); c.line(X(50),Y(150),X(50),Y(60)); c.setDash(); arrow(50,60,120,60)
        arrow(400,185,400,235,BLUE); arrow(300,185,300,235,BLUE)
        c.setFillColor(FILL); c.setStrokeColor(NAVY); c.setLineWidth(1)
        for x,y,w,hh in ((85,132,40,36),(170,100,60,100),(270,110,60,75),(370,110,60,75),(470,115,60,70),(670,120,60,60),(770,132,40,36),(850,120,50,60)):
            c.roundRect(X(x),Y(y+hh),X(w),hh*s*0.85,4,fill=1,stroke=1)
        c.circle(X(600),Y(150),30*s,fill=1,stroke=1)
        c.setFillColor(colors.black); c.setFont('Helvetica',6.5)
        for x,y,t in ((105,153,'FA-1'),(200,145,'V-1 / V-2'),(200,158,'iron oxide'),(200,171,'lead / lag'),(300,145,'E-1'),(300,158,'gas cooler'),(400,145,'F-1'),(400,158,'coalescer'),
                      (500,145,'F-2'),(500,158,'filter 5 um'),(600,147,'K-1'),(600,160,'blower'),(700,145,'PCV-1'),(700,158,'2 psig'),(790,153,'FA-2'),(875,145,'to burner'),(875,158,'biogas train'),
                      (52,175,'raw biogas'),(52,187,'from digester'),(85,55,'to flare / vent (by others)'),(575,63,'recycle for pressure control'),(590,205,'AIT: CH4 / H2S / O2'),(200,225,'TI  PDI  AIT(H2S)'),(700,205,'PT  PSL  PSH  FT')):
            c.drawCentredString(X(x),Y(y),t)
        c.setFillColor(BLUE); c.drawCentredString(X(300),Y(250),'condensate 3.8 gal/hr to lagoon'); c.drawCentredString(X(400),Y(250),'condensate')
        c.setFillColor(colors.black); c.setFont('Helvetica-Bold',7)
        c.drawString(X(20),Y(22),'Stream: 232 scfm design (193 normal) - 100 F sat. - 5,000 ppm H2S  ->  40 F dew point, < 200 ppm H2S, 2 psig')

S=[]
hdr=Table([[Paragraph('Biogas Conditioning Skid - Process Design',title),Paragraph('Midwest Custom Engineering, Inc.<br/>Doc. MCE-LETEK-BGS-001 Rev A - 12 Sep 2026<br/>Prepared by: J. Shipley - Budgetary design',ParagraphStyle('r',parent=small,alignment=2))],
            [Paragraph('LETEK DCG / Bachoco layer farms, Merida, Yucatan - chicken manure digestate dryer, 140 MT/day case',small),'']],colWidths=[W*0.62,W*0.38])
hdr.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,-1),(-1,-1),1.5,NAVY),('SPAN',(0,1),(1,1))])); S+=[hdr]
S+=[Paragraph('1. Purpose and design basis',h),Paragraph('Raw digester biogas is saturated with water, carries hydrogen sulfide, and arrives at a few inches of water column. The dryer burner needs dry, low-sulfur gas at a steady 2 psig. The skid does three things in order: bulk H2S removal, moisture removal, and pressure boosting, with flame arresters at both ends and a control panel that hands the burner management system a clean permissive.',base),Spacer(1,4)]
S+=[tbl([[P('<b>Item</b>'),P('<b>Value</b>'),P('<b>Basis</b>')],
 [P('Biogas flow, design case (140 MT/day)'),P('7,455 Nm3/day = 193 scfm'),P('Customer figure, 19 Aug 2026')],
 [P('Skid design flow'),P('232 scfm (+20%)'),P('160 MT/day case and digester swings')],
 [P('Composition'),P('55% CH4, 45% CO2, saturated'),P('Customer figure; analysis pending')],
 [P('Heating value at 193 scfm'),P('5.8 MMBtu/hr LHV (139 MMBtu/day), 6.5 HHV'),P('911 / 1,012 Btu/scf CH4')],
 [P('Share of dryer duty'),P('80% of 7.3 MMBtu/hr normal fire; 58% of 10 MMBtu/hr max'),P('LHV basis; LPG makes up the balance')],
 [P('H2S inlet (assumed)'),P('up to 5,000 ppmv = 5.2 lb/hr H2S, 117 lb/day S'),P('Poultry manure digestate is sulfur-rich; analysis pending')],
 [P('H2S outlet'),P('under 200 ppmv'),P('Burner train, condensate and stack corrosion')],
 [P('Inlet temperature / pressure'),P('95-100 F, 2-8 in WC'),P('Mesophilic digester; to be confirmed')],
 [P('Outlet to burner'),P('2.0 psig, dew point at least 20 F below ambient, under 5 micron particulate'),P('NFPA 86 train, no condensate in the valve train')],
 [P('Site'),P('30 ft elevation, 85-100 F, coastal, wet season'),P('Outdoor skid under a roof')]],[2.1*inch,2.7*inch,W-4.8*inch])]
S+=[Paragraph('2. Process flow',h),PFD(W)]
S+=[Paragraph('3. Sizing',h),tbl([[P('<b>Tag</b>'),P('<b>Equipment</b>'),P('<b>Sizing</b>'),P('<b>Result / selection</b>')],
 [P('FA-1, FA-2'),P('In-line deflagration flame arresters, 316 SS elements'),P('232 scfm, 4 in line, IIA gas group'),P('4 in bidirectional, inlet and outlet of skid')],
 [P('V-1, V-2'),P('Iron-oxide H2S vessels, lead/lag, 304 SS, top-loading, wet change-out'),P('60 s empty-bed contact at design flow: 232 ft3 per vessel; superficial velocity 12 fpm'),P('2 x 5 ft dia x 14 ft T/T, 12 ft bed, about 14,000 lb pelletized iron oxide each (0.15 lb S per lb media)')],
 [P(''),P('Media life, lead vessel'),P('117 lb S/day at 5,000 ppm = 780 lb media/day'),P('18 days at 5,000 ppm; 179 days at 500 ppm. See note below.')],
 [P('E-1'),P('Gas cooler, shell and tube, 316L tubes, glycol chilled'),P('874 lb/hr gas, 100 F to 40 F: 15,800 Btu/hr sensible + 33,400 latent = 49,300 Btu/hr'),P('5-ton air-cooled glycol chiller; removes 32 lb/hr water (3.8 gal/hr); outlet water 4 lb/hr')],
 [P('F-1'),P('Coalescing separator with level-controlled condensate trap, 316L'),P('Liquid-out at design flow, 0.5 in WC drop'),P('4 in coalescer, automatic drainer to condensate line')],
 [P('F-2'),P('Particulate filter, 5 micron, with PDI'),P('232 scfm'),P('Duplex cartridge housing so a change-out does not stop the dryer')],
 [P('K-1'),P('Rotary-lobe biogas blower, gas-tight, explosion-proof motor, VFD'),P('232 scfm from 0 to 2.5 psig; 4.6 shaft hp at 55%'),P('7.5 hp, 480/3/60, VFD on outlet pressure; 20 F of blower heat gives the dew-point margin after cooling')],
 [P('PCV-1'),P('Outlet pressure control valve and recycle valve to blower suction'),P('2.0 psig set, 10:1 turndown with the burner'),P('2 in PCV, 2 in recycle, PT/PSL/PSH to the BMS')],
 [P('AIT-1/2'),P('Gas analyzers, inlet and outlet'),P('CH4, H2S, O2'),P('Outlet H2S high alarm at 200 ppm, trip to LPG at 500 ppm; O2 over 2% trip')],
 [P('LCP-1'),P('Local control panel, NEMA 4X 304 SS'),P('VFD, analyzer inputs, valve outputs, Modbus to burner BMS and plant PLC'),P('Permissives to the burner: gas pressure OK, H2S OK, O2 OK, arrester temperature OK')],
 [P('Skid'),P('Structural steel skid, 304 SS piping (wet side 316L), 4 in main line'),P('Roughly 10 ft x 24 ft footprint, chiller alongside'),P('Ship as two modules: vessels; cooler/blower/controls')]],[0.6*inch,2.0*inch,2.1*inch,W-4.7*inch])]
S+=[Spacer(1,5),Paragraph('<b>H2S loading drives the design.</b> At 5,000 ppm the dry media alone would consume about 780 lb per day, which is neither economical nor practical to change out. The recommended arrangement is bulk removal in the digester by micro-aeration (2 to 4% air into the headspace) or ferric chloride dosing, both by the digester supplier, bringing the gas to 500 ppm or less. The iron-oxide vessels then run as a polishing stage with a 6-month media life. If the digester cannot accept micro-aeration, a biological trickling scrubber ahead of the vessels is the alternative and roughly doubles the skid footprint. The biogas analysis decides this; the vessels and cooler stay the same either way.',note)]
S+=[PageBreak(),Paragraph('4. Mass and energy summary (193 scfm normal flow)',h),
 tbl([[P('<b>Stream</b>'),P('<b>Flow</b>'),P('<b>T</b>'),P('<b>P</b>'),P('<b>Condition</b>')],
 [P('1 Raw biogas'),P('193 scfm, 874 lb/hr gas + 36 lb/hr water'),P('100 F'),P('4 in WC'),P('saturated, 5,000 ppm H2S')],
 [P('2 After V-1/V-2'),P('192 scfm'),P('100 F'),P('2 in WC'),P('under 200 ppm H2S, saturated')],
 [P('3 After E-1 / F-1'),P('192 scfm gas, 4 lb/hr water'),P('40 F'),P('0 in WC'),P('40 F dew point')],
 [P('4 After K-1 / PCV-1'),P('192 scfm'),P('60-70 F'),P('2.0 psig'),P('dew point 20-30 F below gas temperature')],
 [P('C Condensate'),P('32 lb/hr, 3.8 gal/hr'),P('40 F'),P('-'),P('acidic, to lagoon or digester')],
 [P('S Spent media'),P('14,000 lb per change-out'),P('-'),P('-'),P('non-hazardous after air passivation; landfill')]],[1.3*inch,2.3*inch,0.6*inch,0.7*inch,W-4.9*inch]),Spacer(1,6),
 tbl([[P('<b>Utility</b>'),P('<b>Demand</b>')],[P('Electrical, blower K-1'),P('7.5 hp, 5.6 kW at design')],[P('Electrical, chiller'),P('5 ton, about 6 kW')],[P('Electrical, controls and analyzers'),P('1 kW')],
      [P('Total connected'),P('approx. 13 kW, 480/3/60')],[P('Nitrogen for purge and change-out'),P('bottled, 2 cylinders on site')],[P('Instrument air'),P('none (electric actuators)')],[P('Condensate disposal'),P('3.8 gal/hr, gravity to lagoon')]],[2.6*inch,W-2.6*inch])]
S+=[Paragraph('5. Safety and controls',h)]
for b in ['Flame arresters at skid inlet and outlet, temperature switches on both; the outlet arrester is the last device before the burner biogas train.',
 'Classified area: Class I Division 2 around the skid; blower motor and instruments rated accordingly; skid under a roof, open sides, no enclosure.',
 'Trips to LPG (automatic changeover in the burner BMS): low gas pressure, high H2S, high O2, high blower discharge temperature, arrester high temperature, chiller failure with dew point alarm.',
 'Iron-oxide media is pyrophoric when spent and dry; vessels are changed out wet with nitrogen purge, one vessel at a time (lead/lag lets the dryer keep running).',
 'Condensate is acidic (H2S, CO2); 316L on the cooler, coalescer and condensate piping, 304 SS elsewhere on the skid.',
 'Pressure relief on the blower discharge to the flare/vent header; the digester\'s own flare handles any gas the dryer cannot take.']:
    S.append(Paragraph('- '+b,base))
S+=[Paragraph('6. Information needed to finalize',h),tbl([[P('<b>Item</b>'),P('<b>Why it matters</b>'),P('<b>From</b>')],
 [P('Biogas analysis: CH4, CO2, H2S, O2, N2, moisture, siloxanes'),P('Sets the H2S removal stage (in-digester vs. skid), media life, and whether an activated-carbon polish is needed'),P('LETEK / digester supplier')],
 [P('Digester gas pressure and holder volume'),P('Blower suction design, whether the holder can buffer burner turndown'),P('Digester supplier')],
 [P('Can the digester accept micro-aeration or FeCl3 dosing?'),P('Decides whether the skid is a polish stage (as sized) or needs a biological scrubber'),P('Digester supplier')],
 [P('LPG supply pressure and tank location'),P('Burner changeover and train design'),P('LETEK')],
 [P('Site plan: digester to dryer distance'),P('Line size and blower head; 4 in line assumed for up to 300 ft'),P('LETEK')]],[2.4*inch,3.2*inch,W-5.6*inch])]
S+=[Paragraph('7. Assumptions and confidence',h),Paragraph('Confidence is <b>medium</b> for the cooler, blower and controls (these follow from the flow and composition the customer gave) and <b>low</b> for the H2S stage until the analysis arrives, because a 5,000 ppm assumption versus a 1,500 ppm reality changes the media economics by a factor of three and decides whether in-digester treatment is required. Pricing for this skid follows component quotations and is not included in this document.',base)]
doc.build(S); print('written',OUT.name,OUT.stat().st_size,'bytes')
