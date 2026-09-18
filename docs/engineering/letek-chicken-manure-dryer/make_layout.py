"""Preliminary plot plan for the LETEK / Bachoco digestate dryer (base-14 fonts, compact for e-mail).
Rev 1: dryer train drawn from the silhouette of MCE drawing 104400900-OVERVIEW (8 ft x 40 ft XD-96 train),
scale calibrated against the dimensioned field-assembly sheet 104400906 (drum shell 96 in, main frame 466 in); see xd96_silhouette.json.  Everything else is a block estimate.
Page 1: plan view at 1 in = 12 ft.  Page 2: side elevation silhouette, area schedule, utility summary.
No vendor, price or lead time appears here."""
import json, math
from pathlib import Path
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
HERE=Path(__file__).parent
OUT=HERE/'MCE-LETEK-LAY-001_Preliminary_Layout.pdf'
SIL=json.load(open(HERE/'xd96_silhouette.json'))
NAVY=colors.HexColor('#0b2a4a'); RED=colors.HexColor('#c8102e'); GREY=colors.HexColor('#555555'); LIGHT=colors.HexColor('#e8eef5'); DRUM=colors.HexColor('#c9d8ea')
GREEN=colors.HexColor('#1a7f37'); ORANGE=colors.HexColor('#b36b00')
PW,PH=landscape(letter)
SC=inch/12.0                # 1 in = 12 ft
OX,OY=0.55*inch,1.25*inch   # pad origin on page
FT2M2=0.092903; REV='Rev 1'; DATE='17 Sep 2026'
PAD=(124,64)
# dryer train from the drawing: station s (in) from the drop-out end, half-widths (in). Placed with the drop-out end at XE, centerline YC.
XE,YC=90.0,37.0
plan=SIL['plan_envelope_in']; elev=SIL['elevation_envelope_in']
train_len=plan[-1][0]/12; train_w=(max(b for _,a,b in plan)-min(a for _,a,b in plan))/12
def tx(s): return XE-s/12.0               # station -> pad x (ft); burner end to the west
def ty(off): return YC-off/12.0           # drawing +offset (blower side) -> south
STA={k:tuple(v) for k,v in SIL['stations_in'].items()}; HT=SIL['heights_in']; WT=SIL['weights_lb']
BLK=[  # tag, name, x, y, w, h
 ('D-1','Dewatering unit + feed tank\n(dewatered digestate)',22,50,20,14),
 ('P-1','Dried product bunker / bagging',84,50,20,14),
 ('C-1','Cyclone\n+ airlock',94,33,8,8),
 ('F-1','Fan + stack',104,34,8,6),
 ('BGS','Biogas conditioning skid',10,8,24,10),
 ('CH','Chiller',36,10,6,8),
 ('MCC','MCC / control room',50,6,16,12),
 ('LPG','LPG vaporizer / regulator station\n(by others)',108,6,10,10),
]
train_ft2=sum((b-a)/144.0*2 for _,a,b in plan)  # each 2-pt station step = 2*2.991 in
AREAS=[
 ('Dryer train: burner and fuel train, burner housing, feed breeching, 8 ft x 40 ft drum, drop-out box (from drawing 104400900)',round(train_len*train_w),'%.0f ft long x %.0f ft wide overall; drop-out box top %.1f ft, drum centreline %.1f ft above grade; drum and skid 79,900 lb, burner assembly 16,000 lb, drop-out box 9,300 lb'%(train_len,train_w,HT['dropout_box_top']/12,HT['drum_centreline']/12)),
 ('Cyclone and exhaust fan',8*8+8*6,'cyclone approx. 22 ft tall, stack to 35 ft'),
 ('Dewatering unit, feed tank and transfer',20*14,'covered; wash-down floor with drain'),
 ('Dried product bunker / bagging',20*14,'covered, 3-sided; sized for 3 days of product'),
 ('Biogas conditioning skid and chiller',24*10+6*8,'open-sided roof, classified area, 25 ft from ignition sources'),
 ('MCC / control room',16*12,'air-conditioned; 480 V (or 440 V) MCC, PLC, HMI'),
 ('LPG vaporizer / regulator station (by others)',10*10,'tanks outside the pad, 50 ft min. from the dryer per local code'),
]
pad_ft2=PAD[0]*PAD[1]; eq_ft2=sum(a[1] for a in AREAS)
def X(x): return OX+x*SC
def Y(y): return OY+y*SC
def hdr(c,title,sub,page):
    c.setFillColor(NAVY); c.setFont('Helvetica-Bold',13); c.drawString(0.55*inch,PH-0.55*inch,title)
    c.setFont('Helvetica',8.5); c.setFillColor(GREY); c.drawString(0.55*inch,PH-0.72*inch,sub)
    c.drawRightString(PW-0.55*inch,PH-0.72*inch,'MCE-LETEK-LAY-001  %s  -  %s  -  PRELIMINARY, FOR SITE PLANNING ONLY'%(REV,DATE))
    c.setFont('Helvetica',7); c.drawString(0.55*inch,0.4*inch,'Midwest Custom Engineering, Inc.  -  6526 S Kanner Hwy #215, Stuart, FL 34997  -  usemce.com')
    c.drawRightString(PW-0.55*inch,0.4*inch,'page %d of 2'%page)
    c.setStrokeColor(NAVY); c.setLineWidth(1); c.line(0.55*inch,PH-0.8*inch,PW-0.55*inch,PH-0.8*inch)
