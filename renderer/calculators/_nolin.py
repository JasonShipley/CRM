#!/usr/bin/env python3
"""Nolin Milling's 2026 catalog — the air-handling pages, as printed.

MCE buys its primed gray ductwork from Nolin. This module holds the catalog's own
tables verbatim so a duct run prices itself off a page anybody can check, rather
than off a fabricated-weight guess.

The tables below are laid out the way the catalog prints them and parsed at
import, so a row can be read against the page it came from:

    page  3   spouting, plain end, per foot — what the catalog sends you to for
              duct under 9 in — plus priming charges and angle iron flange rings
    page 43   primed gray ductwork (10 ft sticks), segmented elbows, and the
              offset / Y / 3-way damper valves
    page 44   accessories: flange rings, clamp bands, round-to-round reducers,
              blast gates, round dampers, compression couplings and branches
    page 45   hanger straps, removable back sweep elbows, bird screens and hoods

Catalog terms, from page 3: 2 % 10 days, net 30; all material FOB Dickens, Iowa;
pricing subject to change without notice. These are Nolin's list prices as
published — MCE's own markup is applied in _vendor.py, not here.

Everything here was transcribed from the catalog's page images. test_nolin.py
checks the shape of every table the way the page reads: heavier gauge costs more
than lighter at the same size, a bigger duct costs more than a smaller one at the
same gauge, and a 90 degree elbow costs more than a 60, a 45 and a 30.
"""
import statistics

SOURCE = "Nolin Milling 2026 catalog"
CATALOG_DATE = "2026-05"
TERMS = ("2% 10 days, net 30; all material FOB Dickens, Iowa; pricing subject to "
         "change without notice")
STICK_FT = 10                    # primed gray duct ships in 10 ft lengths
GAUGES = ["14", "12", "10", "7", "1/4"]
GAUGE_ORDER = {g: i for i, g in enumerate(GAUGES)}     # lighter -> heavier


def _table(text, keys, first="int"):
    """Parse a printed table. '-' is a cell the catalog leaves blank."""
    out = {}
    for line in text.strip().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        cells = line.split()
        head = int(cells[0]) if first == "int" else cells[0]
        row = {}
        for key, cell in zip(keys, cells[1:]):
            if cell != "-":
                row[key] = float(cell)
        out[head] = row
    return out


def _bands(text):
    """A table whose left column is a list of sizes sharing one price row."""
    out = {}
    for line in text.strip().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        sizes, _, rest = line.partition(":")
        cells = rest.split()
        for token in sizes.split(","):
            token = token.strip()
            if "-" in token:
                lo, hi = (int(x) for x in token.split("-"))
                span = range(lo, hi + 1)
            else:
                span = [int(token)]
            for size in span:
                out[size] = [float(c) for c in cells]
    return out


# --- page 43: primed gray ductwork ---------------------------------------------
# 10 ft long, carbon steel, welded seam, flanged, prime painted. All OD.
# 3" to 16" -> use spouting, page 3. 38" and up -> call for pricing.
#   dia      14 Ga     12 Ga     10 Ga      7 Ga      1/4"
DUCT_STICK = _table("""
    9       479.00    539.00         -         -         -
   11       499.00    579.00         -         -         -
   13       499.00    579.00    759.00         -         -
   15       499.00    579.00    759.00   1099.00         -
   17       579.00    649.00    839.00   1099.00         -
   18       579.00    649.00    839.00   1099.00   1519.00
   19       629.00    709.00    859.00   1229.00   1889.00
   20       639.00    719.00    869.00   1249.00   1899.00
   21       679.00    759.00    989.00   1359.00   2069.00
   22       689.00    779.00   1019.00   1369.00   2109.00
   23       769.00    859.00   1069.00   1489.00   2279.00
   24       779.00    869.00   1079.00   1509.00   2289.00
   26       819.00    939.00   1189.00   1669.00   2759.00
   28       889.00    999.00   1279.00   1779.00   2979.00
   30       949.00   1079.00   1339.00   1879.00   3139.00
   32      1039.00   1249.00   1619.00   2229.00   3759.00
   34      1199.00   1359.00   1709.00   2359.00   3959.00
   36      1259.00   1449.00   1849.00   2489.00   4289.00
""", GAUGES)

