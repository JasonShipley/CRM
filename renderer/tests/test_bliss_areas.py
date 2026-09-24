#!/usr/bin/env python3
"""Every MCE mill's screen area against the Bliss price book it is sold from.

MCE's XM line is built on the Bliss grinding design and each XM model is priced
at its Bliss counterpart's base price — that price is the link, and it is already
in the calculator (MILL_PRICING[...]["bliss"]). So the screen areas have to agree
too, and this test holds them to it.

Source: "MCE_Bliss_Price_Book_Template_Style (2).xlsx" on MCE's Drive, sheets
E-19HM / E-22HM / E-38HM / E-44HM, Jan'16 revised 2017.

    cd renderer && python3 tests/test_bliss_areas.py
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from calculators._data import MCE_XM_MILLS, MILL_PRICING  # noqa: E402

# Bliss model -> (screen size, screen area, base price). Base price is what ties
# each row to an MCE model; the area is what we are checking.
BLISS_PRICE_BOOK = {
    "E-1906":  ('6.5" x 24"',   312,  8800),
    "E-1912":  ('12" x 24"',    576, 10851),
    "E-1915":  ('15" x 24"',    720, 14560),
    "E-1920":  ('20" x 24"',    960, 17298),
    "E-1924":  ('24" x 24"',   1152, 18299),
    "E-22095": ('9.5" x 29"',   551, 10986),
    "E-22115": ('11.5" x 29"',  667, 13061),
    "E-2215":  ('15" x 29"',    870, 16216),
    "E-2220":  ('20" x 29"',   1160, 19925),
    "E-2224":  ('24" x 29"',   1392, 22204),
    "E-2230":  ('30" x 29"',   1740, 24461),
    "E-2236":  ('36" x 29"',   2088, 27403),
    "E-38095": ('9.5" x 50"',   950, 18390),
    "E-38115": ('11.5" x 50"', 1150, 20804),
    "E-3815":  ('15" x 50"',   1500, 22690),
    "E-3820":  ('20" x 50"',   2000, 25009),
    "E-3824":  ('24" x 50"',   2400, 28848),
    "E-3830":  ('30" x 50"',   3000, 32692),
    "E-3836":  ('36" x 50"',   3600, 39691),
    "ED-3840": ('20" x 50"',   4000, 44335),
    "ED-3848": ('24" x 50"',   4800, 50712),
    "ED-3860": ('30" x 50"',   6000, 57821),
    "E-44095": ('9.5" x 60"',  1140, 21803),
    "E-44115": ('11.5" x 60"', 1380, 23958),
    "E-4415":  ('15" x 60"',   1800, 26104),
    "E-4420":  ('20" x 60"',   2400, 30908),
    "E-4424":  ('24" x 60"',   2880, 33657),
    "E-4430":  ('30" x 60"',   3600, 37749),
    "E-4436":  ('36" x 60"',   4320, 42116),
    "ED-4440": ('20" x 60"',   4800, 51555),
    "ED-4448": ('24" x 60"',   5760, 58181),
    "ED-4460": ('30" x 60"',   7200, 65078),
}
BY_PRICE = {price: (model, size, area)
            for model, (size, area, price) in BLISS_PRICE_BOOK.items()}


def main():
    fails = []
    for mill in MCE_XM_MILLS:
        price = (MILL_PRICING.get(mill["model"]) or {}).get("bliss")
        hit = BY_PRICE.get(price)
        if not hit:
            fails.append(f'{mill["model"]}: base price {price} is not in the price book')
            continue
        bliss_model, bliss_size, bliss_area = hit
        if mill["area"] != bliss_area:
            fails.append(
                f'{mill["model"]} {mill["screenSize"]} = {mill["area"]:,} in², but '
                f'{bliss_model} {bliss_size} = {bliss_area:,} in² '
                f'(delta {mill["area"] - bliss_area:+,})')
        elif mill["screenSize"].replace(" ", "") != bliss_size.replace(" ", ""):
            fails.append(
                f'{mill["model"]} area matches {bliss_model} but the screen reads '
                f'{mill["screenSize"]} against {bliss_size}')
    if fails:
        print(f"{len(fails)} mill(s) disagree with the Bliss price book:\n")
        for f in fails:
            print("  " + f)
        return 1
    print(f"OK — all {len(MCE_XM_MILLS)} mills match the Bliss price book "
          "on screen size and area.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