def poly(c,pts,fill,stroke=NAVY,lw=0.8):
    p=c.beginPath(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    p.close(); c.setFillColor(fill); c.setStrokeColor(stroke); c.setLineWidth(lw); c.drawPath(p,fill=1,stroke=1)
def label(c,x,y,t,col=RED,size=6,font='Helvetica-Oblique'): c.setFont(font,size); c.setFillColor(col); c.drawString(X(x),Y(y),t)
def arrow(c,x1,y1,x2,y2,col=RED):
    c.setStrokeColor(col); c.setLineWidth(1); c.line(X(x1),Y(y1),X(x2),Y(y2))
    a=math.atan2(Y(y2)-Y(y1),X(x2)-X(x1)); s=5
    c.line(X(x2),Y(y2),X(x2)-s*math.cos(a-0.5),Y(y2)-s*math.sin(a-0.5)); c.line(X(x2),Y(y2),X(x2)-s*math.cos(a+0.5),Y(y2)-s*math.sin(a+0.5))
def route(c,pts,col):
    c.setStrokeColor(col); c.setLineWidth(1)
    for (x1,y1),(x2,y2) in zip(pts,pts[1:]): c.line(X(x1),Y(y1),X(x2),Y(y2))
    arrow(c,pts[-2][0],pts[-2][1],pts[-1][0],pts[-1][1],col)

c=canvas.Canvas(str(OUT),pagesize=landscape(letter)); c.setTitle('MCE-LETEK-LAY-001 Preliminary Layout'); c.setAuthor('Midwest Custom Engineering, Inc.')
hdr(c,'Preliminary plot plan - 140 t/day digestate dryer, LETEK DCG / Bachoco, Merida, Yucatan','Plan view, 1 in = 12 ft (1:144).  Pad %d x %d ft (%.0f x %.0f m).'%(PAD[0],PAD[1],PAD[0]*0.3048,PAD[1]*0.3048),1)
c.setStrokeColor(NAVY); c.setLineWidth(1.2); c.setDash(6,3); c.rect(X(0),Y(0),PAD[0]*SC,PAD[1]*SC); c.setDash()
c.setFont('Helvetica',7.5); c.setFillColor(GREY)
c.drawString(X(1),Y(PAD[1])+14,'Concrete equipment pad %d ft x %d ft = %s sq ft (%.0f sq m); roof over dryer train, dewatering and skid recommended (Yucatan rain).'%(PAD[0],PAD[1],format(pad_ft2,','),pad_ft2*FT2M2))
c.drawString(X(1),Y(PAD[1])+5,'Dryer train outline taken from the MCE 8 ft x 40 ft dryer general arrangement; all other items are block estimates.')
# maintenance clearance
c.setStrokeColor(GREY); c.setLineWidth(0.5); c.setDash(2,2); c.rect(X(2),Y(19),112*SC,30*SC); c.setDash()
# blocks
for tag,name,x,y,w,h in BLK:
    c.setFillColor(colors.white if tag=='LPG' else LIGHT); c.setStrokeColor(NAVY); c.setLineWidth(0.9)
    if tag=='LPG': c.setDash(3,2)
    c.rect(X(x),Y(y),w*SC,h*SC,fill=1); c.setDash()
    c.setFillColor(NAVY); c.setFont('Helvetica-Bold',7.5); c.drawString(X(x)+2,Y(y+h)-9,tag)
    c.setFont('Helvetica',6.3); c.setFillColor(colors.black)
    for i,ln in enumerate(name.split('\n')): c.drawString(X(x)+2,Y(y+h)-17-7*i,ln)
    c.setFillColor(GREY); c.setFont('Helvetica',6); c.drawString(X(x)+2,Y(y)+2,'%d x %d ft'%(w,h))
# dryer train silhouette (actual proportions)
top=[(X(tx(s)),Y(ty(a))) for s,a,b in plan]; bot=[(X(tx(s)),Y(ty(b))) for s,a,b in reversed(plan)]
poly(c,top+bot,LIGHT)
# drum body shading and component ticks
s0,s1=STA['XD']; c.setFillColor(DRUM); c.setStrokeColor(NAVY); c.setLineWidth(0.6)
c.rect(X(tx(s1)),Y(YC-HT['plan_outline_inner_od']/24),(s1-s0)/12*SC,HT['plan_outline_inner_od']/12*SC,fill=1)
c.setStrokeColor(NAVY); c.setLineWidth(0.4); c.line(X(tx(s1)),Y(YC),X(tx(s0)),Y(YC))
for s in (STA['DB'][1],STA['FB'][0],STA['BH'][0],STA['BU'][0]):
    c.setDash(1,2); c.line(X(tx(s)),Y(YC-9),X(tx(s)),Y(YC+9)); c.setDash()
c.setFillColor(NAVY); c.setFont('Helvetica-Bold',7.5); c.drawString(X(tx(STA['XD'][1]))+3,Y(YC+6)-2,'XD-96  8 ft dia x 40 ft drum')
c.setFont('Helvetica',6.3); c.setFillColor(colors.black)
c.drawString(X(tx(STA['DB'][1]))+2,Y(YC-7.5),'drop-out box + airlock')
c.drawString(X(tx(STA['FB'][1]))+1,Y(YC+5.5),'feed breeching')
c.drawString(X(tx(STA['BH'][1]))+1,Y(YC-2),'burner housing')
c.drawString(X(tx(STA['BU'][1]))-2,Y(YC+3.5),'burner + fuel train')
c.drawString(X(tx(STA['FB'][1])),Y(YC-10.5),'combustion blower')
c.setFillColor(GREY); c.setFont('Helvetica',6); c.drawString(X(tx(STA['XD'][0]))-40,Y(YC-11.5),'dryer train %.0f ft overall x %.0f ft wide'%(train_len,train_w))
# flows
arrow(c,20,57,26,57,NAVY); label(c,11,58.5,'digestate 8% TS',NAVY); label(c,11,55.5,'from digester',NAVY)
arrow(c,32,50,32,42.5); label(c,33,46,'cake')
route(c,[(86,45.5),(86,47),(88,47),(88,50)],RED); label(c,89,47.5,'dry product')
route(c,[(91,41),(92,41),(92,37),(94,37)],RED); label(c,91.5,43,'exhaust')
arrow(c,102,37,104,37); arrow(c,112,40,112,46); label(c,113,43,'stack')
arrow(c,98,41,98,50); label(c,99,45,'fines')
arrow(c,-5,13,10,13,NAVY); label(c,-5,14.5,'raw biogas',NAVY); label(c,-5,10.5,'<50 mbar',NAVY)
arrow(c,34,13,36,13); route(c,[(39,18),(39,24),(20,24),(20,30)],GREEN); label(c,22,25,'conditioned biogas, 2 psig',GREEN)
route(c,[(108,13),(102,13),(102,26),(14,26),(14,30)],ORANGE); label(c,50,27,'LPG vapor, 5 psig',ORANGE)
arrow(c,66,12,68,12); label(c,67,9,'480 V feeder / cable tray to all drives',GREY)
c.setFont('Helvetica-Oblique',6.5); c.setFillColor(GREY); c.drawString(X(3),Y(20),'10 ft maintenance clearance around the dryer train; crane access along the south side for drum and trunnion service')
c.drawString(X(106),Y(20),'Truck access this side'); c.drawString(X(100),Y(3.5),'LPG tanks: outside pad, min. 50 ft from dryer')
# scale bar and legend
c.setStrokeColor(colors.black); c.setLineWidth(1.5); c.line(X(0),Y(-3),X(24),Y(-3)); c.setFont('Helvetica',6.5); c.setFillColor(colors.black)
for f in (0,12,24): c.line(X(f),Y(-3)-3,X(f),Y(-3)+3); c.drawCentredString(X(f),Y(-3)-11,'%d ft'%f)
c.drawString(X(26),Y(-3)-3,'(0 - 7.3 m)')
lx=X(70); ly=Y(-1); c.setFont('Helvetica',6.5); c.setFillColor(colors.black)
for i,(col,t) in enumerate([(RED,'solids / exhaust'),(NAVY,'digestate, raw biogas'),(GREEN,'conditioned biogas'),(ORANGE,'LPG')]):
    c.setStrokeColor(col); c.setLineWidth(1.2); c.line(lx+i*95,ly,lx+i*95+14,ly); c.drawString(lx+i*95+17,ly-2,t)
c.showPage()

# ---------- page 2: elevation silhouette, schedule, utilities
hdr(c,'Side elevation, area schedule and utility summary','Elevation from the MCE 8 ft x 40 ft dryer general arrangement, 1 in = 15 ft.',2)
ES=inch/15.0; ex0=0.7*inch; ey0=PH-2.75*inch
def EX(s): return ex0+(elev[-1][0]-s)/12*ES   # burner end to the left, like the plan
def EY(h): return ey0+h/12*ES
etop=[(EX(s),EY(b)) for s,a,b in elev]; ebot=[(EX(s),EY(a)) for s,a,b in reversed(elev)]
poly(c,etop+ebot,LIGHT)
c.setStrokeColor(colors.black); c.setLineWidth(1); c.line(ex0-0.1*inch,ey0,EX(0)+0.15*inch,ey0)
c.setFont('Helvetica',6.5); c.setFillColor(GREY)
for h,t in ((0,'grade'),(HT['drum_centreline'],'drum centreline %.1f ft'%(HT['drum_centreline']/12)),(HT['burner_housing_top'],'burner housing top %.1f ft'%(HT['burner_housing_top']/12)),(HT['dropout_box_top'],'drop-out box top %.1f ft'%(HT['dropout_box_top']/12))):
    c.setStrokeColor(GREY); c.setLineWidth(0.4); c.setDash(2,2); c.line(EX(0)+0.15*inch,EY(h),EX(0)+0.3*inch,EY(h)); c.setDash()
    c.drawString(EX(0)+0.33*inch,EY(h)-2,t)
c.setFillColor(NAVY); c.setFont('Helvetica-Bold',7); c.drawString(ex0,ey0-12,'burner / fuel train'); c.drawString(EX(830),ey0-22,'burner housing'); c.drawString(EX(560),ey0-12,'8 ft x 40 ft drum on 39 ft base frame, two trunnion stations'); c.drawString(EX(160),ey0-22,'drop-out box')
c.setFont('Helvetica',6.5); c.setFillColor(GREY); c.drawString(ex0,ey0-33,'%.0f ft overall (burner face to drop-out box), %.0f ft with fuel train; cyclone, fan and stack not shown'%(elev[-1][0]/12,train_len))
base=ParagraphStyle('b',fontName='Helvetica',fontSize=7.6,leading=9.4)
rows=[[Paragraph('<b>Area</b>',base),Paragraph('<b>sq ft</b>',base),Paragraph('<b>sq m</b>',base),Paragraph('<b>Notes</b>',base)]]
for n,a,note in AREAS: rows.append([Paragraph(n,base),Paragraph('%s'%format(a,','),base),Paragraph('%.0f'%(a*FT2M2),base),Paragraph(note,base)])
rows.append([Paragraph('<b>Equipment footprints, total</b>',base),Paragraph('<b>%s</b>'%format(eq_ft2,','),base),Paragraph('<b>%.0f</b>'%(eq_ft2*FT2M2),base),Paragraph('blocks only',base)])
rows.append([Paragraph('<b>Equipment pad incl. clearances and access</b>',base),Paragraph('<b>%s</b>'%format(pad_ft2,','),base),Paragraph('<b>%.0f</b>'%(pad_ft2*FT2M2),base),Paragraph('%d ft x %d ft; roofed area approx. 3,200 sq ft (300 sq m) over dryer train and dewatering'%PAD,base)])
rows.append([Paragraph('<b>Recommended site allowance</b>',base),Paragraph('<b>15,100</b>',base),Paragraph('<b>1,400</b>',base),Paragraph('approx. 47 m x 30 m: pad, truck loop, LPG tank farm set-back, digestate piping corridor',base)])
t=Table(rows,colWidths=[3.2*inch,0.6*inch,0.6*inch,5.5*inch]); t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),LIGHT),('LINEBELOW',(0,0),(-1,0),0.8,NAVY),
  ('LINEBELOW',(0,1),(-1,-4),0.3,colors.HexColor('#cccccc')),('LINEABOVE',(0,-3),(-1,-3),0.8,NAVY),('TOPPADDING',(0,0),(-1,-1),1.5),('BOTTOMPADDING',(0,0),(-1,-1),2.5)]))
