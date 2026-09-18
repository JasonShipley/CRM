"""LETEK DCG / Bachoco - MCE general arrangement sheet in the MCS drawing style (SD-22-03 / SD-01-20):
ANSI D 36 x 24 in, plan / elevation / end views at 3/16 in = 1 ft, feet-inch dimensions, leader labels,
general notes, title block bottom right.  Dryer train from the MCE 8x40 line work (xd96_linework.json.gz,
calibrated on the dimensioned field-assembly sheet); cyclone, fan, stack, feed, dewatering, skid drawn schematically.
LIGHT=1 draws the train as silhouettes (small file for e-mail).  No vendor, price or lead time appears here."""
import json, gzip, io, math, os
from pathlib import Path
from PIL import Image
from reportlab import rl_config; rl_config.useA85=0
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
HERE=Path(__file__).parent; REPO=HERE.parents[2]
LIGHT=os.environ.get('LIGHT')=='1'
DWG='SD-26-01'; REV='P1'; DATE='9/18/2026'
OUT=HERE/('%s_LETEK_XD-96_General_Arrangement%s.pdf'%(DWG,'_email' if LIGHT else ''))
LW=json.load(gzip.open(HERE/'xd96_linework.json.gz')); SIL=json.load(open(HERE/'xd96_silhouette.json'))
HT=SIL['heights_in']; STA=SIL['stations_in']
W,H=36*inch,24*inch; K=13.5   # pt per ft (3/16 in = 1 ft)
BLACK=colors.black; GREY=colors.HexColor('#666666')
c=canvas.Canvas(str(OUT),pagesize=(W,H),pageCompression=1); c.setTitle('%s LETEK XD-96 General Arrangement'%DWG); c.setAuthor('Midwest Custom Engineering, Inc.')
def fi(inches):
    inches=round(inches); f,i=divmod(inches,12); return '%d\'-%d"'%(f,i)
def txt(x,y,s,size=8,bold=False,align='l',rot=0):
    c.saveState(); c.setFillColor(BLACK); c.setFont('Helvetica-Bold' if bold else 'Helvetica',size)
    c.translate(x,y); c.rotate(rot)
    {'l':c.drawString,'c':c.drawCentredString,'r':c.drawRightString}[align](0,0,s); c.restoreState()
def arrow(x,y,ang,L=7,w=2.2):
    p=c.beginPath(); p.moveTo(x,y); p.lineTo(x-L*math.cos(ang)+w*math.sin(ang),y-L*math.sin(ang)-w*math.cos(ang)); p.lineTo(x-L*math.cos(ang)-w*math.sin(ang),y-L*math.sin(ang)+w*math.cos(ang)); p.close()
    c.setFillColor(BLACK); c.drawPath(p,fill=1,stroke=0)
def hdim(x1,x2,y,label=None,ext=None,above=True):
    c.setStrokeColor(BLACK); c.setLineWidth(0.4)
    if ext is not None:
        for x in (x1,x2): c.line(x,ext,x,y+(4 if above else -4))
    c.line(x1,y,x2,y); arrow(x1,y,math.pi); arrow(x2,y,0)
    txt((x1+x2)/2,y+3 if above else y-10,label or fi(abs(x2-x1)/K*12),8,align='c')
def vdim(y1,y2,x,label=None,ext=None,right=True):
    c.setStrokeColor(BLACK); c.setLineWidth(0.4)
    if ext is not None:
        for y in (y1,y2): c.line(ext,y,x+(4 if right else -4),y)
    c.line(x,y1,x,y2); arrow(x,y1,-math.pi/2); arrow(x,y2,math.pi/2)
    txt(x-3 if right else x+11,(y1+y2)/2,label or fi(abs(y2-y1)/K*12),8,align='c',rot=90)
def leader(tx,ty,lx,ly,lines,side='r'):
    c.setStrokeColor(BLACK); c.setLineWidth(0.4); c.line(tx,ty,lx,ly); sh=10 if side=='r' else -10; c.line(lx,ly,lx+sh,ly)
    c.setFillColor(BLACK); c.circle(tx,ty,1.1,fill=1,stroke=0)
    if isinstance(lines,str): lines=[lines]
    for i,s in enumerate(lines): txt(lx+sh+(3 if side=='r' else -3),ly-3-9*i+(9*(len(lines)-1))/2,s,7.5,align='l' if side=='r' else 'r')