# --- page 43: segmented elbows for air ------------------------------------------
# 90 deg 7 gore, 60 deg 5 gore, 45 deg 4 gore, 30 deg 3 gore. Same price flanged or
# with 4 in unflanged tube extensions. 40" and up -> call for pricing.
ELBOW_CENTERLINE = {}
_ELBOW_KEYS = [f"{a}:{g}" for a in ("90", "60", "45", "30") for g in ("14", "12", "10", "7")]
_ELBOWS_RAW = _table("""
#  dia  CL  ----------- 90 deg ----------  ----------- 60 deg ----------  ----------- 45 deg ----------  ----------- 30 deg ----------
#           14Ga    12Ga    10Ga     7Ga    14Ga    12Ga    10Ga     7Ga    14Ga    12Ga    10Ga     7Ga    14Ga    12Ga    10Ga     7Ga
    3  24  129.0   149.0       -       -   109.0   119.0       -       -    89.0   109.0       -       -    79.0    89.0       -       -
    4  24  159.0   169.0   209.0   259.0   129.0   149.0   169.0   209.0   119.0   129.0   149.0   169.0    89.0   109.0   119.0   149.0
    5  24  169.0   199.0   219.0   279.0   149.0   159.0   199.0   219.0   119.0   129.0   159.0   189.0    89.0   109.0   119.0   149.0
    6  24  199.0   209.0   249.0   289.0   159.0   169.0   199.0   239.0   129.0   149.0   159.0   209.0   109.0   119.0   129.0   159.0
    7  24  209.0   219.0   259.0   299.0   169.0   199.0   209.0   259.0   149.0   159.0   169.0   209.0   109.0   119.0   129.0   159.0
    8  24  209.0   219.0   259.0   299.0   169.0   199.0   209.0   259.0   149.0   159.0   169.0   209.0   109.0   119.0   129.0   159.0
    9  24  219.0   239.0   279.0   339.0   169.0   199.0   219.0   279.0   149.0   159.0   169.0   219.0   109.0   119.0   129.0   169.0
   10  24  219.0   249.0   289.0   369.0   199.0   209.0   249.0   289.0   159.0   189.0   199.0   239.0   119.0   129.0   149.0   189.0
   11  36  259.0   299.0   369.0   409.0   209.0   239.0   299.0   379.0   169.0   199.0   249.0   279.0   129.0   149.0   169.0   209.0
   12  36  279.0   319.0   389.0   419.0   219.0   249.0   319.0   389.0   199.0   209.0   259.0   289.0   149.0   159.0   199.0   219.0
   13  36  339.0   389.0   459.0   579.0   279.0   319.0   369.0   459.0   219.0   249.0   299.0   379.0   169.0   199.0   219.0   289.0
   14  36  349.0   409.0   469.0   599.0   289.0   329.0   389.0   479.0   239.0   259.0   319.0   389.0   199.0   209.0   249.0   299.0
   15  48  499.0   559.0   609.0   769.0   409.0   449.0   479.0   629.0   319.0   369.0   409.0   509.0   249.0   279.0   299.0   389.0
   16  48  509.0   579.0   629.0   779.0   419.0   469.0   509.0   639.0   339.0   379.0   419.0   519.0   259.0   299.0   319.0   409.0
   17  48  609.0   689.0   769.0   989.0   469.0   549.0   609.0   779.0   409.0   449.0   509.0   639.0   299.0   349.0   389.0   499.0
   18  48  609.0   709.0   779.0   999.0   499.0   559.0   629.0   819.0   419.0   469.0   539.0   649.0   319.0   369.0   409.0   509.0
   19  48  689.0   769.0   899.0  1159.0   549.0   609.0   729.0   939.0   459.0   519.0   589.0   759.0   339.0   389.0   449.0   579.0
   20  48  709.0   779.0   909.0  1189.0   559.0   629.0   739.0   949.0   469.0   539.0   599.0   769.0   349.0   409.0   459.0   599.0
   21  48  849.0   939.0  1079.0  1329.0   679.0   759.0   869.0  1069.0   549.0   609.0   719.0   859.0   419.0   469.0   549.0   649.0
   22  48  859.0   969.0  1109.0  1339.0   689.0   769.0   889.0  1079.0   559.0   629.0   729.0   869.0   429.0   479.0   559.0   669.0
   23  48  989.0  1119.0  1279.0  1639.0   799.0   899.0  1029.0  1329.0   649.0   729.0   849.0  1079.0   499.0   559.0   629.0   839.0
   24  48  999.0  1129.0  1299.0  1669.0   809.0   909.0  1039.0  1339.0   669.0   739.0   859.0  1099.0   509.0   579.0   639.0   849.0
   26  48 1119.0  1259.0  1469.0  1899.0   899.0  1019.0  1169.0  1539.0   739.0   839.0   979.0  1229.0   579.0   639.0   759.0   969.0
   28  48 1149.0  1319.0  1559.0  2029.0   939.0  1059.0  1259.0  1629.0   759.0   849.0  1019.0  1329.0   589.0   649.0   779.0  1029.0
   30  48 1319.0  1499.0  1729.0  2139.0  1069.0  1199.0  1389.0  1709.0   869.0   989.0  1129.0  1389.0   679.0   759.0   859.0  1069.0
   32  48 1499.0  1679.0  1899.0  2379.0  1189.0  1369.0  1519.0  1909.0   989.0  1109.0  1239.0  1539.0   739.0   839.0   979.0  1209.0
   34  48 1519.0  1719.0  1989.0  2429.0  1229.0  1389.0  1599.0  1979.0   999.0  1119.0  1319.0  1599.0   779.0   869.0   999.0  1239.0
   36  60 1589.0  1799.0  2039.0  2619.0  1289.0  1429.0  1639.0  2099.0  1029.0  1189.0  1339.0  1709.0   809.0   899.0  1029.0  1319.0
""", ["cl"] + _ELBOW_KEYS)