w,hh=t.wrap(PW-1.1*inch,PH); ytab=ey0-0.6*inch-hh; t.drawOn(c,0.55*inch,ytab)
y=ytab-0.18*inch
c.setFillColor(NAVY); c.setFont('Helvetica-Bold',9.5); c.drawString(0.55*inch,y,'Utility and interface summary (dewatered feed case, 140 t/day digestate at 8% TS)'); y-=12
U=[('Electrical','480 V / 3 ph / 60 Hz (or 440 V 60 Hz per site), approx. 160 hp connected, 100 kW average running; one feeder to the MCC. Control power 120 V.'),
   ('Biogas','From digester at <50 mbar; skid blower delivers 2 psig to the burner. Design flow approx. 200 scfm; H2S must be reduced to <500 ppm before the skid (see biogas skid design).'),
   ('LPG','New vapor supply, 5 psig at the burner train, sized for the full 10 MMBtu/hr burner when the digester is down (approx. 110 gal/hr liquid at full fire; far less in normal dewatered operation).'),
   ('Water','Wash-down and dewatering polymer make-up, approx. 2 gpm average, 20 gpm peak; potable quality for polymer.'),
   ('Compressed air','Instrument air 5 scfm at 90 psig, dry, for burner valves, airlock seals and skid instruments.'),
   ('Digestate in','Approx. 26,000 gal/day (98 m3/day) at 8% TS, pumped to the dewatering feed tank; centrate returned to the digester or lagoon by others.'),
   ('Product out','Approx. 13 t/day dried product at 15% moisture; bunker sized for 3 days; truck loading on the east side.'),
   ('Exhaust','Dryer exhaust via cyclone and stack (35 ft); no wet scrubber included; odor / ammonia control to be reviewed against local permit.'),
   ('Structures','All equipment on grade on a reinforced concrete pad; cyclone and stack on a steel support; roof over dryer train, dewatering and skid recommended.'),
   ('Equipment weights','Dryer drum and skid 79,900 lb empty plus up to 19,300 lb of material in the drum when running; burner assembly 16,000 lb; drop-out box 9,300 lb; total dryer train approx. 94,400 lb empty (from the MCE 8 ft x 40 ft dryer weight sheet). Cyclone, fan, dewatering and skid weights to follow with Rev C.')]
for k,v in U:
    p=Paragraph('<b>%s.</b> %s'%(k,v),base); pw,ph=p.wrap(PW-1.1*inch,PH); y-=ph; p.drawOn(c,0.55*inch,y); y-=1
c.save()
print('written',OUT.name,OUT.stat().st_size,'bytes; train %.1f x %.1f ft, train area %.0f ft2'%(train_len,train_w,train_len*train_w))