def rect(x,y,w,h,dash=None,lw=0.6):
    c.setStrokeColor(BLACK); c.setLineWidth(lw)
    if dash: c.setDash(*dash)
    c.rect(x,y,w,h); c.setDash()
def title(x,y,name,sub,scale='Scale  3/16" = 1\'-0"'):
    txt(x,y,name,15,True,'c'); tw=c.stringWidth(name,'Helvetica-Bold',15); c.setLineWidth(1.2); c.setStrokeColor(BLACK); c.line(x-tw/2-6,y-4,x+tw/2+6,y-4)
    txt(x,y-15,sub,9,False,'c'); txt(x,y-26,scale,8.5,False,'c')

# ---------------- sheet border and title block
c.setLineWidth(1.5); c.setStrokeColor(BLACK); c.rect(0.5*inch,0.5*inch,W-1*inch,H-1*inch)
TBX,TBY,TBW,TBH=W-0.5*inch-8.6*inch,0.5*inch,8.6*inch,3.5*inch
c.setLineWidth(1.0); c.rect(TBX,TBY,TBW,TBH)
im=Image.open(REPO/'renderer'/'assets'/'mce-logo.png').convert('RGBA'); im.thumbnail((200,200) if LIGHT else (320,320)); bg=Image.new('RGB',im.size,'white'); bg.paste(im,mask=im.split()[3]); lb=io.BytesIO(); bg.save(lb,'JPEG',quality=55 if LIGHT else 70,optimize=True); lb.seek(0)
from reportlab.lib.utils import ImageReader
lh=0.75*inch; lw_=lh*im.size[0]/im.size[1]; c.drawImage(ImageReader(lb),TBX+TBW/2-lw_/2,TBY+TBH-0.85*inch,lw_,lh)
c.line(TBX,TBY+TBH-0.95*inch,TBX+TBW,TBY+TBH-0.95*inch)
note=['THIS DRAWING AND THE DESIGN SHOWN THEREIN IS THE PROPERTY OF MIDWEST CUSTOM ENGINEERING, INC. ANY DUPLICATION OR USE OF THIS PRINT FOR PURPOSES',
      'OTHER THAN THAT FOR WHICH IT WAS FURNISHED IS HEREBY PROHIBITED. COPYRIGHT 2026, MIDWEST CUSTOM ENGINEERING, INC. ALL RIGHTS RESERVED.']
