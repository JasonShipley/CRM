"""SD-26-02: proposed plant layout for LETEK DCG / Bachoco as a 2D CAD file (DXF R2018, inches, model space 1:1).
Plan view with the real 8x40 dryer train line work (xd96_linework.json.gz), sized schematic cyclone / fan / stack,
and dashed PLACEHOLDER blocks for every item not yet defined (dewatering, polymer, scrubber, biogas skid, chiller,
MCC, LPG, bunker, feed pumps).  Elevation and end views below / beside.  Layers keep the classes separate so the
placeholders can be swapped for vendor blocks later.  No vendor, price or lead time appears here."""
import json, gzip, math, zipfile
from pathlib import Path
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
HERE=Path(__file__).parent
DWG='SD-26-02'; REV='P2'; DATE='9/23/2026'
OUT=HERE/('%s_LETEK_Proposed_Layout.dxf'%DWG)
LW=json.load(gzip.open(HERE/'xd96_linework.json.gz')); SIL=json.load(open(HERE/'xd96_silhouette.json'))
HT=SIL['heights_in']; STA=SIL['stations_in']
doc=ezdxf.new('R2018',setup=True); doc.header['$INSUNITS']=1; doc.header['$LUNITS']=4; doc.header['$MEASUREMENT']=0
msp=doc.modelspace()
LAY={'PAD':(8,'DASHED'),'CLEARANCE':(9,'DASHED2'),'DRYER-TRAIN':(7,'Continuous'),'EQUIPMENT':(4,'Continuous'),'PLACEHOLDER':(1,'DASHED'),
     'PLACEHOLDER-TEXT':(1,'Continuous'),'FLOW':(3,'Continuous'),'DIMENSIONS':(2,'Continuous'),'TEXT':(7,'Continuous'),'CENTERLINE':(6,'CENTER'),'TITLE':(7,'Continuous'),'NOTES':(7,'Continuous')}
for n,(col,lt) in LAY.items(): doc.layers.add(n,color=col,linetype=lt)
doc.styles.add('MCE',font='arial.ttf')
ds=doc.dimstyles.new('MCE',dxfattribs={'dimtxt':7,'dimasz':6,'dimexe':4,'dimexo':6,'dimgap':2,'dimdec':0,'dimtxsty':'MCE','dimclrt':2,'dimlunit':4,'dimtih':0,'dimtoh':0,'dimtad':1})
def fi(inches):
    inches=round(inches); f,i=divmod(inches,12); return '%d\'-%d"'%(f,i)
def text(x,y,s,h=7,align=TA.MIDDLE_CENTER,layer='TEXT',rot=0):
    t=msp.add_text(s,height=h,rotation=rot,dxfattribs={'layer':layer,'style':'MCE'}); t.set_placement((x,y),align=align); return t
def mtext(x,y,s,h=7,layer='TEXT',width=None,attach=5):
    m=msp.add_mtext(s,dxfattribs={'layer':layer,'style':'MCE','char_height':h,'attachment_point':attach}); m.set_location((x,y))
    if width: m.dxf.width=width
    return m
def rect(x,y,w,h,layer,close=True): return msp.add_lwpolyline([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],close=close,dxfattribs={'layer':layer})
def placeholder(x,y,w,h,name,status):
    rect(x,y,w,h,'PLACEHOLDER'); msp.add_line((x,y),(x+w,y+h),dxfattribs={'layer':'PLACEHOLDER'}); msp.add_line((x,y+h),(x+w,y),dxfattribs={'layer':'PLACEHOLDER'})
    mtext(x+w/2,y+h/2,'PLACEHOLDER\\P%s\\P%s x %s\\P%s'%(name,fi(w),fi(h),status),h=6,layer='PLACEHOLDER-TEXT',width=w-6)
def hdim(x1,x2,y,txt=None,layer='DIMENSIONS'):
    d=msp.add_linear_dim(base=(x1,y),p1=(x1,y),p2=(x2,y),dimstyle='MCE',text=txt or fi(abs(x2-x1)),dxfattribs={'layer':layer}); d.render(); return d