ELBOW = {}
for _dia, _row in _ELBOW_RAW_ITEMS if False else _ELBOWS_RAW.items():
    ELBOW_CENTERLINE[_dia] = int(_row["cl"])
    ELBOW[_dia] = {angle: {g: _row[f"{angle}:{g}"]
                           for g in ("14", "12", "10", "7") if f"{angle}:{g}" in _row}
                   for angle in ("90", "60", "45", "30")}

# --- page 44: round to round reducers -------------------------------------------
# The "air adaptor" on an MCE air system. 2 in reduction is 6 in tall, 4 in is 12 in.
#   (large, small)          14 Ga    12 Ga    10 Ga
REDUCER = {}
for _line in """
     6  4    79.00    79.00    89.00
     8  6    79.00    79.00    89.00
     8  4    89.00   109.00   129.00
    10  8    79.00    89.00   119.00
    10  6   109.00   119.00   149.00
    12 10    89.00   109.00   129.00
    12  8   109.00   119.00   149.00
    14 12   109.00   119.00   149.00
    14 10   119.00   129.00   159.00
    16 14   149.00   159.00   189.00
    16 12   159.00   189.00   219.00
    16 10   169.00   189.00   239.00
    18 16   159.00   189.00   219.00
    18 14   169.00   189.00   239.00
    20 18   209.00   219.00   259.00
    20 16   239.00   259.00   319.00
    24 20   279.00   319.00   369.00
""".strip().splitlines():
    _c = _line.split()
    REDUCER[(int(_c[0]), int(_c[1]))] = dict(zip(("14", "12", "10"),
                                                 (float(x) for x in _c[2:])))