for i,s in enumerate(note): txt(TBX+6,TBY+TBH-0.95*inch-10-8*i,s,5.4)
c.line(TBX,TBY+TBH-1.3*inch,TBX+TBW,TBY+TBH-1.3*inch)
txt(TBX+TBW/2,TBY+TBH-1.3*inch-16,'MCE GENERAL ARRANGEMENT',13,True,'c')
c.line(TBX,TBY+TBH-1.6*inch,TBX+TBW,TBY+TBH-1.6*inch)
txt(TBX+TBW/2,TBY+TBH-1.6*inch-14,'LETEK DCG / BACHOCO - MODEL XD-96 8\'-0" x 40\'-0" ROTARY DRYER SYSTEM',9.5,False,'c')
txt(TBX+TBW/2,TBY+TBH-1.6*inch-27,'PRELIMINARY PLAN AND ELEVATIONS - MERIDA, YUCATAN',9.5,False,'c')
c.line(TBX,TBY+TBH-2.1*inch,TBX+TBW,TBY+TBH-2.1*inch)
# drawn / date / drawing number grid
gy=TBY+TBH-2.1*inch; g2=TBY+0.55*inch
c.line(TBX,g2,TBX+TBW,g2); c.line(TBX+1.6*inch,TBY,TBX+1.6*inch,gy); c.line(TBX+3.2*inch,TBY,TBX+3.2*inch,gy); c.line(TBX+7.6*inch,TBY,TBX+7.6*inch,gy)
c.line(TBX,gy-0.45*inch,TBX+3.2*inch,gy-0.45*inch)
txt(TBX+3,gy-8,'DRAWN:',5.5); txt(TBX+0.6*inch,gy-22,'MCE',8); txt(TBX+1.6*inch+3,gy-8,'DATE:',5.5); txt(TBX+2.2*inch,gy-22,DATE,8)
txt(TBX+3,gy-0.45*inch-8,'CHECK:',5.5); txt(TBX+1.6*inch+3,gy-0.45*inch-8,'DATE:',5.5)
txt(TBX+3,g2-8,'SCALE:',5.5); txt(TBX+0.5*inch,g2-22,'3/16" = 1\'-0"   [1:64]',8)
txt(TBX+3.2*inch+3,gy-8,'DRAWING NUMBER:',5.5); txt(TBX+5.4*inch,gy-0.85*inch,DWG,22,False,'c')
txt(TBX+7.6*inch+3,gy-8,'REV:',5.5); txt(TBX+8.1*inch,gy-0.85*inch,REV,14,False,'c')
txt(TBX+3.2*inch+3,g2-8,'SHEET:',5.5); txt(TBX+3.2*inch+0.5*inch,g2-22,'1 OF 1',8)
# ---------------- general notes
NX,NY,NW,NH=TBX,TBY+TBH+0.2*inch,TBW,4.1*inch
c.setLineWidth(0.8); c.rect(NX,NY,NW,NH); txt(NX+NW/2,NY+NH-16,'GENERAL NOTES',11,True,'c'); c.line(NX+NW/2-45,NY+NH-19,NX+NW/2+45,NY+NH-19)
notes=[
 '1.  PRELIMINARY ARRANGEMENT FOR SITE PLANNING ONLY. DIMENSIONS OF THE DRYER TRAIN ARE TAKEN FROM THE MCE 8\'-0" x 40\'-0" DRYER',
 '    GENERAL ARRANGEMENT. CYCLONE, FAN, DUCTING, FEED, DISCHARGE, DEWATERING AND BIOGAS EQUIPMENT ARE SHOWN SCHEMATICALLY AND',
 '    WILL BE SIZED IN FINAL ENGINEERING. EQUIPMENT CAN BE ROTATED TO SUIT BUYER\'S SITE PLAN.',
 '2.  BASIS: 140 MT/DAY DIGESTATE AT 8% TS, DEWATERED TO 22-30% TS AHEAD OF THE DRYER, DRIED TO 15% MOISTURE. 10 MMBTU/HR DUAL-FUEL',
 '    BURNER, BIOGAS PRIMARY WITH LPG STAND-BY. DRUM MATERIAL CARBON STEEL (316L OPTIONAL).',
 '3.  ESTIMATED EQUIPMENT WEIGHTS FOR FOUNDATION DESIGN: DRUM AND SKID 79,900 LB EMPTY PLUS UP TO 19,300 LB OF MATERIAL IN THE DRUM',
 '    WHEN RUNNING; BURNER ASSEMBLY 16,000 LB; DROP-OUT BOX 9,300 LB. CYCLONE, FAN, DEWATERING AND SKID WEIGHTS TO FOLLOW.',
 '4.  UTILITIES: 480V/3PH/60HZ (OR 440V/60HZ), APPROX. 160 HP CONNECTED, 100 KW AVERAGE. BIOGAS FROM DIGESTER AT <50 MBAR TO SKID INLET;',
 '    SKID DELIVERS 2 PSIG TO THE BURNER TRAIN. LPG VAPOR 5 PSIG AT THE BURNER TRAIN (SUPPLY BY OTHERS). INSTRUMENT AIR 5 SCFM AT 90 PSIG.',
 '    WASH-DOWN AND POLYMER MAKE-UP WATER 2 GPM AVERAGE, 20 GPM PEAK.',
 '5.  CONCRETE EQUIPMENT PAD 124\'-0" x 64\'-0", ROOF OVER DRYER TRAIN, DEWATERING UNIT AND BIOGAS SKID RECOMMENDED. 10\'-0" MAINTENANCE',
 '    CLEARANCE AROUND THE DRYER TRAIN AND CRANE ACCESS ALONG THE COMBUSTION BLOWER SIDE FOR DRUM AND TRUNNION SERVICE.',
 '6.  LPG STORAGE, BIOGAS PIPING FROM THE DIGESTER, DIGESTATE PUMPING, CENTRATE RETURN, PRODUCT BUNKER, ELECTRICAL FEEDER, FOUNDATIONS,',
 '    ROOFING AND EXHAUST SCRUBBING (IF REQUIRED BY THE AIR PERMIT) ARE BY OTHERS. LPG TANKS MIN. 50\'-0" FROM THE DRYER PER LOCAL CODE.',
 '7.  DRYER CONTROL PANEL AND MCC TO BE LOCATED IN THE CONTROL ROOM SHOWN OR REMOTELY AS PREFERRED.']