def vdim(y1,y2,x,txt=None):
    d=msp.add_linear_dim(base=(x,y1),p1=(x,y1),p2=(x,y2),angle=90,dimstyle='MCE',text=txt or fi(abs(y2-y1)),dxfattribs={'layer':'DIMENSIONS'}); d.render(); return d
def leader(tx,ty,lx,ly,lines,side='r'):
    sh=12 if side=='r' else -12
    msp.add_leader([(tx,ty),(lx,ly),(lx+sh,ly)],dxfattribs={'layer':'TEXT'})
    text(lx+sh+(3 if side=='r' else -3),ly,'\n'.join(lines) if False else lines[0],6,TA.MIDDLE_LEFT if side=='r' else TA.MIDDLE_RIGHT)
    for i,s in enumerate(lines[1:],1): text(lx+sh+(3 if side=='r' else -3),ly-8*i,s,6,TA.MIDDLE_LEFT if side=='r' else TA.MIDDLE_RIGHT)
# ---------------- geometry in inches: pad 124 x 64 ft, train centreline y = 37 ft, drop-out far end x = 34 ft, burner to +x
F=12.0; PADW,PADH=124*F,64*F; XD=34*F; YC=37*F
plan=LW['plan']; elev=LW['elevation']; train_len=max(max(s[0],s[2]) for s in plan)*F; train_end=XD+train_len
import he74_cyclone as he74
CYX=26*F; CYR=he74.A/2; CZ0=84.0; FNX=16*F; STX,STR=9*F,1.75*F   # HE-74 cyclone centre, radius, discharge flange 7 ft above grade
CY_TOP=CZ0+he74.B; CY_ROOF=CZ0+he74.ROOF; CY_INL=CY_ROOF-he74.INLET_H; CY_T=he74.OUT_T/2
def polys(P,fx,fy,layer='EQUIPMENT'):
    for pl in P: msp.add_lwpolyline([(fx(x),fy(y)) for x,y in pl],dxfattribs={'layer':layer})
FBX=XD+(STA['FB'][0]+STA['FB'][1])/2
# ---- PLAN VIEW
rect(0,0,PADW,PADH,'PAD'); text(6,PADH+10,'CONCRETE EQUIPMENT PAD %s x %s (BY OTHERS)'%(fi(PADW),fi(PADH)),7,TA.BOTTOM_LEFT)
hdim(0,PADW,PADH+60); vdim(0,PADH,PADW+60)
rect(XD-12*F,YC-18*F,train_len+16*F,36*F,'CLEARANCE'); text(XD-11*F,YC-17*F,"10'-0\" MAINTENANCE CLEARANCE AROUND DRYER TRAIN; CRANE ACCESS ON THE COMBUSTION BLOWER SIDE",6,TA.BOTTOM_LEFT)
for s0,o0,s1,o1 in plan:
    if abs(s1-s0)+abs(o1-o0)>0.02: msp.add_line((XD+s0*F,YC-o0*F),(XD+s1*F,YC-o1*F),dxfattribs={'layer':'DRYER-TRAIN'})