# Page 44: square to rounds and square to squares — the transition off a square
# hood, a plenum flange or a rectangular pickup onto round duct.
#   (square_in, round_in)     14 Ga    12 Ga    10 Ga
SQUARE_TO_ROUND = {}
for _line in """
     4  4    59.00    59.00    69.00
     6  6    59.00    59.00    69.00
     6  4    59.00    69.00    79.00
     8  8    59.00    59.00    69.00
     8  6    59.00    69.00    79.00
    10 10    59.00    69.00    79.00
    10  8    69.00    79.00    79.00
    10  6    69.00    79.00    79.00
    12 12    79.00    89.00   109.00
    12 10    89.00   109.00   119.00
    12  8    89.00   109.00   119.00
    14 14    89.00   109.00   129.00
    14 12   109.00   119.00   149.00
    14 10   119.00   129.00   159.00
    16 16   129.00   159.00   189.00
    16 14   149.00   169.00   199.00
    16 12   159.00   189.00   219.00
    16 10   159.00   189.00   219.00
    18 18   159.00   189.00   219.00
    18 16   169.00   189.00   239.00
    18 14   169.00   189.00   239.00
    20 20   189.00   209.00   249.00
    20 18   209.00   239.00   279.00
    20 16   219.00   249.00   299.00
    24 24   249.00   279.00   329.00
    24 22   259.00   299.00   349.00
    24 20   279.00   319.00   369.00
""".strip().splitlines():
    _c = _line.split()
    SQUARE_TO_ROUND[(int(_c[0]), int(_c[1]))] = dict(
        zip(("14", "12", "10"), (float(x) for x in _c[2:])))


# --- page 44: accessories -------------------------------------------------------
# Angle iron flange rings, punched, bare steel. Two per duct joint.
FLANGE_RING = _bands("""
    3,4,5:      6.49
    6:          8.49
    7,8:        8.99
    9,10:      10.79
    11,12:     19.29
    13,14:     20.79
    15:        28.89
    16:        29.29
    17,18:     32.49
    19,20:     36.29
    21,22:     40.99
    23,24:     41.99
    25-30:     58.99
    31-38:     70.99
    39-48:     94.99
    50-60:    129.99
    62-72:    168.99
""")
FLANGE_RING_HEAVY = _bands("""     # 3/16 in thick
    6,8:       14.19
    10:        16.29
""")

# Two piece clamp bands, zinc plated through 24 in. The catalog's own order — it is
# not monotonic, and 8 in really is cheaper than 7 in.
CLAMP_BAND = _bands("""
    3,4,5,6:   10.99
    7:         14.99
    8:         10.99
    9:         14.99
    10:        12.99
    11,12:     19.99
    13:        25.99
    14:        27.99
    16:        37.90
    18:        49.90
    20:        54.90
    24:        66.90
    15,17,19,21,22,23:  66.90      # primed gray
""")

# Page 45: hanger strap for duct.
HANGER_STRAP = _bands("""
    4,5,6,8:    8.69
    10,12:     14.29
    14,16,18:  24.59
    20,22,24:  32.09
    26-48:     74.29
""")

# Page 44: air blast gates, and the 5/8 in tall slim blast gate.
BLAST_GATE = _bands("""
    3,4,5,6:   89.00
    7,8:      109.00
    9,10:     119.00
    11,12:    149.00
    13,14:    159.00
    16,18:    219.00
    20,22,24: 349.00
""")
SLIM_BLAST_GATE = _bands("""
    4,6,8:     89.00
    10,12:    159.00
    14,16:    169.00
    18:       189.00
    20:       209.00
    24:       239.00
""")