for i,s in enumerate(notes): txt(NX+8,NY+NH-36-10.2*i,s,6.6)

# ---------------- geometry (ft): pad 124 x 64, train centreline y=37, drop-out box far end at x=34, burner end to the right
PADW,PADH=124.0,64.0; XD=34.0; YC=37.0
PX0,PY0=1.0*inch,10.3*inch   # plan origin (pad corner) on sheet
def PX(x): return PX0+x*K
def PY(y): return PY0+y*K
EY0=2.3*inch                 # elevation grade line
def EY(h): return EY0+h*K
plan=LW['plan']; elev=LW['elevation']
train_len=max(max(s[0],s[2]) for s in plan); train_end=XD+train_len
# ---- PLAN VIEW
c.setStrokeColor(BLACK)
rect(PX(0),PY(0),PADW*K,PADH*K,dash=(8,4),lw=0.8)
txt(PX(1),PY(PADH)+5,'CONCRETE EQUIPMENT PAD %s x %s (BY OTHERS)'%(fi(PADW*12),fi(PADH*12)),7.5)
# pad dims
hdim(PX(0),PX(PADW),PY(PADH)+0.55*inch,ext=PY(PADH)+0.1*inch); vdim(PY(0),PY(PADH),PX(PADW)+0.45*inch,ext=PX(PADW)+0.1*inch)
# dryer train line work
c.setLineWidth(0.3); c.setStrokeColor(BLACK)
if LIGHT:
    pe=SIL['plan_envelope_in']; pts=[(PX(XD+s/12),PY(YC-a/12)) for s,a,b in pe]+[(PX(XD+s/12),PY(YC-b/12)) for s,a,b in reversed(pe)]
    p=c.beginPath(); p.moveTo(*pts[0]); [p.lineTo(*q) for q in pts[1:]]; p.close(); c.drawPath(p,fill=0,stroke=1)
    s0,s1=STA['XD']; c.rect(PX(XD+s0/12),PY(YC-HT['plan_outline_inner_od']/24),(s1-s0)/12*K,HT['plan_outline_inner_od']/12*K)
else:
    c.lines([(PX(XD+s0),PY(YC-o0),PX(XD+s1),PY(YC-o1)) for s0,o0,s1,o1 in plan])
