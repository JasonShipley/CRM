import math
LB=2204.62; BTU_LB=1750; THEO=1144.12
def case(mt, mc_in, mc_cake, mc_out, hrs, capture=1.0):
    feed=mt*LB; ds=feed*(1-mc_in)
    cake=None; press_w=0
    if mc_cake is not None:
        cake_ds=ds*capture; cake=cake_ds/(1-mc_cake); press_w=feed-cake  # pressate incl uncaptured solids
        dry_in=cake; ds_d=cake_ds
    else:
        dry_in=feed; ds_d=ds
    prod=ds_d/(1-mc_out); water=dry_in-prod
    q=water*BTU_LB
    return dict(feed=feed, ds=ds, cake=cake, press_stream=press_w, dryer_in=dry_in, prod=prod, water=water,
                water_hr=water/hrs, q_hr=q/hrs, q_day=q, mt_prod=prod/LB)
V=math.pi*4**2*40
BIOGAS=145.77
print(f"XD-96 drum 8x40 volume {V:.0f} ft3")
rows=[("A 140 tpd, press to 70%MC, 24h",140,0.85,0.70,0.15,24),
      ("A 160 tpd, press to 70%MC, 24h",160,0.85,0.70,0.15,24),
      ("A 140 tpd, press 70%, 20h",140,0.85,0.70,0.15,20),
      ("B 140 tpd, press to 75%MC, 24h",140,0.85,0.75,0.15,24),
      ("B 160 tpd, press to 75%MC, 20h",160,0.85,0.75,0.15,20),
      ("C 140 tpd, NO press, 24h",140,0.85,None,0.15,24),
      ("C 160 tpd, NO press, 24h",160,0.85,None,0.15,24),
      ("ref XD-36: 30 tpd 35->15, 18h",30,0.35,None,0.15,18),
      ("ref XD-60: 75 tpd 35->15, 16h",75,0.35,None,0.15,16)]
print(f"{'case':38s}{'feed lb/d':>10s}{'dryer in lb/h':>14s}{'prod lb/h':>10s}{'water lb/h':>11s}{'MMBtu/h':>9s}{'MMBtu/d':>9s}{'biogas%':>8s}{'lb/h/ft3':>9s}{'prod MT/d':>10s}")
for n,mt,mi,mc,mo,h in rows:
    r=case(mt,mi,mc,mo,h)
    print(f"{n:38s}{r['feed']:10.0f}{r['dryer_in']/h:14.0f}{r['prod']/h:10.0f}{r['water_hr']:11.0f}{r['q_hr']/1e6:9.2f}{r['q_day']/1e6:9.1f}{100*BIOGAS/(r['q_day']/1e6):8.0f}{r['water_hr']/V:9.2f}{r['mt_prod']:10.1f}")
r=case(140,0.85,0.70,0.15,24)
print("\nCase A streams (140 tpd, 24 h): feed %.0f lb/h (%.1f MT/d); pressate %.0f lb/h (%.1f MT/d); cake %.0f lb/h; product %.0f lb/h (%.1f MT/d); water evap %.0f lb/h"%(r['feed']/24,140,r['press_stream']/24,r['press_stream']/LB,r['cake']/24,r['prod']/24,r['mt_prod'],r['water_hr']))
# LPG
lpg_gal=91500; usd=14.5
for n,q in [("A make-up",r['q_day']/1e6-BIOGAS),("A all-LPG",r['q_day']/1e6),("C make-up",case(140,0.85,None,0.15,24)['q_day']/1e6-BIOGAS)]:
    print(f"{n}: {q:.1f} MMBtu/d = {q*1e6/lpg_gal:.0f} gal LPG/d = US${q*usd:,.0f}/d")
# biogas check
nm3=7455; ch4=0.55
print(f"\nBiogas {nm3} Nm3/d -> {nm3/24:.0f} Nm3/h = {nm3/24*37.33/60:.0f} scfm; LHV {nm3*ch4*35.8/1055.06:.1f} MMBtu/d, HHV {nm3*ch4*39.8/1055.06:.1f} MMBtu/d; avg {BIOGAS/24:.2f} MMBtu/h; ~{ch4*1012:.0f} Btu/scf HHV")
# exhaust gas
for label,q,w in [("A 140/24h",r['q_hr'],r['water_hr']),("B 160/20h",case(160,0.85,0.75,0.15,20)['q_hr'],case(160,0.85,0.75,0.15,20)['water_hr']),("C 140/24h",case(140,0.85,None,0.15,24)['q_hr'],case(140,0.85,None,0.15,24)['water_hr'])]:
    Tin=1100; Tamb=85; Tex=230; cp=0.26
    mgas=q/(cp*(Tin-Tamb)); mex=(mgas*1.10)+w  # 10% leakage
    rho=0.0765*(460+60)/(460+Tex)*0.96
    acfm=mex/rho/60
    print(f"exhaust {label}: hot gas {mgas:,.0f} lb/h, exhaust {mex:,.0f} lb/h -> {acfm:,.0f} ACFM @{Tex}F; fan bhp @12inWC ~{acfm*12/(6356*0.65):.0f}; cyclone D @3300fpm Lapple ~{math.sqrt(acfm/3300/0.125):.1f} ft")