msp.add_line((XD-4*F,YC),(train_end+3*F,YC),dxfattribs={'layer':'CENTERLINE'})
# cyclone, fan, stack, ducting, airlocks (sized schematic on EQUIPMENT)
E={'layer':'EQUIPMENT'}
cyc_circ,cyc_poly=he74.plan(inlet_side=1)   # HE-74 in plan from the dimension sheet, inlet toward the drop-out box
for x,y,r in cyc_circ: msp.add_circle((CYX+x,YC+y),r,dxfattribs=E)
polys(cyc_poly,lambda x:CYX+x,lambda y:YC+y)
rect(CYX-9,YC-9,18,18,'EQUIPMENT'); rect(CYX-6,YC+9,12,50*F-YC-9,'EQUIPMENT')   # airlock under the discharge, product screw north to the bunker
rect(XD+3*F,YC+1*F,4*F,4*F,'EQUIPMENT')   # exhaust riser on the drop-out box top
msp.add_lwpolyline([(XD+3*F,YC+1*F),(XD+1*F,YC+CYR-he74.INLET_W),(CYX,YC+CYR-he74.INLET_W)],dxfattribs=E); msp.add_lwpolyline([(XD+3*F,YC+5*F),(XD+1*F,YC+CYR),(CYX,YC+CYR)],dxfattribs=E)   # transition to the 19 in tangential inlet
msp.add_circle((FNX,YC),3*F,dxfattribs=E); rect(FNX-3.5*F,YC-4.5*F,7*F,9*F,'EQUIPMENT')
msp.add_line((CYX-CY_T,YC-1*F),(FNX+3*F,YC-1*F),dxfattribs=E); msp.add_line((CYX-CY_T,YC+1*F),(FNX+3*F,YC+1*F),dxfattribs=E)
msp.add_circle((STX,YC),STR,dxfattribs=E); msp.add_line((FNX-3*F,YC-1.2*F),(STX+STR,YC-1.2*F),dxfattribs=E); msp.add_line((FNX-3*F,YC+1.2*F),(STX+STR,YC+1.2*F),dxfattribs=E)
rect(XD+4*F,YC+6.5*F,3*F,2*F,'EQUIPMENT'); rect(XD+5.25*F,YC+8.5*F,1.5*F,(50*F-YC-8.5*F),'EQUIPMENT')   # discharge airlock + product conveyor
rect(FBX-0.75*F,YC+3*F,1.5*F,10*F,'EQUIPMENT')   # feed screw
# placeholders (dashed, crossed, labelled)
placeholder(FBX-10*F,50*F,20*F,14*F,'DEWATERING UNIT WITH FEED TANK\\P(DECANTER OR SCREW PRESS)','SIZE TBD AFTER SAMPLE TEST')
placeholder(FBX+12*F,52*F,8*F,8*F,'POLYMER MAKE-UP SYSTEM','IF REQUIRED - TBD')
placeholder(FBX-20*F,57*F,8*F,6*F,'DIGESTATE FEED PUMPS','BY OTHERS')
placeholder(20*F,50*F,20*F,14*F,'DRIED PRODUCT BUNKER / BAGGING','BY OTHERS - 3 DAYS STORAGE')
placeholder(2*F,44*F,12*F,12*F,'EXHAUST SCRUBBER','IF REQUIRED BY AIR PERMIT - TBD')
placeholder(84*F,2*F,24*F,10*F,'BIOGAS CONDITIONING SKID','MCE DESIGN BGS-001 - VENDOR TBD')
placeholder(76*F,3*F,6*F,8*F,'GAS CHILLER','TBD')
placeholder(56*F,2*F,16*F,10*F,'MCC / CONTROL ROOM','TBD')
placeholder(112*F,2*F,10*F,10*F,'LPG VAPORIZER / REGULATOR STATION','BY OTHERS')
placeholder(40*F,2*F,10*F,8*F,'AIR COMPRESSOR / INSTRUMENT AIR','TBD')
# flow arrows (simple polylines) on FLOW
def flow(pts,label=None,lpos=None):
    msp.add_lwpolyline(pts,dxfattribs={'layer':'FLOW'})
    (x1,y1),(x2,y2)=pts[-2],pts[-1]; a=math.atan2(y2-y1,x2-x1); s=8
    msp.add_lwpolyline([(x2-s*math.cos(a-0.4),y2-s*math.sin(a-0.4)),(x2,y2),(x2-s*math.cos(a+0.4),y2-s*math.sin(a+0.4))],dxfattribs={'layer':'FLOW'})
    if label: text(*(lpos or (pts[0][0],pts[0][1]+6)),label,5,TA.BOTTOM_LEFT,'FLOW')