# centreline
c.setDash([12,3,2,3]); c.setLineWidth(0.4); c.line(PX(XD-4),PY(YC),PX(train_end+3),PY(YC)); c.setDash()
# cyclone, fan, stack, ducting (plan)
CYX,CYR=26.0,4.0; FNX=16.0; STX,STR=9.0,1.75
c.setLineWidth(0.7); c.circle(PX(CYX),PY(YC),CYR*K); c.circle(PX(CYX),PY(YC),1.2*K)
c.rect(PX(CYX-1.5),PY(YC-6.5),3*K,3*K)  # cyclone support / airlock footprint
c.line(PX(XD+2),PY(YC+3.5),PX(CYX+1),PY(YC+3.5)); c.line(PX(XD+2),PY(YC+5.5),PX(CYX+1),PY(YC+5.5))   # inlet duct from drop-out box top
c.circle(PX(FNX),PY(YC),3.0*K); c.rect(PX(FNX-3.5),PY(YC-4.5),7*K,9*K,)  # fan scroll and base
c.line(PX(CYX-CYR),PY(YC-1),PX(FNX+3),PY(YC-1)); c.line(PX(CYX-CYR),PY(YC+1),PX(FNX+3),PY(YC+1))       # cyclone outlet to fan inlet
c.circle(PX(STX),PY(YC),STR*K); c.line(PX(FNX-3),PY(YC-1.2),PX(STX+STR),PY(YC-1.2)); c.line(PX(FNX-3),PY(YC+1.2),PX(STX+STR),PY(YC+1.2))
# discharge airlock and product conveyor to bunker (north side)
rect(PX(XD+4),PY(YC+6.5),3*K,2*K); rect(PX(XD+5.25),PY(YC+8.5),0.5*K*3,(50-YC-8.5)*K,lw=0.5)
rect(PX(20),PY(50),20*K,14*K,dash=(4,3))
# dewatering, feed screw
FBX=XD+(STA['FB'][0]+STA['FB'][1])/24
rect(PX(FBX-10),PY(50),20*K,14*K,dash=(4,3)); rect(PX(FBX-0.75),PY(YC+3),1.5*K,10*K)
# biogas skid, chiller, MCC, LPG
rect(PX(84),PY(2),24*K,10*K); rect(PX(76),PY(3),6*K,8*K); rect(PX(56),PY(2),16*K,10*K); rect(PX(112),PY(2),10*K,10*K,dash=(4,3))
# maintenance clearance
rect(PX(XD-12),PY(YC-18),(train_len+16)*K,36*K,dash=(2,3),lw=0.4)
# plan dims
hdim(PX(XD),PX(train_end),PY(YC-19.3),ext=PY(YC-16),above=False)
txt((PX(XD)+PX(train_end))/2,PY(YC-19.3)-19,'DRYER TRAIN OVERALL (REF)',7,align='c')
hdim(PX(XD+STA['XD'][0]/12),PX(XD+STA['XD'][1]/12),PY(YC+11.5),label='40\'-0" DRUM',ext=PY(YC+8))
hdim(PX(STX-STR),PX(train_end),PY(YC-22.8),ext=None,above=False); txt((PX(STX-STR)+PX(train_end))/2,PY(YC-22.8)-19,'DRYER SYSTEM OVERALL, STACK TO FUEL TRAIN (REF)',7,align='c')
hdim(PX(CYX-CYR),PX(CYX+CYR),PY(YC+6.5),label='8\'-0" DIA',ext=None)
# plan labels
leader(PX(CYX),PY(YC+2.5),PX(CYX+2),PY(YC+16),['HIGH EFFICIENCY','CYCLONE COLLECTOR'])
leader(PX(FNX),PY(YC-2),PX(FNX-4),PY(YC-11),['60 HP DRYER FAN'],side='l')
leader(PX(STX),PY(YC+1),PX(STX-3),PY(YC+9),['EXHAUST STACK','35\'-0" HIGH'],side='l')
leader(PX(XD+5.5),PY(YC+7.5),PX(XD-8),PY(YC+10.5),['ROTARY AIRLOCK AND','PRODUCT CONVEYOR'],side='l')
leader(PX(30),PY(57),PX(30),PY(57),['DRIED PRODUCT BUNKER','(BY OTHERS)'])
leader(PX(XD+STA['DB'][1]/24),PY(YC-5),PX(XD+2),PY(YC-11),['DROP-OUT BOX'],side='l')
leader(PX(XD+STA['XD'][1]/12-8),PY(YC+4.4),PX(XD+STA['XD'][1]/12-4),PY(YC+16),['MODEL XD-96 ROTARY DRYER','8\'-0" DIA x 40\'-0" DRUM'])
leader(PX(XD+30),PY(YC-4.5),PX(XD+32),PY(YC-13),['SADDLE MOUNT DRUM DRIVE, 30 HP'])
leader(PX(FBX),PY(YC+8),PX(FBX+6),PY(YC+11),['12" S.S. FEED SCREW x 10\'-0"'])
leader(PX(FBX+2),PY(57),PX(FBX+11),PY(60),['DEWATERING UNIT WITH FEED TANK','(DECANTER OR SCREW PRESS)','CAKE CHUTE TO FEED SCREW'])
leader(PX(XD+(STA['BH'][0]+STA['BH'][1])/24),PY(YC-3.8),PX(XD+STA['BH'][0]/12+2),PY(YC-12.5),['BURNER HOUSING'])
leader(PX(XD+(STA['FB'][1])/12+1),PY(YC-7.5),PX(XD+STA['FB'][1]/12+6),PY(YC-16),['COMBUSTION AIR BLOWER'])
leader(PX(train_end-4),PY(YC+1),PX(train_end-6),PY(YC+8),['10 MMBTU/HR DUAL FUEL BURNER','(LPG / BIOGAS) WITH FUEL TRAINS'])
leader(PX(96),PY(7),PX(96),PY(7),['BIOGAS CONDITIONING SKID']); leader(PX(79),PY(7),PX(79),PY(7),['GAS','CHILLER'])
leader(PX(64),PY(7),PX(64),PY(7),['MCC / CONTROL ROOM']); leader(PX(117),PY(7),PX(117),PY(7),['LPG VAPORIZER','(BY OTHERS)'])
txt(PX(2),PY(2),'TRUCK ACCESS AND LPG TANK FARM: THIS SIDE, LOCATION PER BUYER\'S SITE PLAN',7)
txt(PX(FBX-9),PY(PADH)-8,'DIGESTATE FROM DIGESTER (BY OTHERS)',7); txt(PX(84),PY(0.8),'RAW BIOGAS FROM DIGESTER, <50 MBAR (BY OTHERS)',7)
# north arrow
c.setLineWidth(0.8); nx,ny=PX(PADW)+1.1*inch,PY(PADH)-0.3*inch; c.line(nx,ny-25,nx,ny+10); arrow(nx,ny+10,math.pi/2,10,3); txt(nx,ny+14,'N (ARBITRARY)',7,align='c')
title(PX(PADW/2),PY(0)-0.45*inch,'PLAN VIEW','MODEL XD-96 DRYER SYSTEM')