# Page 44: round damper — controls volume, not a shut-off. Same price flanged or not.
#                          14 Ga    12 Ga    10 Ga
ROUND_DAMPER = _bands("""
    4,5,6,7,8:   239.00   259.00   299.00
    10,12:       259.00   299.00   329.00
    14,16,18:    349.00   389.00   429.00
    20,22,24:    469.00   519.00   579.00
""")

# Page 44: compression coupling, 12 gauge, two piece, rubber seal.
COMPRESSION_COUPLING = _bands("""
    6:         59.00
    7,8,9:     89.00
    10,11:    109.00
    12,13:    129.00
    14,15,16: 159.00
    17-20:    249.00
    21-24:    379.00
""")

# Page 44/45: branch fittings.   14 Ga  12 Ga  10 Ga
BRANCH_45_OFFSET = _bands("""
    6:   149.00  159.00  199.00
    8:   149.00  159.00  199.00
    10:  149.00  189.00  209.00
    12:  199.00  209.00  249.00
    14:  239.00  259.00  319.00
    16:  279.00  329.00  379.00
    18:  339.00  379.00  449.00
    20:  429.00  479.00  549.00
    24:  549.00  609.00  709.00
""")
BRANCH_45_Y = _bands("""
    6:   129.00  149.00  169.00
    8:   129.00  149.00  169.00
    10:  149.00  159.00  199.00
    12:  189.00  199.00  239.00
    14:  219.00  249.00  299.00
    16:  259.00  299.00  369.00
    18:  329.00  349.00  419.00
    20:  409.00  469.00  549.00
    24:  519.00  579.00  709.00
""")
BRANCH_45_THREE_WAY = _bands("""
    6:   209.00  219.00  259.00
    8:   219.00  239.00  279.00
    10:  239.00  249.00  299.00
    12:  259.00  289.00  349.00
    14:  329.00  349.00  419.00
    16:  379.00  419.00  509.00
    18:  429.00  479.00  579.00
    20:  519.00  579.00  709.00
    24:  689.00  779.00  929.00
""")
BRANCH_90_T = _bands("""
    6:   169.00  189.00  219.00
    8:   209.00  219.00  249.00
    10:  209.00  239.00  259.00
    12:  259.00  289.00  319.00
    14:  259.00  299.00  329.00
    16:  319.00  339.00  389.00
    18:  369.00  419.00  459.00
    20:  429.00  479.00  539.00
    24:  509.00  579.00  639.00
""")

# Page 45: what goes on the end of a fan discharge that vents to atmosphere.
HAT_RAIN_HOOD = _bands("""
    6,8,10,12:      289.00
    14,16,18,20:    449.00
    22,24,26,28:    599.00
    30,32,34,36:    809.00
""")
SHIELDED_RAIN_HOOD = _bands("""
    6,8,10,12:      319.00
    14,16,18,20:    539.00
    22,24,26,28:    709.00
    30,32,34,36:   1019.00
""")
BIRD_SCREEN_ROUND = _bands("""
    6:   119.00
    8:   119.00
    10:  129.00
    12:  149.00
    14:  169.00
    16:  189.00
    18:  209.00
    20:  279.00
    24:  339.00
    30:  469.00
    36:  609.00
""")

# Page 45: removable back sweep elbows, 10 gauge with a 10 gauge removable back —
# the abrasion-service elbow, for a mill or cyclone discharge that wears one out.
#   dia  CL      90        60        45        30
SWEEP_ELBOW = _table("""
    3   36    779.00    719.00    649.00    589.00
    4   36    809.00    729.00    669.00    609.00
    5   36    859.00    779.00    679.00    639.00
    6   36    869.00    809.00    719.00    649.00
    8   48   1109.00    999.00    869.00    839.00
   10   48   1549.00   1369.00   1249.00   1199.00
   12   48   1639.00   1499.00   1419.00   1319.00
   14   48   1889.00   1709.00   1509.00   1459.00
   16   48   2399.00   2199.00   2009.00   1949.00
   18   48   3109.00   2799.00   2489.00   2429.00
   20   48   3569.00   3199.00   2819.00   2669.00
   24   48   4089.00   3669.00   3269.00   3059.00
""", ["cl", "90", "60", "45", "30"])