flow([(FBX-30*F,60*F),(FBX-20*F,60*F)],'DIGESTATE FROM DIGESTER (BY OTHERS)',(FBX-34*F,52*F))
flow([(FBX-12*F,60*F),(FBX-10*F,60*F)]); flow([(FBX,50*F),(FBX,YC+13*F)],'CAKE')
flow([(XD+6*F,50*F),(XD+6*F,52*F),(40*F,52*F)],'DRIED PRODUCT')
flow([(96*F,-4*F),(96*F,2*F)],'RAW BIOGAS FROM DIGESTER <50 MBAR (BY OTHERS)')
flow([(84*F,7*F),(82*F,7*F)]); flow([(79*F,11*F),(79*F,20*F),(train_end-14*F,20*F),(train_end-14*F,YC-4*F)],'CONDITIONED BIOGAS 2 PSIG')
flow([(117*F,12*F),(117*F,24*F),(train_end-8*F,24*F),(train_end-8*F,YC-3*F)],'LPG VAPOR 5 PSIG')
# plan dims and labels
hdim(XD,train_end,YC-20*F,fi(train_len)+' DRYER TRAIN OVERALL (REF)'); hdim(XD+STA['XD'][0],XD+STA['XD'][1],YC+11*F,"40'-0\" DRUM")
hdim(STX-STR,train_end,YC-23*F,fi(train_end-STX+STR)+' STACK TO FUEL TRAIN (REF)'); hdim(CYX-CYR,CYX+CYR,YC-5.5*F,"6'-2\" DIA HE-74 CYCLONE")
leader(CYX+2*F,YC-2.3*F,CYX+2*F,YC+16*F,['MODEL HE-74 HIGH EFFICIENCY CYCLONE COLLECTOR','74" DIA, WITH ROTARY AIRLOCK']); leader(FNX,YC-2*F,FNX-4*F,YC-11*F,['60 HP DRYER FAN'],'l')
leader(STX,YC+1*F,STX-3*F,YC+9*F,['EXHAUST STACK 35\'-0" HIGH'],'l'); leader(XD+5.5*F,YC+7.5*F,XD-8*F,YC+10.5*F,['ROTARY AIRLOCK AND','PRODUCT CONVEYOR'],'l')
leader(XD+STA['DB'][1]/2,YC-5*F,XD+2*F,YC-11*F,['DROP-OUT BOX'],'l'); leader(XD+STA['XD'][1]-8*F,YC+4.4*F,XD+STA['XD'][1]-4*F,YC+16*F,['MODEL XD-96 ROTARY DRYER','8\'-0" DIA x 40\'-0" DRUM'])
leader(XD+30*F,YC-4.5*F,XD+32*F,YC-13*F,['SADDLE MOUNT DRUM DRIVE, 30 HP']); leader(FBX,YC+8*F,FBX+6*F,YC+11*F,['12" S.S. FEED SCREW x 10\'-0"'])
leader(XD+(STA['BH'][0]+STA['BH'][1])/2,YC-3.8*F,XD+STA['BH'][0]+2*F,YC-12.5*F,['BURNER HOUSING']); leader(XD+STA['FB'][1]+1*F,YC-7.5*F,XD+STA['FB'][1]+6*F,YC-16*F,['COMBUSTION AIR BLOWER'])
leader(train_end-4*F,YC+1*F,train_end-6*F,YC+8*F,['10 MMBTU/HR DUAL FUEL BURNER','(LPG / BIOGAS) WITH FUEL TRAINS'])
text(2*F,1*F,'TRUCK ACCESS AND LPG TANK FARM: THIS SIDE, LOCATION PER BUYER\'S SITE PLAN',6,TA.BOTTOM_LEFT)
# north arrow
nx,ny=PADW+120,PADH-20; msp.add_line((nx,ny-40),(nx,ny+20),dxfattribs={'layer':'TEXT'}); msp.add_lwpolyline([(nx-6,ny+8),(nx,ny+20),(nx+6,ny+8)],close=True,dxfattribs={'layer':'TEXT'}); text(nx,ny+28,'N (ARBITRARY)',6)
text(PADW/2,-9*F,'PLAN VIEW - PROPOSED LAYOUT',14,TA.MIDDLE_CENTER,'TITLE'); text(PADW/2,-13*F,'MODEL XD-96 DRYER SYSTEM - DIMENSIONS IN INCHES, MODEL 1:1',7)
# ---- ELEVATION VIEW (grade at EY0)
EY0=-66*F
def EY(hft): return EY0+hft*F
msp.add_line((0,EY0),(PADW,EY0),dxfattribs={'layer':'PAD'}); text(6,EY0-9,'GRADE',6,TA.TOP_LEFT)
for s0,h0,s1,h1 in elev:
    if abs(s1-s0)+abs(h1-h0)>0.02: msp.add_line((XD+s0*F,EY(h0)),(XD+s1*F,EY(h1)),dxfattribs={'layer':'DRYER-TRAIN'})