# ---- ELEVATION VIEW
c.setLineWidth(1.0); c.setStrokeColor(BLACK); c.line(PX(0),EY(0),PX(PADW),EY(0)); txt(PX(0.5),EY(0)-9,'GRADE',6.5)
c.setLineWidth(0.3)
if LIGHT:
    ee=SIL['elevation_envelope_in']; pts=[(PX(XD+s/12),EY(b/12)) for s,a,b in ee]+[(PX(XD+s/12),EY(a/12)) for s,a,b in reversed(ee)]
    p=c.beginPath(); p.moveTo(*pts[0]); [p.lineTo(*q) for q in pts[1:]]; p.close(); c.drawPath(p,fill=0,stroke=1)
else:
    c.lines([(PX(XD+s0),EY(h0),PX(XD+s1),EY(h1)) for s0,h0,s1,h1 in elev])
DBT=HT['dropout_box_top']/12; DCL=HT['drum_centreline']/12; BHT=HT['burner_housing_top']/12
# cyclone: cylinder 14-22 ft, cone 8-14, legs
c.setLineWidth(0.7); c.rect(PX(CYX-CYR),EY(14),2*CYR*K,8*K)
p=c.beginPath(); p.moveTo(PX(CYX-CYR),EY(14)); p.lineTo(PX(CYX-1),EY(8)); p.lineTo(PX(CYX+1),EY(8)); p.lineTo(PX(CYX+CYR),EY(14)); c.drawPath(p,fill=0,stroke=1)
for dx in (-CYR+0.5,CYR-0.5): c.line(PX(CYX+dx),EY(14),PX(CYX+dx),EY(0))
c.line(PX(CYX-CYR+0.5),EY(7),PX(CYX+CYR-0.5),EY(7)); c.rect(PX(CYX-1),EY(6),2*K,2*K)   # airlock
c.line(PX(CYX+1.5),EY(6.5),PX(XD+8),EY(6.5)); c.line(PX(CYX+1.5),EY(5.5),PX(XD+8),EY(5.5))  # product screw to bunker side
c.rect(PX(XD+2),EY(DBT-0.5),4*K,1.5*K)   # drop-out box outlet
c.line(PX(XD+2),EY(DBT+1),PX(XD+2),EY(20.5)); c.line(PX(XD+6),EY(DBT+1),PX(XD+6),EY(21.5)); c.line(PX(XD+2),EY(20.5),PX(CYX+CYR),EY(20.5)); c.line(PX(XD+6),EY(21.5),PX(CYX+CYR),EY(21.5))
c.line(PX(CYX-1.2),EY(22),PX(CYX-1.2),EY(23)); c.line(PX(CYX+1.2),EY(22),PX(CYX+1.2),EY(25))
c.line(PX(CYX-1.2),EY(23),PX(FNX+1),EY(23)); c.line(PX(CYX+1.2),EY(25),PX(FNX-1),EY(25))   # cyclone outlet duct to fan
c.line(PX(FNX+1),EY(23),PX(FNX+1),EY(7.5)); c.line(PX(FNX-1),EY(25),PX(FNX-1),EY(7.5))
c.circle(PX(FNX),EY(4.5),3.0*K); c.rect(PX(FNX-3.5),EY(0),7*K,1.5*K); c.rect(PX(FNX+3.5),EY(0),3*K,3.5*K)  # fan, base, motor
c.rect(PX(FNX-2.5),EY(0),1.0*K,7.5*K)
c.line(PX(FNX-3),EY(4.5),PX(STX+STR),EY(4.5)); c.line(PX(FNX-3),EY(6.5),PX(STX+STR),EY(6.5))
c.rect(PX(STX-STR),EY(0),2*STR*K,35*K); c.rect(PX(STX-STR-0.75),EY(0),(2*STR+1.5)*K,1.5*K)
# dewatering (behind) and feed screw
rect(PX(FBX-10),EY(0),20*K,12*K,dash=(4,3)); rect(PX(FBX-0.75),EY(DCL+2),1.5*K,10*K,dash=(4,3))
# MCC etc are behind: omit.  Elevation dims
vdim(EY(0),EY(35),PX(STX-STR)-0.5*inch,label='35\'-0" STACK',ext=PX(STX-STR)-0.1*inch,right=False)
vdim(EY(0),EY(22),PX(CYX-CYR)-0.3*inch,label='22\'-0" (REF)',ext=PX(CYX-CYR)-0.1*inch,right=False)
vdim(EY(0),EY(DBT),PX(XD)-0.35*inch,label=fi(HT['dropout_box_top'])+' (REF)',ext=None,right=False)
vdim(EY(0),EY(DCL),PX(train_end)+1.15*inch,label=fi(HT['drum_centreline'])+' DRUM CL',ext=None)
vdim(EY(0),EY(BHT),PX(train_end)+0.6*inch,label=fi(HT['burner_housing_top'])+' (REF)',ext=PX(train_end)+0.1*inch)
hdim(PX(XD),PX(train_end),EY(0)-0.5*inch,label=fi(train_len*12)+' (REF)',ext=EY(0)-0.1*inch,above=False)
hdim(PX(XD+STA['XD'][0]/12),PX(XD+STA['XD'][1]/12),EY(DCL+6.5),label='40\'-0" DRUM',ext=None)
c.setDash([12,3,2,3]); c.setLineWidth(0.4); c.line(PX(XD-2),EY(DCL),PX(train_end+2),EY(DCL)); c.setDash()
# elevation labels
leader(PX(CYX+CYR),EY(18),PX(CYX+CYR+4),EY(28),['HIGH EFFICIENCY','CYCLONE COLLECTOR'])
leader(PX(STX),EY(30),PX(STX-2.5),EY(31),['EXHAUST STACK'],side='l')
leader(PX(FNX),EY(6),PX(FNX-5),EY(11),['60 HP DRYER FAN'],side='l')
leader(PX(CYX),EY(6.5),PX(CYX+1),EY(-2.8),['ROTARY AIRLOCK AND PRODUCT','SCREW TO BUYER\'S BUNKER'])
leader(PX(XD+4),EY(DBT+1.5),PX(XD+10),EY(27),['DRYER EXHAUST DUCT'])
leader(PX(XD+STA['DB'][1]/24),EY(DBT-3),PX(XD+STA['DB'][1]/12+3),EY(DBT+4),['DROP-OUT BOX'])
leader(PX(XD+STA['XD'][1]/12-12),EY(DCL+4.3),PX(XD+STA['XD'][1]/12-8),EY(DCL+11),['MODEL XD-96 ROTARY DRYER'])
leader(PX(XD+STA['XD'][0]/12+8),EY(2),PX(XD+STA['XD'][0]/12+10),EY(-4.2),['REAR TRUNNION BASE'])
leader(PX(XD+STA['XD'][1]/12-9),EY(2),PX(XD+STA['XD'][1]/12-7),EY(-4.2),['FRONT TRUNNION BASE AND DRUM DRIVE'])
leader(PX(FBX),EY(DCL+9),PX(FBX+6),EY(DCL+13),['12" S.S. FEED SCREW FROM','DEWATERING UNIT (BEHIND)'])
leader(PX(XD+(STA['BH'][0]+STA['BH'][1])/24),EY(BHT-2),PX(XD+STA['BH'][1]/12+2),EY(BHT+6),['BURNER HOUSING'])
leader(PX(train_end-3),EY(DCL-1),PX(train_end-12),EY(-4.2),['DUAL FUEL BURNER AND FUEL TRAINS'],side='l')
title(PX(PADW/2),EY(0)-1.15*inch,'ELEVATION VIEW','MODEL XD-96 DRYER SYSTEM')