# --- page 3: spouting, plain end, per foot --------------------------------------
# What the catalog sends you to for duct under 9 in. Plain end, so it needs flange
# rings or clamp bands, and it is bare steel until primed.
#   dia     14 Ga    12 Ga    10 Ga     7 Ga     1/4"
SPOUTING_PER_FT = _table("""
    3        5.79        -     7.69        -        -
    4        7.19     8.89     9.79        -        -
    5           -    10.89    11.69        -        -
    6        7.49    11.49    13.39    15.99        -
    7           -    15.69    17.09        -        -
    8       12.89    15.29    17.59    24.19    32.99
   10           -    17.89    21.89    29.39    36.49
   12           -    19.49    27.39    37.69    38.39
   14           -    32.49    38.89    44.89    45.89
   16           -    37.89    45.89    49.89    55.89
   18           -        -        -        -    74.89
   20           -        -        -        -    80.89
   24           -        -        -        -   109.89
""", GAUGES)

# Shop coat gray primer only, per foot, on top of the spouting price.
PRIMING_PER_FT = _bands("""
    4,6,8,10:    1.25
    12,14,16:    1.75
    18,20,24:    2.25
""")

# Page 3 prints the same spouting in galvanized and in 304 stainless, so the cost
# of a material change is Nolin's own, measured where the three tables overlap —
# not a number anybody guessed at. MATERIAL_ADDER below is built from these.
GALVANIZED_PER_FT = _table("""
    4        7.39        -        -        -        -
    5        8.49        -        -        -        -
    6       10.09    11.69    14.59        -        -
    7           -    15.99        -        -        -
    8       13.29    16.19    19.99    27.79        -
   10           -    21.49    26.49    34.09        -
   12           -    22.89    31.89    49.89    69.89
   14           -        -    45.89    58.89    76.89
   16           -        -        -    66.89    90.89
""", GAUGES)

# * 16 in 12 ga and 16 in 7 ga are 10 ft lengths only.
STAINLESS_304_PER_FT = _table("""
    3       20.69    25.39    28.89        -        -
    4       28.19    31.29    37.39        -        -
    5           -        -    45.89        -        -
    6           -    41.90    52.90        -        -
    8           -    56.90    69.90    80.90        -
   10           -    68.90    88.90   103.90        -
   12           -    82.90   103.90   116.90        -
   14           -   109.90   123.90   139.90        -
   16           -   111.90   176.90   188.90        -
""", GAUGES)


def _ratios(table):
    """Every cell where this material and carbon steel print the same size and gauge."""
    out = []
    for dia, row in table.items():
        base = SPOUTING_PER_FT.get(dia, {})
        for gauge, price in row.items():
            if gauge in base and base[gauge]:
                out.append(price / base[gauge])
    return sorted(out)


def _adder(name, table, note):
    r = _ratios(table)
    return {"factor": round(statistics.median(r), 3),
            "low": round(r[0], 3), "high": round(r[-1], 3),
            "samples": len(r), "material": name, "note": note,
            "source": f"{SOURCE} p. 3, {name} vs carbon steel spouting",
            "date": CATALOG_DATE}


