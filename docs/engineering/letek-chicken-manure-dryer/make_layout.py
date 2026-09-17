"""Preliminary plot plan for the LETEK / Bachoco digestate dryer (base-14 fonts, compact for e-mail).
Page 1: plan view at 1 in = 12 ft.  Page 2: area schedule, utility summary and notes.
Dimensions are preliminary engineering estimates for site planning only; no vendor, price or lead time appears here."""
import io
from pathlib import Path
from PIL import Image
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
HERE=Path(__file__).parent; REPO=HERE.parents[2]
OUT=HERE/'MCE-LETEK-LAY-001_Preliminary_Layout.pdf'
NAVY=colors.HexColor('#0b2a4a'); RED=colors.HexColor('#c8102e'); GREY=colors.HexColor('#555555'); LIGHT=colors.HexColor('#e8eef5')
PW,PH=landscape(letter)
SC=inch/12.0            # 1 in = 12 ft
OX,OY=0.55*inch,1.25*inch   # pad origin on page
FT2M2=0.092903

# (tag, name, x, y, w, h, fill)  -- feet, pad origin lower-left, x east, y north
PAD=(110,64)
BLK=[
 ('D-1','Dewatering unit + feed tank\n(dewatered digestate)',0,44,20,15,LIGHT),
 ('B-1','Burner housing\n+ feed screw',10,30,12,14,LIGHT),
 ('XD','Rotary drum 8 ft dia x 40 ft\n(drum, drive, trunnions)',22,30,40,14,colors.HexColor('#d6e2f0')),
 ('DB','Drop-out box\n+ airlock',62,30,10,14,LIGHT),
 ('C-1','Cyclone\n+ airlock',74,33,8,8,LIGHT),
 ('F-1','Fan + stack',84,34,8,6,LIGHT),
 ('P-1','Dried product bunker / bagging',68,46,20,18,LIGHT),
 ('BGS','Biogas conditioning skid',10,8,24,10,LIGHT),
 ('CH','Chiller',36,10,6,8,LIGHT),
 ('MCC','MCC / control room',48,6,16,12,LIGHT),
 ('LPG','LPG vaporizer / regulator station\n(by others)',96,8,10,10,colors.white),
]
AREAS=[  # name, footprint ft2 (block), note
 ('Dryer train (burner housing, drum, drop-out box)',62*14,'16 ft high; 10 ft clear all round for maintenance'),
 ('Cyclone and exhaust fan',8*8+8*6,'cyclone approx. 22 ft tall, stack to 35 ft'),
 ('Dewatering unit, feed tank and transfer',20*15,'covered; wash-down floor with drain'),
 ('Dried product bunker / bagging',20*18,'covered, 3-sided; sized for 3 days of product'),
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
    c.drawRightString(PW-0.55*inch,PH-0.72*inch,'MCE-LETEK-LAY-001  Rev 0  -  17 Sep 2026  -  PRELIMINARY, FOR SITE PLANNING ONLY')
    c.setFont('Helvetica',7); c.drawString(0.55*inch,0.4*inch,'Midwest Custom Engineering, Inc.  -  6526 S Kanner Hwy #215, Stuart, FL 34997  -  usemce.com')
    c.drawRightString(PW-0.55*inch,0.4*inch,'page %d of 2'%page)
    c.setStrokeColor(NAVY); c.setLineWidth(1); c.line(0.55*inch,PH-0.8*inch,PW-0.55*inch,PH-0.8*inch)

c=canvas.Canvas(str(OUT),pagesize=landscape(letter)); c.setTitle('MCE-LETEK-LAY-001 Preliminary Layout'); c.setAuthor('Midwest Custom Engineering, Inc.')
hdr(c,'Preliminary plot plan - 140 t/day digestate dryer, LETEK DCG / Bachoco, Merida, Yucatan','Plan view, 1 in = 12 ft (1:144).  Pad %d x %d ft (%.0f x %.0f m).'%(PAD[0],PAD[1],PAD[0]*0.3048,PAD[1]*0.3048),1)
# pad
c.setStrokeColor(NAVY); c.setLineWidth(1.2); c.setDash(6,3); c.rect(X(0),Y(0),PAD[0]*SC,PAD[1]*SC); c.setDash()
c.setFont('Helvetica',7.5); c.setFillColor(GREY)
c.drawString(X(1),Y(PAD[1])+5,'Concrete equipment pad %d ft x %d ft = %s sq ft (%.0f sq m); roof over dryer train, dewatering and skid recommended (Yucatan rain)'%(PAD[0],PAD[1],format(pad_ft2,','),pad_ft2*FT2M2))
# blocks
for tag,name,x,y,w,h,fill in BLK:
    c.setFillColor(fill); c.setStrokeColor(NAVY); c.setLineWidth(0.9)
    if tag=='LPG': c.setDash(3,2)
    c.rect(X(x),Y(y),w*SC,h*SC,fill=1); c.setDash()
    c.setFillColor(NAVY); c.setFont('Helvetica-Bold',7.5); c.drawString(X(x)+2,Y(y+h)-9,tag)
    c.setFont('Helvetica',6.3); c.setFillColor(colors.black)
    for i,ln in enumerate(name.split('\n')): c.drawString(X(x)+2,Y(y+h)-17-7*i,ln)
    c.setFillColor(GREY); c.setFont('Helvetica',6); c.drawString(X(x)+2,Y(y)+2,'%d x %d ft'%(w,h))
# drum outline inside the XD block
c.setStrokeColor(NAVY); c.setLineWidth(0.6); c.roundRect(X(23),Y(33),38*SC,8*SC,4,fill=0)
# flow lines
def arrow(x1,y1,x2,y2,label=None,col=RED):
    c.setStrokeColor(col); c.setLineWidth(1); c.line(X(x1),Y(y1),X(x2),Y(y2))
    import math
    a=math.atan2(Y(y2)-Y(y1),X(x2)-X(x1)); s=5
    c.line(X(x2),Y(y2),X(x2)-s*math.cos(a-0.5),Y(y2)-s*math.sin(a-0.5)); c.line(X(x2),Y(y2),X(x2)-s*math.cos(a+0.5),Y(y2)-s*math.sin(a+0.5))
    if label: c.setFont('Helvetica-Oblique',6); c.setFillColor(col); c.drawString(X((x1+x2)/2)+3,Y((y1+y2)/2)+3,label)
def label(x,y,t,col=RED): c.setFont('Helvetica-Oblique',6); c.setFillColor(col); c.drawString(X(x),Y(y),t)
def poly(pts,col):
    c.setStrokeColor(col); c.setLineWidth(1)
    for (x1,y1),(x2,y2) in zip(pts,pts[1:]): c.line(X(x1),Y(y1),X(x2),Y(y2))
    arrow(pts[-2][0],pts[-2][1],pts[-1][0],pts[-1][1],None,col)
arrow(-5,52,0,52,None,NAVY); label(-5,49.5,'digestate 8% TS',NAVY); label(-5,47.5,'from digester',NAVY)
arrow(16,44,16,40); label(17,45.5,'cake')
arrow(72,37,74,37); arrow(82,37,84,37); arrow(92,40,92,46); label(93,43,'stack')
arrow(67,44,70,46); label(60,45.5,'dry product')
arrow(78,41,78,46); label(79,43,'fines')
arrow(-5,13,10,13,None,NAVY); label(-5,14.5,'raw biogas',NAVY); label(-5,10.5,'<50 mbar',NAVY)
arrow(34,13,36,13); poly([(39,18),(39,25),(16,25),(16,30)],colors.HexColor('#1a7f37')); label(20,26,'conditioned biogas, 2 psig',colors.HexColor('#1a7f37'))
poly([(96,13),(94,13),(94,27),(20,27),(20,30)],colors.HexColor('#b36b00')); label(50,28,'LPG vapor, 5 psig',colors.HexColor('#b36b00'))
arrow(64,12,66,12); label(65,9,'480 V feeder / cable tray to all drives',GREY)
# clearances and notes
c.setStrokeColor(GREY); c.setLineWidth(0.5); c.setDash(2,2); c.rect(X(0),Y(20),92*SC,34*SC); c.setDash()
c.setFont('Helvetica-Oblique',6.5); c.setFillColor(GREY); c.drawString(X(1),Y(21),'10 ft maintenance clearance around dryer train; keep 45 ft clear east of the drop-out box for drum / shell removal')
c.drawString(X(96),Y(20),'Truck access this side'); c.drawString(X(96),Y(4),'LPG tanks: outside pad, min. 50 ft from dryer')
# scale bar
c.setStrokeColor(colors.black); c.setLineWidth(1.5); c.line(X(0),Y(-3),X(24),Y(-3)); c.setFont('Helvetica',6.5); c.setFillColor(colors.black)
for f in (0,12,24): c.line(X(f),Y(-3)-3,X(f),Y(-3)+3); c.drawCentredString(X(f),Y(-3)-11,'%d ft'%f)
c.drawString(X(26),Y(-3)-3,'(0 - 7.3 m)')
# legend
lx=X(70); ly=Y(-1)
c.setFont('Helvetica',6.5); c.setFillColor(colors.black)
for i,(col,t) in enumerate([(RED,'solids / exhaust'),(NAVY,'digestate, raw biogas'),(colors.HexColor('#1a7f37'),'conditioned biogas'),(colors.HexColor('#b36b00'),'LPG')]):
    c.setStrokeColor(col); c.setLineWidth(1.2); c.line(lx+i*95,ly,lx+i*95+14,ly); c.drawString(lx+i*95+17,ly-2,t)
c.showPage()

# ---------- page 2: schedule, utilities, notes
hdr(c,'Area schedule, utility summary and notes','All figures preliminary; to be confirmed after dewatering test and biogas analysis.',2)
base=ParagraphStyle('b',fontName='Helvetica',fontSize=8,leading=10); bold=ParagraphStyle('bb',parent=base,fontName='Helvetica-Bold')
rows=[[Paragraph('<b>Area</b>',base),Paragraph('<b>sq ft</b>',base),Paragraph('<b>sq m</b>',base),Paragraph('<b>Notes</b>',base)]]
for n,a,note in AREAS: rows.append([Paragraph(n,base),Paragraph('%s'%format(a,','),base),Paragraph('%.0f'%(a*FT2M2),base),Paragraph(note,base)])
rows.append([Paragraph('<b>Equipment footprints, total</b>',base),Paragraph('<b>%s</b>'%format(eq_ft2,','),base),Paragraph('<b>%.0f</b>'%(eq_ft2*FT2M2),base),Paragraph('blocks only',base)])
rows.append([Paragraph('<b>Equipment pad incl. clearances and access</b>',base),Paragraph('<b>%s</b>'%format(pad_ft2,','),base),Paragraph('<b>%.0f</b>'%(pad_ft2*FT2M2),base),Paragraph('%d ft x %d ft; roofed area approx. 2,400 sq ft (220 sq m) over dryer train and dewatering'%PAD,base)])
rows.append([Paragraph('<b>Recommended site allowance</b>',base),Paragraph('<b>12,900</b>',base),Paragraph('<b>1,200</b>',base),Paragraph('approx. 40 m x 30 m: pad, truck loop, LPG tank farm set-back, digestate piping corridor',base)])
t=Table(rows,colWidths=[3.0*inch,0.7*inch,0.7*inch,5.3*inch]); t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),LIGHT),('LINEBELOW',(0,0),(-1,0),0.8,NAVY),
  ('LINEBELOW',(0,1),(-1,-4),0.3,colors.HexColor('#cccccc')),('LINEABOVE',(0,-3),(-1,-3),0.8,NAVY),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