# ---- END VIEW (looking from the burner end toward the drop-out box)
VX,VY=30.6*inch,9.6*inch
def VXf(w): return VX+w*K
def VYf(h): return VY+h*K
c.setLineWidth(1.0); c.line(VXf(-18),VYf(0),VXf(14),VYf(0))
# stack and cyclone behind (on the centreline)
c.setLineWidth(0.7); c.rect(VXf(-STR),VYf(0),2*STR*K,35*K); c.rect(VXf(-CYR),VYf(14),2*CYR*K,8*K)
c.rect(VXf(-5.8),VYf(0),11.6*K,DBT*K)   # drop-out box
c.setLineWidth(0.5); c.circle(VXf(0),VYf(DCL),HT['tire_od']/24*K); c.circle(VXf(0),VYf(DCL),HT['plan_outline_inner_od']/24*K); c.circle(VXf(0),VYf(DCL),HT['drum_shell_od']/24*K)
c.rect(VXf(-6.5),VYf(0),13*K,2.0*K)   # base frame / skid
for dx in (-4.2,4.2): c.rect(VXf(dx-1.2),VYf(2),2.4*K,2.5*K)   # trunnion bases
c.rect(VXf(-3.5),VYf(5.6),7*K,(BHT-5.6)*K); c.circle(VXf(0),VYf(DCL),1.6*K); c.rect(VXf(-1),VYf(DCL-0.9),2*K,1.8*K)   # burner housing, burner
c.rect(VXf(3.5),VYf(0),4.5*K,4.5*K); c.circle(VXf(5.75),VYf(2.25),1.8*K)   # combustion blower
c.rect(VXf(-11.5),VYf(0),5*K,4*K)  # fuel train skid
vdim(VYf(0),VYf(35),VXf(-16.5),label='35\'-0"',ext=None,right=False); vdim(VYf(0),VYf(DBT),VXf(8),label=fi(HT['dropout_box_top']),ext=None)
hdim(VXf(-HT['tire_od']/24),VXf(HT['tire_od']/24),VYf(DCL+7),label=fi(HT['tire_od'])+' TRACK O.D.',ext=None)
hdim(VXf(-5.8),VXf(5.8),VYf(-1.2),label='11\'-7"',ext=None,above=False)
leader(VXf(0),VYf(30),VXf(3),VYf(31),['EXHAUST STACK']); leader(VXf(CYR),VYf(21),VXf(6),VYf(24),['CYCLONE COLLECTOR (BEHIND)'])
leader(VXf(-5.8),VYf(16),VXf(-9),VYf(19),['DROP-OUT BOX (BEHIND)'],side='l'); leader(VXf(-3.5),VYf(11),VXf(-9),VYf(12.5),['BURNER HOUSING'],side='l')
leader(VXf(5.75),VYf(4),VXf(9),VYf(7),['COMBUSTION AIR BLOWER']); leader(VXf(-4.2),VYf(3.2),VXf(-9),VYf(5.5),['TRUNNION BASE'],side='l')
leader(VXf(-9),VYf(2),VXf(-9),VYf(-2.5),['FUEL TRAINS, LPG AND BIOGAS'],side='l')
title(VX,VY-0.85*inch,'END VIEW','MODEL XD-96 DRYER SYSTEM')
c.showPage(); c.save(); print('written',OUT.name,OUT.stat().st_size,'bytes')
