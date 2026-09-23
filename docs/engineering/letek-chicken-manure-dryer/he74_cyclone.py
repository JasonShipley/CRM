"""MCE HE-74 high efficiency cyclone outline for the LETEK drawings (SD-26-01 GA sheet, SD-26-02 DXF layout).

Geometry (inches) from the H-74 dimension table on file (74 in barrel class, the unit on quote 20260917-LETEK-B):
  A  74     barrel diameter                      B  292    overall, expansion chamber bottom to top of outlet plenum (24'-4")
  J  49.4   expansion chamber height             D  151.3  bottom to cone top (barrel bottom flange)
  G  110    cone split flange elevation          F  108    barrel height (roof at 259.3)
  E  32.7   outlet plenum height on the roof     C  199.4  mount pad elevation
  inlet 19 x 45 (tangential, top at the roof)    outlet plenum 37 x 24    discharge 10 in round
  weight about 2,374 lb in 10 ga; 13,275 CFM at 2 in WG, 16,263 CFM at 3 in WG (2016 basis)
All functions return polylines as lists of (x, z) tuples in inches, x from the cyclone centreline, z from the
expansion-chamber bottom (the discharge flange face).  Callers add the stand height and convert units."""
A = 74.0; B = 292.0; D = 151.3; F = 108.0; E = 32.7; J = 49.4; G = 110.0; C = 199.4
ROOF = D + F                      # 259.3
EC_ID = 24.7; DISCH = 10.0; EC_CONE = 12.0
INLET_W, INLET_H = 19.0, 45.0
OUT_T, OUT_U = 37.0, 24.0
WEIGHT_LB = 2374
CFM_2IN, CFM_3IN = 13275, 16263


def cone_radius(z):
    """Radius of the main cone at elevation z (J <= z <= D)."""
    e, r = EC_ID / 2, A / 2
    return e + (r - e) * (z - J) / (D - J)


def elevation():
    """Side elevation (any azimuth; the inlet is the duct end, drawn by the caller)."""
    r, e, d = A / 2, EC_ID / 2, DISCH / 2
    P = []
    for k in (-1, 1):   # left and right profiles
        P.append([(k * d, 0), (k * d, 2), (k * e, EC_CONE), (k * e, J), (k * r, D), (k * r, ROOF)])
    for z, w in ((0, d), (J, e), (D, r), (ROOF, r)):   # horizontal seams / flanges
        P.append([(-w - 1.5, z), (w + 1.5, z)])
    rg = cone_radius(G)
    P.append([(-rg - 1.5, G), (rg + 1.5, G)])          # cone split flange
    P.append([(-d - 2.5, 0), (-d - 2.5, 1.5), (d + 2.5, 1.5), (d + 2.5, 0)])   # discharge flange
    t = OUT_T / 2
    P.append([(-t, ROOF), (-t, B), (t, B), (t, ROOF)])  # outlet plenum (draw-thru fitting) on the riser flange
    P.append([(-t, ROOF + 4), (t, ROOF + 4)])
    for k in (-1, 1):   # mount pads (four at 45 deg; two visible at +/-0.707 R in any side view)
        xp = k * r * 0.7071
        P.append([(xp, C), (xp + k * 6, C), (xp + k * 6, C + 8), (xp, C + 8)])
    # 8 in inspection port on the expansion chamber (octagon)
    import math
    cx, cz, rr = e * 0.0, EC_CONE + (J - EC_CONE) / 2, 4.0
    P.append([(cx + rr * math.cos(a), cz + rr * math.sin(a)) for a in [i * math.pi / 4 for i in range(9)]])
    return P


def stand(z0, leg_offset=None):
    """Four-leg stand: legs outboard of the barrel, top frame under the mount pads, horizontal braces and an
    X-brace in the lower panel.  Returns polylines in (x, z_absolute) inches for a side view, given the cyclone
    base elevation z0 (discharge flange above grade)."""
    r = A / 2
    xo = leg_offset if leg_offset is not None else r + 6
    top = z0 + C            # underside of the mount pads
    P = []
    for k in (-1, 1):
        P.append([(k * xo, 0), (k * xo, top - 8)])                                                      # legs
        P.append([(k * (xo + 6), 0), (k * (xo + 6), 1), (k * (xo - 6), 1), (k * (xo - 6), 0)])         # base plates
    P.append([(-xo - 2, top - 8), (-xo - 2, top), (xo + 2, top), (xo + 2, top - 8), (-xo - 2, top - 8)])   # top frame beam
    mid = (top - 8 + 30) / 2
    for zb in (mid, 30):
        P.append([(-xo, zb), (xo, zb)])                                                                 # horizontal braces
    P.append([(-xo, 30), (xo, mid)]); P.append([(xo, 30), (-xo, mid)])                                  # X brace, lower panel
    return P


def plan(inlet_side=1):
    """Plan view: barrel, riser tube, outlet plenum, discharge, inlet stub (tangential, on inlet_side x).
    Returns (circles [(x, y, r)], polylines)."""
    r = A / 2
    circles = [(0, 0, r), (0, 0, OUT_T / 2), (0, 0, DISCH / 2)]
    t, u = OUT_T / 2, OUT_U / 2
    P = [[(-t, -u), (t, -u), (t, u), (-t, u), (-t, -u)]]   # outlet plenum
    # tangential inlet: 19 wide, inner wall tangent to the barrel, extends 30 in beyond the barrel on inlet_side
    y0, y1 = r - INLET_W, r
    x_edge = 0.0
    P.append([(inlet_side * x_edge, y0), (inlet_side * (x_edge + 30), y0)])
    P.append([(inlet_side * x_edge, y1), (inlet_side * (x_edge + 30), y1)])
    import math
    for a in (45, 135, 225, 315):   # mount pads at 45 deg (stand legs clear the inlet, outlet and product screw)
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        P.append([(r * c - 4 * s, r * s + 4 * c), ((r + 6) * c - 4 * s, (r + 6) * s + 4 * c), ((r + 6) * c + 4 * s, (r + 6) * s - 4 * c), (r * c + 4 * s, r * s - 4 * c), (r * c - 4 * s, r * s + 4 * c)])
    return circles, P