DBT=HT['dropout_box_top']/12; DCL=HT['drum_centreline']/12; BHT=HT['burner_housing_top']/12
# HE-74 cyclone from the dimension sheet, discharge flange at CZ0 (7 ft), four-leg stand, airlock and screw below
polys(he74.elevation(),lambda x:CYX+x,lambda z:EY0+CZ0+z); polys(he74.stand(CZ0),lambda x:CYX+x,lambda z:EY0+z)
rect(CYX-9,EY0+CZ0-18,18,18,'EQUIPMENT'); rect(CYX-6,EY0+CZ0-30,12,12,'EQUIPMENT')
# exhaust duct: 4 ft riser out of the TOP of the drop-out box, elbow, horizontal run into the 19 x 45 in tangential inlet at the barrel top
msp.add_lwpolyline([(XD+7*F,EY(DBT)),(XD+7*F,EY0+CY_ROOF),(CYX+CYR,EY0+CY_ROOF)],dxfattribs=E); msp.add_lwpolyline([(XD+3*F,EY(DBT)),(XD+3*F,EY0+CY_INL),(CYX+CYR,EY0+CY_INL)],dxfattribs=E)
# outlet plenum (37 x 24) to the fan inlet
msp.add_line((CYX-CY_T,EY0+CY_ROOF+4),(FNX+1*F,EY0+CY_ROOF+4),dxfattribs=E); msp.add_line((CYX-CY_T,EY0+CY_TOP-4),(FNX-1*F,EY0+CY_TOP-4),dxfattribs=E)
msp.add_line((FNX+1*F,EY0+CY_ROOF+4),(FNX+1*F,EY(7.5)),dxfattribs=E); msp.add_line((FNX-1*F,EY0+CY_TOP-4),(FNX-1*F,EY(7.5)),dxfattribs=E)
msp.add_circle((FNX,EY(4.5)),3*F,dxfattribs=E); rect(FNX-3.5*F,EY0,7*F,1.5*F,'EQUIPMENT'); rect(FNX+3.5*F,EY0,3*F,3.5*F,'EQUIPMENT'); rect(FNX-2.5*F,EY0,1*F,7.5*F,'EQUIPMENT')
msp.add_line((FNX-3*F,EY(4.5)),(STX+STR,EY(4.5)),dxfattribs=E); msp.add_line((FNX-3*F,EY(6.5)),(STX+STR,EY(6.5)),dxfattribs=E)
rect(STX-STR,EY0,2*STR,35*F,'EQUIPMENT'); rect(STX-STR-9,EY0,2*STR+18,1.5*F,'EQUIPMENT')
rect(FBX-0.75*F,EY(DCL+2),1.5*F,10*F,'PLACEHOLDER')
msp.add_line((XD-2*F,EY(DCL)),(train_end+2*F,EY(DCL)),dxfattribs={'layer':'CENTERLINE'})
vdim(EY0,EY(35),STX-STR-30,"35'-0\" STACK"); vdim(EY0,EY0+CY_TOP,CYX-CYR-24,fi(CY_TOP)+' (REF)'); vdim(EY0,EY(DBT),XD-28,fi(HT['dropout_box_top'])+' (REF)')
vdim(EY0,EY(BHT),train_end+40,fi(HT['burner_housing_top'])+' (REF)'); vdim(EY0,EY(DCL),train_end+80,fi(HT['drum_centreline'])+' DRUM CL')
hdim(XD,train_end,EY0-36,fi(train_len)+' (REF)'); hdim(XD+STA['XD'][0],XD+STA['XD'][1],EY(DCL+6.5),"40'-0\" DRUM")
leader(CYX+CYR,EY0+CZ0+15*F,CYX+CYR+3.5*F,EY(35.5),['MODEL HE-74 HIGH EFFICIENCY CYCLONE COLLECTOR, 74" DIA']); leader(STX,EY(30),STX-2.5*F,EY(31),['EXHAUST STACK'],'l')
leader(FNX,EY(6),FNX-5*F,EY(11),['60 HP DRYER FAN'],'l'); leader(CYX,EY0+CZ0-9,CYX+1*F,EY(-3.5),['ROTARY AIRLOCK AND PRODUCT SCREW TO BUNKER'])
leader(XD+5*F,EY(22),XD+10*F,EY(33),['DRYER EXHAUST DUCT']); leader(XD+STA['DB'][1]/2,EY(DBT-3),XD+STA['DB'][1]+3*F,EY(DBT+4),['DROP-OUT BOX'])
leader(XD+STA['XD'][1]-12*F,EY(DCL+4.3),XD+STA['XD'][1]-8*F,EY(DCL+11),['MODEL XD-96 ROTARY DRYER'])
leader(XD+STA['XD'][0]+8*F,EY(2),XD+STA['XD'][0]+10*F,EY(-5.5),['REAR TRUNNION BASE']); leader(XD+STA['XD'][1]-9*F,EY(2),XD+STA['XD'][1]-7*F,EY(-5.5),['FRONT TRUNNION BASE AND DRUM DRIVE'])
leader(FBX,EY(DCL+9),FBX+6*F,EY(DCL+13),['12" S.S. FEED SCREW FROM DEWATERING UNIT','(BEHIND, NOT SHOWN)']); leader(XD+(STA['BH'][0]+STA['BH'][1])/2,EY(BHT-2),XD+STA['BH'][1]+2*F,EY(BHT+6),['BURNER HOUSING'])
leader(train_end-3*F,EY(DCL-1),train_end+8*F,EY(-3.5),['DUAL FUEL BURNER AND FUEL TRAINS'])
text(PADW/2,EY0-9*F,'ELEVATION VIEW',14,TA.MIDDLE_CENTER,'TITLE'); text(PADW/2,EY0-13*F,'MODEL XD-96 DRYER SYSTEM',7)
# ---- END VIEW (from the burner end), right of the plan
VX,VY=PADW+40*F,0
def VXf(w): return VX+w*F
def VYf(h): return VY+h*F
msp.add_line((VXf(-21),VY),(VXf(14),VY),dxfattribs={'layer':'PAD'})
rect(VXf(-1.75),VY,3.5*F,35*F,'EQUIPMENT'); polys(he74.elevation(),lambda x:VXf(0)+x,lambda z:VY+CZ0+z); polys(he74.stand(CZ0),lambda x:VXf(0)+x,lambda z:VY+z); rect(VXf(-5.8),VY,11.6*F,DBT*F,'DRYER-TRAIN')
for r in (HT['tire_od']/2,HT['plan_outline_inner_od']/2,HT['drum_shell_od']/2): msp.add_circle((VXf(0),VYf(DCL)),r,dxfattribs={'layer':'DRYER-TRAIN'})
rect(VXf(-6.5),VY,13*F,2*F,'DRYER-TRAIN')
for dx in (-4.2,4.2): rect(VXf(dx-1.2),VYf(2),2.4*F,2.5*F,'DRYER-TRAIN')
rect(VXf(-3.5),VYf(5.6),7*F,(BHT-5.6)*F,'DRYER-TRAIN'); msp.add_circle((VXf(0),VYf(DCL)),1.6*F,dxfattribs={'layer':'DRYER-TRAIN'}); rect(VXf(-1),VYf(DCL-0.9),2*F,1.8*F,'DRYER-TRAIN')
rect(VXf(3.5),VY,4.5*F,4.5*F,'DRYER-TRAIN'); msp.add_circle((VXf(5.75),VYf(2.25)),1.8*F,dxfattribs={'layer':'DRYER-TRAIN'}); rect(VXf(-11.5),VY,5*F,4*F,'DRYER-TRAIN')
vdim(VY,VYf(35),VXf(-19),"35'-0\""); vdim(VY,VYf(DBT),VXf(8),fi(HT['dropout_box_top'])); hdim(VXf(-HT['tire_od']/24),VXf(HT['tire_od']/24),VYf(DCL+7),fi(HT['tire_od'])+' TRACK O.D.'); hdim(VXf(-5.8),VXf(5.8),VYf(-1.5),"11'-7\"")
leader(VXf(0),VYf(30),VXf(3),VYf(31),['EXHAUST STACK']); leader(VXf(3),VYf(25),VXf(6),VYf(27),['HE-74 CYCLONE (BEHIND)'])
leader(VXf(-5.8),VYf(16),VXf(-8),VYf(19.5),['DROP-OUT BOX (BEHIND)'],'l'); leader(VXf(-3.5),VYf(11),VXf(-9),VYf(12.5),['BURNER HOUSING'],'l')
leader(VXf(5.75),VYf(4),VXf(9),VYf(7),['COMBUSTION AIR BLOWER']); leader(VXf(-4.2),VYf(3.2),VXf(-9),VYf(5.5),['TRUNNION BASE'],'l'); leader(VXf(-9),VYf(2),VXf(-9),VYf(-3.5),['FUEL TRAINS, LPG AND BIOGAS'],'l')
text(VX,VY-9*F,'END VIEW',14,TA.MIDDLE_CENTER,'TITLE'); text(VX,VY-13*F,'MODEL XD-96 DRYER SYSTEM - FROM THE BURNER END',7)
# ---- title block and notes (model space, bottom right)
TX,TY,TW,TH=PADW+8*F,EY0-8*F,60*F,30*F
rect(TX,TY,TW,TH,'TITLE'); msp.add_line((TX,TY+TH-7*F),(TX+TW,TY+TH-7*F),dxfattribs={'layer':'TITLE'}); msp.add_line((TX,TY+TH-14*F),(TX+TW,TY+TH-14*F),dxfattribs={'layer':'TITLE'})
msp.add_line((TX,TY+8*F),(TX+TW,TY+8*F),dxfattribs={'layer':'TITLE'}); msp.add_line((TX+20*F,TY),(TX+20*F,TY+8*F),dxfattribs={'layer':'TITLE'}); msp.add_line((TX+40*F,TY),(TX+40*F,TY+8*F),dxfattribs={'layer':'TITLE'})
text(TX+TW/2,TY+TH-3.5*F,'MIDWEST CUSTOM ENGINEERING, INC. - STUART, FL - USEMCE.COM',12,TA.MIDDLE_CENTER,'TITLE')
text(TX+TW/2,TY+TH-10.5*F,'MCE PROPOSED PLANT LAYOUT - PLAN, ELEVATION AND END VIEW',10,TA.MIDDLE_CENTER,'TITLE')
mtext(TX+TW/2,TY+TH-14*F-2*F,'LETEK DCG / BACHOCO - MODEL XD-96 8\'-0" x 40\'-0" ROTARY DRYER SYSTEM\\PMERIDA, YUCATAN - PRELIMINARY, FOR SITE PLANNING ONLY\\PPROPRIETARY AND CONFIDENTIAL - PROPERTY OF MIDWEST CUSTOM ENGINEERING, INC. - COPYRIGHT 2026',7,'TITLE',width=TW-12,attach=2)
text(TX+3,TY+7*F,'DRAWN: MCE   DATE: %s'%DATE,6,TA.TOP_LEFT,'TITLE'); text(TX+20*F+3,TY+7*F,'UNITS: INCHES   SCALE: 1:1 MODEL',6,TA.TOP_LEFT,'TITLE'); text(TX+40*F+3,TY+7*F,'DRAWING NO.',6,TA.TOP_LEFT,'TITLE')
text(TX+50*F,TY+3*F,'%s  REV %s'%(DWG,REV),12,TA.MIDDLE_CENTER,'TITLE')
NOTES=['GENERAL NOTES',
 '1. PRELIMINARY ARRANGEMENT FOR SITE PLANNING. DRYER TRAIN LINE WORK (LAYER DRYER-TRAIN) IS FROM THE MCE 8x40 DRYER GENERAL ARRANGEMENT AND IS TO SCALE.',
 '2. ITEMS ON LAYER PLACEHOLDER ARE NOT YET DEFINED: THE DASHED, CROSSED RECTANGLES RESERVE SPACE AT THE SIZE SHOWN AND WILL BE REPLACED BY VENDOR BLOCKS WHEN SELECTED.',
 '3. CYCLONE OUTLINE IS FROM THE MCE HE-74 DIMENSION SHEET (74 IN BARREL, 24\'-4" OVERALL, ABOUT 2,400 LB). FAN, STACK, DUCTING, AIRLOCKS AND SCREWS',
 '   (LAYER EQUIPMENT) ARE SIZED SCHEMATICALLY AND WILL BE DETAILED IN FINAL ENGINEERING. CERTIFIED DRAWINGS ARE ISSUED FOR APPROVAL WITH AN ORDER.',
 '4. BASIS: 140 MT/DAY DIGESTATE AT 8% TS, DEWATERED TO 22-30% TS, DRIED TO 15% MOISTURE; 10 MMBTU/HR DUAL-FUEL BURNER, BIOGAS PRIMARY, LPG STAND-BY.',
 '5. WEIGHTS FOR FOUNDATION DESIGN: DRUM AND SKID 79,900 LB EMPTY + 19,300 LB MATERIAL RUNNING; BURNER ASSEMBLY 16,000 LB; DROP-OUT BOX 9,300 LB.',
 '6. UTILITIES: 480V/3/60 (OR 440V/60), ~160 HP CONNECTED; BIOGAS <50 MBAR TO SKID, 2 PSIG TO BURNER; LPG VAPOR 5 PSIG (BY OTHERS); INSTRUMENT AIR 5 SCFM AT 90 PSIG.',
 '7. PAD 124\'-0" x 64\'-0", ROOF OVER DRYER TRAIN, DEWATERING AND SKID RECOMMENDED. LPG TANKS MIN. 50\'-0" FROM THE DRYER. EQUIPMENT CAN BE ROTATED TO SUIT THE SITE.',
 '8. LAYERS: PAD, CLEARANCE, DRYER-TRAIN, EQUIPMENT, PLACEHOLDER, PLACEHOLDER-TEXT, FLOW, DIMENSIONS, TEXT, CENTERLINE, TITLE, NOTES.']
for i,s in enumerate(NOTES): text(TX,TY-6*F-9*i,s,7 if i==0 else 5.5,TA.TOP_LEFT,'NOTES')
doc.audit(); doc.saveas(OUT)
with zipfile.ZipFile(str(OUT)+'.zip','w',zipfile.ZIP_DEFLATED) as z: z.write(OUT,OUT.name)
print('written',OUT.name,OUT.stat().st_size,'bytes; zip',Path(str(OUT)+'.zip').stat().st_size)