w,hh=t.wrap(PW-1.1*inch,PH); t.drawOn(c,0.55*inch,PH-1.0*inch-hh)
y=PH-1.15*inch-hh
c.setFillColor(NAVY); c.setFont('Helvetica-Bold',10); c.drawString(0.55*inch,y,'Utility and interface summary (dewatered feed case, 140 t/day digestate at 8% TS)'); y-=14
U=[('Electrical','480 V / 3 ph / 60 Hz (or 440 V 60 Hz per site), approx. 160 hp connected, 100 kW average running; one feeder to the MCC. Control power 120 V.'),
   ('Biogas','From digester at <50 mbar; skid blower delivers 2 psig to the burner. Design flow approx. 200 scfm; H2S must be reduced to <500 ppm before the skid (see biogas skid design).'),
   ('LPG','New vapor supply, 5 psig at the burner train, sized for the full 10 MMBtu/hr burner when the digester is down (approx. 110 gal/hr liquid at full fire; far less in normal dewatered operation).'),
   ('Water','Wash-down and dewatering polymer make-up, approx. 2 gpm average, 20 gpm peak; potable quality for polymer.'),
   ('Compressed air','Instrument air 5 scfm at 90 psig, dry, for burner valves, airlock seals and skid instruments.'),
   ('Digestate in','Approx. 26,000 gal/day (98 m3/day) at 8% TS, pumped to the dewatering feed tank; centrate returned to the digester or lagoon by others.'),
   ('Product out','Approx. 13 t/day dried product at 15% moisture; bunker sized for 3 days; truck loading on the east side.'),
   ('Exhaust','Dryer exhaust via cyclone and stack (35 ft); no wet scrubber included; odor / ammonia control to be reviewed against local permit.'),
   ('Structures','All equipment on grade on a reinforced concrete pad; cyclone and stack on a steel support; roof over dryer train, dewatering and skid recommended.')]
for k,v in U:
    p=Paragraph('<b>%s.</b> %s'%(k,v),base); pw,ph=p.wrap(PW-1.1*inch,PH); y-=ph; p.drawOn(c,0.55*inch,y); y-=2
c.save()
print('written',OUT.name,OUT.stat().st_size,'bytes')