# What a material change costs, as a multiplier on the carbon steel price.
#
# The catalog prints ductwork, elbows and fittings in primed gray carbon steel
# only. Spouting is the one product it prints in all three materials, so these
# factors are measured there and carried across. That makes a galvanized or
# stainless duct line a BUDGETARY number off a real ratio, not a catalog price —
# `stick()` and `elbow()` say so, and the quote carries it as an open item.
# For a firm price on a stainless run, Nolin quotes it.
MATERIAL_ADDER = {
    "carbon": {"factor": 1.0, "low": 1.0, "high": 1.0, "samples": 0,
               "material": "carbon steel", "note": "the catalog price as printed",
               "source": f"{SOURCE} p. 43", "date": CATALOG_DATE},
    "galvanized": _adder("galvanized", GALVANIZED_PER_FT,
                         "galvanized runs close to carbon on light gauge and pulls "
                         "away as the gauge gets heavy"),
    "stainless": _adder("304 stainless", STAINLESS_304_PER_FT,
                        "304 is a different order of cost — spread this wide means "
                        "the factor is a budget figure, not a quote"),
}
MATERIALS = [("carbon", "Primed gray carbon steel — the catalog price"),
             ("galvanized", "Galvanized"),
             ("stainless", "304 stainless")]


def _nearest(table, size):
    """The catalog row that covers a size, or the next one up that exists."""
    if size in table:
        return size, table[size]
    bigger = [s for s in table if s >= size]
    if bigger:
        s = min(bigger)
        return s, table[s]
    return None, None


def stick(diameter_in, gauge="14"):
    """(price, actual_diameter, actual_gauge) for one 10 ft length, or None.

    Falls up to the next size and the next heavier gauge the catalog actually
    prints, and says which it landed on — a 25 in duct is not in the book, and
    quoting the 26 in is what Nolin would do.
    """
    dia, row = _nearest(DUCT_STICK, int(diameter_in))
    if not row:
        return None
    for g in GAUGES[GAUGE_ORDER.get(gauge, 0):]:
        if g in row:
            return row[g], dia, g
    return None


def elbow(diameter_in, angle="90", gauge="14"):
    """(price, actual_diameter, actual_gauge, centerline_in) for one elbow."""
    dia, row = _nearest(ELBOW, int(diameter_in))
    if not row:
        return None
    prices = row.get(str(angle)) or {}
    for g in GAUGES[GAUGE_ORDER.get(gauge, 0):]:
        if g in prices:
            return prices[g], dia, g, ELBOW_CENTERLINE[dia]
    return None


def reducer(large_in, small_in, gauge="14"):
    """(price, (large, small), gauge) for the closest printed reducer, or None."""
    large, small = int(large_in), int(small_in)
    exact = REDUCER.get((large, small))
    if exact is None:
        # the nearest printed reducer that is at least this big on both ends
        fits = [(l, s) for (l, s) in REDUCER
                if l >= large and s >= small and l > s]
        if not fits:
            return None
        large, small = min(fits, key=lambda p: (p[0] - large) + (p[1] - small))
        exact = REDUCER[(large, small)]
    for g in ("14", "12", "10")[list(("14", "12", "10")).index(gauge)
                                if gauge in ("14", "12", "10") else 0:]:
        if g in exact:
            return exact[g], (large, small), g
    return None


def transition(square_in, round_in, gauge="14"):
    """(price, (square, round), gauge) for a square or rectangular to round
    transition. A rectangle takes its larger side, which is what Nolin prices."""
    sq, rd = int(square_in), int(round_in)
    exact = SQUARE_TO_ROUND.get((sq, rd))
    if exact is None:
        fits = [(a, b) for (a, b) in SQUARE_TO_ROUND if a >= sq and b >= rd]
        if not fits:
            return None
        sq, rd = min(fits, key=lambda p: (p[0] - sq) + (p[1] - rd))
        exact = SQUARE_TO_ROUND[(sq, rd)]
    order = ("14", "12", "10")
    start = order.index(gauge) if gauge in order else 0
    for g in order[start:]:
        if g in exact:
            return exact[g], (sq, rd), g
    return None


def band(table, size, column=0):
    """One price out of a banded table, falling up to the next size printed."""
    _size, row = _nearest(table, int(size))
    if not row:
        return None
    return row[column] if column < len(row) else row[-1]
