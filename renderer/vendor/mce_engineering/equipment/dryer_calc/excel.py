"""Excel backbone: the rotary dryer calculator as a live, formula-driven, MCE-branded workbook.

    from mce_engineering.equipment.dryer_calc.excel import build_workbook
    build_workbook(request_dict, "out.xlsx", record_index="RD-000012")

Sheets
  Mass-Energy Balance  customer-facing process diagram (the legacy FLOW sheet, done right)
  Inputs               every input: default, entry (override), value used, unit, sane range, check, source
  Calc                 the calculation, one named line at a time (mass balance to handoffs)
  Gas                  species tables: combustion, gas streams, flame temperature
  Drum                 standard drum candidates and checks (three shell-loss passes)
  Data                 material and fuel presets, constants, property coefficients
  Notes                method, reference state, sources, open assumptions

Every result is an Excel formula on named cells; nothing is pasted from Python. The Python
engine (rotary.py) is the reference: tests/dryer_calc/test_excel.py recalculates this workbook
in LibreOffice and checks it against the engine. The gas side at a fixed inlet temperature is
linear in fuel and dilution air, so the workbook solves it in closed form (Cramer's rule); to
fix exhaust ACFM or gas flow instead, use Goal Seek on the inlet temperature.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as CL
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from . import emissions as EM
from . import properties as P
from .combustion import GAS_STOICH, HF298, HFG25_KJ_KMOL
from .presets import FUELS, MATERIALS, NEMA_HP, STANDARD_DRUM_DIAMETERS_FT, STANDARD_DRUM_LENGTHS_FT
from .resolve import resolve
from .rotary import CALC_VERSION, FIRE_RISK_INLET_F
from .schema import DryerRequest
from .units import IN_WC_TO_PSI, KJ_PER_KG_TO_BTU_PER_LB, PSI_TO_KPA

ASSETS = Path(__file__).resolve().parent / "assets"
WB_VERSION = "MCE rotary dryer workbook 1.0"

# MCE brand (Brand Guidelines v1.0). Oswald/Inter are not on every PC: Arial Narrow / Arial substitute.
ORANGE, BLACK, STEEL, WHITE, SILVER = "FF6602", "000000", "575D5E", "FFFFFF", "C8C7C7"
FIELD, HEADER, PANEL, MUTED = "F1F1F1", "E4E4E4", "F5F5F5", "9A9A9A"
HEAD_FONT, BODY_FONT = "Arial Narrow", "Arial"
INPUT_BLUE = "0000FF"


def _font(size=9, bold=False, color="000000", head=False, italic=False):
    return Font(name=HEAD_FONT if head else BODY_FONT, size=size, bold=bold, color=color, italic=italic)


def _fill(c):
    return PatternFill("solid", fgColor=c)


THIN = Side(style="thin", color=SILVER)
BOX = Side(style="thin", color=STEEL)
GRID = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

FUEL_SHORT = {"natural_gas": "Natural Gas", "propane": "Propane", "no2_oil": "#2 Fuel Oil",
              "biomass": "Biomass Fuel"}
GAS_COMPONENTS = ["CH4", "C2H6", "C3H8", "C4H10", "H2", "CO", "CO2", "N2", "O2", "H2S"]
ULT = ["C", "H", "O", "N", "S", "ash"]
SPECIES = ["N2", "O2", "Ar", "CO2", "H2O", "SO2"]


class Book:
    def __init__(self):
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.names: dict[str, str] = {}

    def sheet(self, title):
        ws = self.wb.create_sheet(title)
        ws.sheet_view.showGridLines = False
        return ws

    def name(self, nm: str, ws, ref: str):
        assert nm not in self.names, nm
        sheet = ws.title
        q = f"'{sheet}'" if " " in sheet or "-" in sheet else sheet
        target = f"{q}!{ref}"
        self.names[nm] = target
        self.wb.defined_names[nm] = DefinedName(nm, attr_text=target)


def _abs(col: int, row: int) -> str:
    return f"${CL(col)}${row}"


# --------------------------------------------------------------------------------------- Data
def build_data(bk: Book):
    ws = bk.sheet("Data")
    ws.column_dimensions["A"].width = 2
    r = 1
    ws.cell(r, 2, "Data: presets, constants and property coefficients").font = _font(13, True, head=True)
    r = 3
    # constants
    consts = [
        ("k_kJ2BTU", "kJ/kg to BTU/lb (also kJ/kmol to BTU/lbmol)", KJ_PER_KG_TO_BTU_PER_LB, "", "IT BTU, exact"),
        ("k_T0K", "Reference temperature", 273.15, "K", "32 F reference state"),
        ("k_HFG32", "hfg at the triple point", P.HFG_TRIPLE_KJ_KG, "kJ/kg", "IAPWS-95"),
        ("k_HFG77", "hfg at 77 F (HHV/LHV conversion)", 2442.3, "kJ/kg", "IAPWS-95; ISO 18125 convention"),
        ("k_R", "Gas constant", 10.73159, "psia ft3/lbmol R", ""),
        ("k_Tstd", "Standard temperature (70 F)", 529.67, "R", "SCFM basis 70 F, 29.92 in. Hg"),
        ("k_Pstd", "Standard pressure", 14.696, "psia", ""),
        ("k_g", "Gravity", 32.174, "ft/s2", ""),
        ("k_AMCA", "AMCA standard air density", 0.075, "lb/ft3", "AMCA 210"),
        ("k_INWC", "in. w.c. to psi", IN_WC_TO_PSI, "psi", "60 F water (ASHRAE)"),
        ("k_PSIKPA", "psi to kPa", PSI_TO_KPA, "kPa", ""),
        ("k_FireT", "Fire-risk inlet limit", FIRE_RISK_INLET_F, "F", "MCE (Jason 2026-11-07)"),
    ]
    ws.cell(r, 2, "Constants").font = _font(10, True, head=True)
    r += 1
    for nm, lab, val, unit, src in consts:
        ws.cell(r, 2, lab)
        ws.cell(r, 3, val)
        ws.cell(r, 4, unit)
        ws.cell(r, 5, src).font = _font(8, color=MUTED)
        bk.name(nm, ws, _abs(3, r))
        r += 1
    ws.cell(r, 2, "Standard molar volume")
    ws.cell(r, 3, "=k_R*k_Tstd/k_Pstd")
    ws.cell(r, 4, "ft3/lbmol")
    bk.name("k_StdVol", ws, _abs(3, r))
    r += 1
    ws.cell(r, 2, "hfg at 32 F")
    ws.cell(r, 3, "=k_HFG32*k_kJ2BTU")
    ws.cell(r, 4, "BTU/lb")
    bk.name("k_HFG32B", ws, _abs(3, r))
    r += 1
    ws.cell(r, 2, "hfg at 77 F")
    ws.cell(r, 3, "=k_HFG77*k_kJ2BTU")
    ws.cell(r, 4, "BTU/lb")
    bk.name("k_HFG77B", ws, _abs(3, r))
    r += 2
    # molecular weights
    ws.cell(r, 2, "Molecular weights (IUPAC 2013)").font = _font(10, True, head=True)
    r += 1
    for el in ["C", "H", "H2", "O", "O2", "N2", "S", "H2O", "Ar", "CO2", "SO2"]:
        ws.cell(r, 2, el)
        ws.cell(r, 3, P.MW[el])
        ws.cell(r, 4, "lb/lbmol")
        bk.name(f"mw_{el}", ws, _abs(3, r))
        r += 1
    r += 1
    # IF97 region 4
    ws.cell(r, 2, "IAPWS-IF97 Region 4 coefficients n1 to n10").font = _font(10, True, head=True)
    r += 1
    for i, n in enumerate(P._N, 1):
        ws.cell(r, 2, f"n{i}")
        ws.cell(r, 3, n)
        bk.name(f"k_if{i}", ws, _abs(3, r))
        r += 1
    r += 1
    ws.cell(r, 2, "Saturated liquid h (kJ/kg) = a t^4 + b t^3 + c t^2 + d t (t in C), fit to IAPWS-95").font = \
        _font(10, True, head=True)
    r += 1
    for i, c in enumerate(P._HF_FIT[:4]):
        ws.cell(r, 2, "abcd"[i])
        ws.cell(r, 3, c)
        bk.name(f"k_hf{'abcd'[i]}", ws, _abs(3, r))
        r += 1
    r += 1
    # NEMA motor sizes
    ws.cell(r, 2, "NEMA MG-1 motor HP").font = _font(10, True, head=True)
    r += 1
    r0 = r
    for hp in NEMA_HP:
        ws.cell(r, 2, hp)
        r += 1
    bk.name("t_NEMA", ws, f"$B${r0}:$B${r - 1}")
    r += 1
    # pick lists
    lists = {"l_TUnit": ["lb/hr", "TPH"], "l_TBasis": ["wet_feed", "dry_solids", "product"],
             "l_HVbasis": ["net_as_fired", "net_dry", "gross_dry", "gross_as_fired"],
             "l_HVsource": ["entered", "analysis"], "l_Shell": ["UA", "percent"], "l_YesNo": ["Yes", "No"],
             "l_SPbasis": ["standard_air", "operating"]}
    ws.cell(r, 2, "Pick lists").font = _font(10, True, head=True)
    r += 1
    for nm, items in lists.items():
        ws.cell(r, 2, nm)
        for j, it in enumerate(items):
            ws.cell(r, 3 + j, it)
        bk.name(nm, ws, f"${CL(3)}${r}:${CL(2 + len(items))}${r}")
        r += 1
    r += 1

    # fuels table
    ws.cell(r, 2, "Fuels (ultimate analysis dry mass %, gas composition mol %)").font = _font(10, True, head=True)
    r += 1
    fcols = ["label", "kind", "heating_value", "heating_value_basis", "moisture_wb", "density", "excess_air_pct",
             "furnace_efficiency", "cp"] + [f"u_{u}" for u in ULT] + [f"g_{g}" for g in GAS_COMPONENTS] + ["key"]
    for j, c in enumerate(fcols):
        ws.cell(r, 2 + j, c).font = _font(8, True)
    r += 1
    r0 = r
    for key, fu in FUELS.items():
        ult = fu.get("ultimate", {}).get("value", {}) or {}
        comp = fu.get("composition", {}).get("value", {}) or {}
        vals = [fu["label"], fu["kind"], fu["heating_value"]["value"], fu["heating_value_basis"]["value"],
                fu["moisture_wb"]["value"], fu["density"]["value"], fu["excess_air_pct"]["value"],
                fu["furnace_efficiency"]["value"], fu["cp"]["value"]] + [ult.get(u, 0.0) for u in ULT] + \
            [comp.get(g, 0.0) for g in GAS_COMPONENTS] + [key]
        for j, v in enumerate(vals):
            ws.cell(r, 2 + j, v)
        r += 1
    for j, c in enumerate(fcols):
        bk.name(f"fu_{c}", ws, f"${CL(2 + j)}${r0}:${CL(2 + j)}${r - 1}")
    sc = 2 + len(fcols)
    ws.cell(r0 - 1, sc, "short").font = _font(8, True)
    for i, key in enumerate(FUELS):
        ws.cell(r0 + i, sc, FUEL_SHORT[key])
    bk.name("fu_short", ws, f"${CL(sc)}${r0}:${CL(sc)}${r - 1}")
    r += 1
    # gas components
    ws.cell(r, 2, "Gas fuel components (heats of formation at 25 C, Cengel Table A-26 / NIST-JANAF)").font = \
        _font(10, True, head=True)
    r += 1
    hdr = ["component", "MW", "O2 demand", "CO2 formed", "H2O formed", "SO2 formed", "Hf kJ/kmol", "LHV kJ/kmol"]
    for j, c in enumerate(hdr):
        ws.cell(r, 2 + j, c).font = _font(8, True)
    r += 1
    hf_rows = {}
    r0 = r
    for g in GAS_COMPONENTS:
        o2, c, h, s = GAS_STOICH[g]
        ws.cell(r, 2, g)
        ws.cell(r, 3, P.MW[g] if g in P.MW else {"N2": P.MW["N2"], "O2": P.MW["O2"], "CO2": P.MW["CO2"]}[g])
        ws.cell(r, 4, o2)
        ws.cell(r, 5, c)
        ws.cell(r, 6, h)
        ws.cell(r, 7, s)
        ws.cell(r, 8, HF298[g])
        hf_rows[g] = r
        r += 1
    # LHV per kmol = Hf - c Hf(CO2) - h Hf(H2O,g) - s Hf(SO2); inerts zero
    ws.cell(r, 2, "Hf CO2 / H2O(g) / SO2 / hfg25")
    ws.cell(r, 3, HF298["CO2"])
    ws.cell(r, 4, HF298["H2O"])
    ws.cell(r, 5, HF298["SO2"])
    ws.cell(r, 6, HFG25_KJ_KMOL)
    hfr = r
    for g in GAS_COMPONENTS:
        rr = hf_rows[g]
        if g in ("CO2", "N2", "O2"):
            ws.cell(rr, 9, 0)
        else:
            ws.cell(rr, 9, f"=H{rr}-E{rr}*$C${hfr}-F{rr}*$D${hfr}-G{rr}*$E${hfr}")
    for j, c in enumerate(["comp", "MW", "O2", "CO2", "H2O", "SO2", "HF", "LHV"]):
        bk.name(f"gc_{c}", ws, f"${CL(2 + j)}${r0}:${CL(2 + j)}${r0 + len(GAS_COMPONENTS) - 1}")
    bk.name("k_HFG25", ws, f"$F${hfr}")
    for col in range(2, 34):
        ws.column_dimensions[CL(col)].width = 12
    ws.column_dimensions["B"].width = 34
    for row in ws.iter_rows():
        for c in row:
            if c.font is None or c.font.name != HEAD_FONT:
                c.font = Font(name=BODY_FONT, size=c.font.size if c.font and c.font.size else 9,
                              bold=c.font.bold if c.font else False, color=c.font.color if c.font else None)
    return ws


# --------------------------------------------------------------------------------------- Products
PCOLS = ["label", "key", "is_wood", "protein", "fat", "carbohydrate", "fiber", "ash", "cp", "bulk_density_dry",
         "particle_size_in", "particle_density", "sphericity", "ver_min", "ver_max", "residence_target_min",
         "max_product_temp_F", "product_temp_F", "mc_in", "mc_out", "heat_sensitivity", "fire_risk", "sticky", "source"]
PHEAD = {"label": "Product", "key": "key", "is_wood": "Wood", "protein": "Protein % dry", "fat": "Fat % dry",
         "carbohydrate": "Carbohydrate % dry", "fiber": "Fiber % dry", "ash": "Ash % dry",
         "cp": "Cp dry solids BTU/lb-F", "bulk_density_dry": "Bulk density dry lb/ft3",
         "particle_size_in": "Particle dia in", "particle_density": "Particle density lb/ft3",
         "sphericity": "Sphericity", "ver_min": "VER low", "ver_max": "VER high",
         "residence_target_min": "Residence min", "max_product_temp_F": "Max product F",
         "product_temp_F": "Discharge F", "mc_in": "Typical MC in % wb", "mc_out": "Typical MC out % wb",
         "heat_sensitivity": "Heat sensitivity", "fire_risk": "Fire risk", "sticky": "Sticky", "source": "Sources"}


def build_products(bk: Book):
    from .presets import CHOI_OKOS, T_CP_MEAN_C
    ws = bk.sheet("Products")
    ws.column_dimensions["A"].width = 2
    ws.cell(1, 2, "PRODUCT LIBRARY").font = _font(14, True, head=True)
    ws.cell(2, 2, "Picked on the Inputs sheet; every value can be overridden there. Cp is for the DRY solids (water is "
                  "counted separately): wood by the USDA Wood Handbook equation, other products by Choi & Okos (1986) "
                  "from the dry composition (ASHRAE Handbook Refrigeration Ch.19), at 130 F.").font = \
        _font(8, italic=True, color=STEEL)
    r = 4
    ws.cell(r, 2, "Cp evaluation temperature").font = _font(9)
    ws.cell(r, 3, T_CP_MEAN_C)
    ws.cell(r, 4, "C (130 F)")
    bk.name("k_TcpC", ws, _abs(3, r))
    r += 1
    ws.cell(r, 2, "kJ/kg-K to BTU/lb-F").font = _font(9)
    ws.cell(r, 3, 0.238845897)
    bk.name("k_CpConv", ws, _abs(3, r))
    r += 2
    ws.cell(r, 2, "Choi & Okos component cp = a + b t + c t^2 (kJ/kg-K, t in C)").font = _font(9, True)
    r += 1
    for j, h in enumerate(["component", "a", "b", "c"]):
        ws.cell(r, 2 + j, h).font = _font(8, True)
    r += 1
    for comp, (a, b, c) in CHOI_OKOS.items():
        ws.cell(r, 2, comp)
        for j, val in enumerate((a, b, c)):
            ws.cell(r, 3 + j, val)
            bk.name(f"co_{comp[:4]}_{'abc'[j]}", ws, _abs(3 + j, r))
        r += 1
    r += 1
    for j, c in enumerate(PCOLS):
        cell = ws.cell(r, 2 + j, PHEAD[c])
        cell.font = _font(8, True, WHITE)
        cell.fill = _fill(BLACK)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r].height = 36
    r += 1
    r0 = r
    C = {c: 2 + j for j, c in enumerate(PCOLS)}
    for key, m in MATERIALS.items():
        comp = (m.get("composition") or {}).get("value") or {}
        vals = {"label": m["label"], "key": key, "is_wood": "Yes" if m["is_wood"] else "No",
                "bulk_density_dry": m["bulk_density_dry"]["value"], "particle_size_in": m["particle_size_in"]["value"],
                "particle_density": m["particle_density"]["value"], "sphericity": m["sphericity"]["value"],
                "ver_min": m["ver_range"]["value"][0], "ver_max": m["ver_range"]["value"][1],
                "residence_target_min": m["residence_target_min"]["value"],
                "max_product_temp_F": m["max_product_temp_F"]["value"], "product_temp_F": m["product_temp_F"]["value"],
                "mc_in": m["mc_in"]["value"], "mc_out": m["mc_out"]["value"],
                "heat_sensitivity": m["heat_sensitivity"]["value"], "fire_risk": m["fire_risk"]["value"],
                "sticky": "Yes" if m["sticky"]["value"] else "No"}
        for k in ("protein", "fat", "carbohydrate", "fiber", "ash"):
            vals[k] = comp.get(k, 0.0)
        src = [f"cp: {m['cp']['source']}"]
        if comp:
            src.append(f"composition: {m['composition']['source']}")
        src.append("Other properties: MCE assumption, confirm unless noted in presets.py.")
        vals["source"] = " ".join(src)
        for k, val in vals.items():
            ws.cell(r, C[k], val)
        cc = {k: f"{CL(C[k])}{r}" for k in ("protein", "fat", "carbohydrate", "fiber", "ash", "is_wood")}
        t = "k_TcpC"
        terms = "+".join(f"{cc[k]}*(co_{k[:4]}_a+co_{k[:4]}_b*{t}+co_{k[:4]}_c*{t}^2)"
                         for k in ("protein", "fat", "carbohydrate", "fiber", "ash"))
        tot = f"({cc['protein']}+{cc['fat']}+{cc['carbohydrate']}+{cc['fiber']}+{cc['ash']})"
        ws.cell(r, C["cp"], f'=IF(OR({cc["is_wood"]}="Yes",{tot}=0),(0.1031+0.003867*({t}+273.15))*k_CpConv,'
                            f'({terms})/{tot}*k_CpConv)').number_format = "0.0000"
        r += 1
    for c in PCOLS:
        bk.name(f"m_{c}", ws, f"${CL(C[c])}${r0}:${CL(C[c])}${r - 1}")
    for c in range(3, 2 + len(PCOLS)):
        ws.column_dimensions[CL(c)].width = 10
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions[CL(C["source"])].width = 110
    for row in ws.iter_rows(min_row=r0, max_row=r - 1):
        for cell in row:
            cell.font = _font(8)
    ws.freeze_panes = ws.cell(r0, 3)
    return ws


# --------------------------------------------------------------------------------------- Inputs
class InputWriter:
    """Default | Entry (override) | Used | Unit | Low | High | Check | Source."""

    def __init__(self, bk: Book, ws, entries: dict[str, Any]):
        self.bk, self.ws, self.r, self.entries = bk, ws, 6, entries
        self.dv: dict[str, DataValidation] = {}

    def section(self, title):
        self.r += 1
        ws = self.ws
        for c in range(2, 11):
            ws.cell(self.r, c).fill = _fill(STEEL)
        ws.cell(self.r, 2, title.upper()).font = _font(10, True, WHITE, head=True)
        ws.cell(self.r, 1).fill = _fill(ORANGE)
        self.r += 1

    def add(self, nm, label, default, unit="", lo=None, hi=None, src="", pick=None, text=False):
        ws, r = self.ws, self.r
        ws.cell(r, 2, label).font = _font(9)
        c = ws.cell(r, 3, default)
        c.font = _font(9, color=STEEL)
        e = ws.cell(r, 4)
        if nm in self.entries and self.entries[nm] is not None:
            e.value = self.entries[nm]
        e.font = _font(9, True, INPUT_BLUE)
        e.fill = _fill("FFF4E5")
        e.border = Border(left=BOX, right=BOX, top=BOX, bottom=BOX)
        ws.cell(r, 5, f'=IF(D{r}="",C{r}&"",D{r})' if text else f'=IF(D{r}="",C{r},D{r})').font = _font(9, True)
        ws.cell(r, 6, unit).font = _font(8, color=STEEL)
        if lo is not None:
            ws.cell(r, 7, lo).font = _font(8, color=MUTED)
        if hi is not None:
            ws.cell(r, 8, hi).font = _font(8, color=MUTED)
        if lo is not None and hi is not None and not text:
            ws.cell(r, 9, f'=IF(OR(E{r}<G{r},E{r}>H{r}),"OUT OF RANGE",IF(D{r}<>"","override",""))')
        else:
            ws.cell(r, 9, f'=IF(D{r}<>"","override","")')
        ws.cell(r, 9).font = _font(8, True, ORANGE)
        sc = ws.cell(r, 10, src)
        sc.data_type = "s"
        sc.font = _font(8, color=MUTED)
        for col in (5,):
            ws.cell(r, col).fill = _fill(FIELD)
        if pick:
            if pick not in self.dv:
                ref = self.bk.names[pick] if not pick.startswith("=") else pick[1:]
                self.dv[pick] = DataValidation(type="list", formula1=f"={ref}" if not pick.startswith("=") else pick,
                                               allow_blank=True)
                ws.add_data_validation(self.dv[pick])
            self.dv[pick].add(f"D{r}")
        self.bk.name(nm, ws, _abs(5, r))
        self.r += 1
        return r


def build_inputs(bk: Book, entries: dict[str, Any], job: dict[str, str]):
    ws = bk.sheet("Inputs")
    widths = {"A": 1.5, "B": 38, "C": 16, "D": 16, "E": 16, "F": 16, "G": 8, "H": 8, "I": 13, "J": 70}
    for k, v in widths.items():
        ws.column_dimensions[k].width = v
    ws.cell(1, 2, "MIDWEST CUSTOM ENGINEERING").font = _font(14, True, head=True)
    ws.cell(2, 2, "Rotary dryer calculator: inputs").font = _font(11, True, ORANGE, head=True)
    ws.cell(3, 2, "Type into the orange ENTRY column only. Blank entry = the default in column C (presets follow "
                  "the material and fuel picks). Every entry is flagged 'override'; values outside the sane range "
                  "are flagged OUT OF RANGE. The value used is column E.").font = _font(8, italic=True,
                                                                                         color=STEEL)
    hdr = ["Item", "Default", "Entry", "Used", "Unit", "Low", "High", "Check", "Source of the default"]
    for j, h in enumerate(hdr):
        c = ws.cell(5, 2 + j, h)
        c.font = _font(9, True, WHITE, head=True)
        c.fill = _fill(BLACK)
    w = InputWriter(bk, ws, entries)
    # job (text)
    w.section("Job")
    for nm, lab in (("j_Job", "Job / quote number"), ("j_Customer", "Customer"), ("j_Location", "Site location"),
                    ("j_Case", "Case description"), ("j_PreparedBy", "Prepared by"), ("j_Date", "Date"),
                    ("j_Record", "Sizing record index")):
        w.add(nm, lab, job.get(nm, ""), text=True)
    mrow = "MATCH(p_Material,m_label,0)"
    w.section("Process")
    w.add("p_Material", "Product", MATERIALS["wood_shavings"]["label"], src="pull-down (Products sheet)", pick="m_label",
          text=True)
    w.add("p_Throughput", "Throughput", 1.5, "per unit below", 0.001, 400000, "Test case 1.5 TPH wet")
    w.add("p_TUnit", "Throughput unit", "TPH", src="pull-down", pick="l_TUnit", text=True)
    w.add("p_TBasis", "Throughput basis", "wet_feed", src="wet_feed / dry_solids / product", pick="l_TBasis",
          text=True)
    w.add("p_MCin", "Infeed moisture", f"=INDEX(m_mc_in,{mrow})", "% wet basis", 2, 90, "product typical value")
    w.add("p_MCout", "Product moisture", f"=INDEX(m_mc_out,{mrow})", "% wet basis", 0.5, 40, "product typical value")
    w.add("p_BmRatio", "Backmix ratio", 0, "lb / lb fresh wet feed", 0, 3, "SHEET Input A14")
    w.add("p_BmMC", "Backmix moisture", "=p_MCout", "% wet basis", 0.5, 40, "= product MC")
    w.add("p_BmT", "Backmix temperature", "=s_Tamb", "F", -20, 250, "= ambient (conservative)")
    w.add("p_FeedT", "Fresh feed temperature", "=s_Tamb", "F", -20, 200, "= ambient")
    w.add("p_ProdT", "Product discharge temperature", f"=INDEX(m_product_temp_F,{mrow})", "F", 100, 400,
          "product preset")
    w.add("p_Cp", "Material specific heat (dry)", f"=INDEX(m_cp,{mrow})", "BTU/lb-F", 0.2, 0.9, "material preset")
    w.add("p_RhoDry", "Bulk density, dry product", f"=INDEX(m_bulk_density_dry,{mrow})", "lb/ft3", 2, 120,
          "material preset")
    w.add("p_RhoWet", "Bulk density, wet infeed", "=p_RhoDry*(1+p_MCin/(100-p_MCin))", "lb/ft3", 2, 150,
          "= dry x (1 + dry-basis MC), no shrink or swell")
    w.add("p_Dp", "Design particle size (volume-equivalent dia)", f"=INDEX(m_particle_size_in,{mrow})", "in",
          0.002, 4, "material preset")
    w.add("p_RhoP", "Particle density", f"=INDEX(m_particle_density,{mrow})", "lb/ft3", 5, 200, "material preset")
    w.add("p_Phi", "Particle sphericity", f"=INDEX(m_sphericity,{mrow})", "-", 0.1, 1, "material preset")
    w.add("p_MaxT", "Maximum product temperature", f"=INDEX(m_max_product_temp_F,{mrow})", "F", 100, 600,
          "material preset")
    w.add("p_Residence", "Target drum residence time", f"=INDEX(m_residence_target_min,{mrow})", "min", 1, 90,
          "material preset")
    w.add("p_VERmin", "VER design range, low", f"=INDEX(m_ver_min,{mrow})", "lb H2O/hr-ft3", 0.2, 15,
          "material preset")
    w.add("p_VERmax", "VER design range, high", f"=INDEX(m_ver_max,{mrow})", "lb H2O/hr-ft3", 0.2, 15,
          "material preset")
    w.add("p_Fire", "Fire risk class", f"=INDEX(m_fire_risk,{mrow})", "", src="material preset", text=True)
    w.add("p_Hours", "Operating hours per year", 7500, "hr/yr", 100, 8760, "SHEET Input H31")
    w.add("p_VOC", "Product VOC factor", 0, "lb VOC/oven-dry ton", 0, 20,
          "0 = not estimated; AP-42 Ch.10.6 or a stack test (wood)")
    w.section("Site")
    w.add("s_Tamb", "Ambient temperature", 60, "F", -40, 120, "SHEET Input D4")
    w.add("s_W", "Ambient humidity ratio", 0.002, "lb H2O/lb dry air", 0, 0.03, "SHEET Input D6")
    w.add("s_Elev", "Elevation", 1200, "ft", -300, 10000, "SHEET Input A10")
    frow = "MATCH(f_Fuel,fu_label,0)"
    w.section("Fuel and burner")
    w.add("f_Fuel", "Fuel / burner", FUELS["biomass"]["label"], src="pull-down", pick="fu_label", text=True)
    w.add("f_HV", "Heating value", f"=INDEX(fu_heating_value,{frow})", "BTU/lb", 1000, 25000, "fuel preset")
    w.add("f_HVbasis", "Heating value basis", f"=INDEX(fu_heating_value_basis,{frow})", "", src="fuel preset",
          pick="l_HVbasis", text=True)
    w.add("f_HVsource", "Heating value used", "entered", "", src="entered, or 'analysis' = LHV from the analysis",
          pick="l_HVsource", text=True)
    w.add("f_MC", "Fuel moisture as fired", f"=INDEX(fu_moisture_wb,{frow})", "% wet basis", 0, 60, "fuel preset")
    w.add("f_Density", "Fuel density (solid bulk or liquid)", f"=INDEX(fu_density,{frow})", "lb/ft3", 0.01, 70,
          "fuel preset")
    w.add("f_EA", "Excess air", f"=INDEX(fu_excess_air_pct,{frow})", "% excess air", 0, 400,
          "fuel preset (130 = 2.3 x stoichiometric)")
    w.add("f_Eff", "Furnace efficiency (unburned fuel + radiation only)", f"=INDEX(fu_furnace_efficiency,{frow})",
          "fraction", 0.8, 1.0, "MCE: 98% gas, 93% biomass (Jason 2026-11-07)")
    w.add("f_Cp", "Fuel specific heat", f"=INDEX(fu_cp,{frow})", "BTU/lb-F", 0.2, 1.0, "fuel preset")
    w.add("f_T", "Fuel temperature", "=s_Tamb", "F", -40, 200, "= ambient")
    for u in ULT:
        w.add(f"f_u{u}", f"Ultimate analysis {u} (dry)", f"=INDEX(fu_u_{u},{frow})", "mass % dry", 0, 100,
              "fuel preset (solid and liquid fuels)")
    for g in GAS_COMPONENTS:
        w.add(f"f_g{g}", f"Gas composition {g}", f"=INDEX(fu_g_{g},{frow})", "mol %", 0, 100,
              "fuel preset (gas fuels)")
    w.section("Rotary drum dryer")
    w.add("r_Tin", "Dryer inlet gas temperature", 900, "F", 250, 1800, "MCE 900 F (Jason 2026-11-07)")
    w.add("r_Texh", "Dryer exhaust temperature", 180, "F", 120, 400, "SHEET Input F24")
    w.add("r_Recycle", "Recycle fraction of exhaust", 0, "fraction", 0, 0.8, "SHEET Input H28")
    w.add("r_Trec", "Recycle gas temperature", "=r_Texh-5", "F", 100, 400, "SHEET Input F29")
    w.add("r_Leak", "Seal leakage air", 5, "% of inlet gas", 0, 30, "MCE assumption, confirm")
    w.add("r_ShellMethod", "Shell loss method", "UA", "", src="UA = U x A x (T gas avg - T amb)", pick="l_Shell",
          text=True)
    w.add("r_Insulated", "Insulation jacket", "No", "", src="pull-down", pick="l_YesNo", text=True)
    w.add("r_U", "Shell U", '=IF(r_Insulated="Yes",0.5,1.5)', "BTU/hr-ft2-F", 0.05, 6,
          "1.5 bare / 0.5 jacketed (accepted by Jason 2026-11-07)")
    w.add("r_ShellPct", "Shell loss (percent method)", 5, "% of burner LHV", 0, 20, "fallback")
    w.add("r_BurnerMargin", "Burner design margin", 1.10, "x operating", 1, 2, "MCE 1.10 (Jason 2026-11-07)")
    w.add("r_DesignFactor", "Design throughput factor (feeders)", 1.25, "x operating", 1, 3, "MCE assumption, confirm")
    w.add("r_Vtarget", "Drum gas velocity target", 350, "FPM", 100, 1500, "MCE target (Jason 2026-11-07)")
    w.add("r_Vtol", "Velocity allowance over target (alternate only)", 10, "%", 0, 50, "MCE assumption, confirm")
    w.add("r_EntFrac", "Entrainment limit", 0.5, "x terminal velocity", 0.1, 1, "MCE assumption, confirm")
    w.add("r_FillMin", "Drum fill, minimum", 5, "% of volume", 1, 25, "MCE assumption, confirm")
    w.add("r_FillMax", "Drum fill, maximum", 15, "% of volume", 1, 25, "MCE assumption, confirm")
    w.add("r_Crit", "Drum speed", 25, "% of critical", 5, 50, "MCE assumption, confirm")
    w.add("r_CritMin", "Drum speed, minimum", 15, "% of critical", 5, 50, "")
    w.add("r_CritMax", "Drum speed, maximum", 35, "% of critical", 5, 50, "")
    w.add("r_SlopeMin", "Drum slope, minimum", 0, "in/ft", 0, 2, "")
    w.add("r_SlopeMax", "Drum slope, maximum", 1, "in/ft", 0, 2, "")
    w.add("r_LDmin", "L/D, minimum", 4, "-", 2, 15, "")
    w.add("r_LDmax", "L/D, maximum", 10, "-", 2, 15, "")
    w.add("r_Lnormal", "Normal maximum drum length", 60, "ft", 10, 100, "Jason 2026-11-07 (to 80 ft possible)")
    w.add("r_DewMargin", "Minimum exhaust margin above dew point", 30, "F", 0, 150, "MCE assumption, confirm")
    w.add("r_ForceD", "Force drum diameter (0 = pick)", 0, "ft", 0, 20, "check a given drum")
    w.add("r_ForceL", "Force drum length (0 = pick)", 0, "ft", 0, 120, "")
    w.section("Air system")
    w.add("a_DuctV", "Duct velocity target", "=IF(p_RhoDry>12,5200,4500)", "FPM", 1500, 8000, "SHEET Input A23")
    w.add("a_DuctInc", "Duct size increment", 1, "in", 0.5, 6, "MCE assumption, confirm")
    w.add("a_Conveyed", "Product air conveyed to cyclone", "Yes", "", src="SHEET Input A25", pick="l_YesNo",
          text=True)
    w.add("a_MinRatio", "Minimum gas to product for conveying", 3, "lb/lb", 0.5, 20, "SHEET Input A26")
    w.add("a_ConvCoeff", "Minimum conveying velocity coefficient", 920, "FPM/sqrt(lb/ft3)", 100, 3000, "SHEET FLOW R15")
    w.add("a_ConvFactor", "Conveying velocity factor", 1.3, "-", 1, 3, "SHEET FLOW R15")
    w.add("a_SP", "Fan static pressure", 18, "in. w.c.", 1, 60, "SHEET DESIGN B29")
    w.add("a_SPbasis", "Fan SP basis", "standard_air", "", src="standard_air = rated at 0.075 lb/ft3",
          pick="l_SPbasis", text=True)
    w.add("a_FanEff", "Fan static efficiency", 0.571, "fraction", 0.3, 0.9, "SHEET factor 1.75 = 1/0.571")
    w.add("a_FanStatic", "Static pressure at fan inlet", 0, "in. w.c. gauge", -60, 10, "0 = site pressure")
    w.add("a_Grain", "Collector outlet loading (stack PM)", 0.02, "gr/dscf", 0.001, 0.5, "MCE assumption, confirm")
    w.add("a_VFD", "Fan VFD or inlet damper", "Yes", "", src="No = motor sized for cold start", pick="l_YesNo",
          text=True)
    ws.freeze_panes = "C6"
    return ws


# --------------------------------------------------------------------------------------- Calc
class CalcWriter:
    def __init__(self, bk: Book, ws):
        self.bk, self.ws, self.r = bk, ws, 5

    def section(self, title):
        self.r += 1
        ws = self.ws
        for c in range(2, 9):
            ws.cell(self.r, c).fill = _fill(STEEL)
        ws.cell(self.r, 1).fill = _fill(ORANGE)
        ws.cell(self.r, 2, title.upper()).font = _font(10, True, WHITE, head=True)
        self.r += 1

    def put(self, nm, label, formula, unit="", fmt="#,##0.00", note="", si=None):
        ws, r = self.ws, self.r
        ws.cell(r, 2, label).font = _font(9)
        c = ws.cell(r, 3, formula)
        c.number_format = fmt
        c.font = _font(9, True)
        ws.cell(r, 4, unit).font = _font(8, color=STEEL)
        if si:
            expr, siu = si
            sc = ws.cell(r, 5, f"={expr.replace('X', f'C{r}')}")
            sc.number_format = "#,##0.00"
            sc.font = _font(8, color=STEEL)
            ws.cell(r, 6, siu).font = _font(8, color=MUTED)
        nc = ws.cell(r, 7, note)
        nc.data_type = "s"
        nc.font = _font(8, color=MUTED)
        if nm:
            self.bk.name(nm, ws, _abs(3, r))
        self.r += 1
        return r


N_CHECKS = 20
LB2KG = "X*0.45359237"
BTU2KW = "X*0.000293071"
F2C = "(X-32)/1.8"


def build_gas_and_calc(bk: Book):
    calc = bk.sheet("Calc")
    gas = bk.sheet("Gas")
    for k, v in {"A": 1.5, "B": 44, "C": 16, "D": 15, "E": 13, "F": 9, "G": 70}.items():
        calc.column_dimensions[k].width = v
    calc.cell(1, 2, "MIDWEST CUSTOM ENGINEERING").font = _font(14, True, head=True)
    calc.cell(2, 2, "Rotary dryer calculator: calculation").font = _font(11, True, ORANGE, head=True)
    calc.cell(3, 2, "Every line is a named formula. Reference state: 32 F liquid water h = 0; all ideal gases h = 0 "
                    "at 32 F; water vapor from liquid at 32 F. SCFM at 70 F, 29.92 in. Hg.").font = \
        _font(8, italic=True, color=STEEL)
    for j, h in enumerate(["Item", "Value", "Unit", "Metric", "", "Method / note"]):
        c = calc.cell(5, 2 + j, h)
        c.font = _font(9, True, WHITE, head=True)
        c.fill = _fill(BLACK)
    w = CalcWriter(bk, calc)

    # ---- site
    w.section("Site")
    w.put("d_Psite", "Barometric pressure", "=14.696*(1-0.0000068754*s_Elev)^5.2559", "psia", "0.000",
          "ASHRAE Fundamentals 2017 Ch.1 Eq.3", si=("X*6.894757", "kPa"))
    w.put("d_MWair", "Dry air molecular weight", "=SUMPRODUCT(g_airfrac,g_MW)", "lb/lbmol", "0.000",
          "N2 78.084, O2 20.946, Ar 0.934, CO2 0.036 mol %")

    # ---- mass balance
    w.section("a. Mass balance")
    w.put("d_T", "Throughput", '=p_Throughput*IF(p_TUnit="TPH",2000,1)', "lb/hr", "#,##0.0", si=(LB2KG, "kg/h"))
    w.put("d_win", "Infeed MC (fraction wb)", "=p_MCin/100", "", "0.0000")
    w.put("d_wout", "Product MC (fraction wb)", "=p_MCout/100", "", "0.0000")
    w.put("d_wbm", "Backmix MC (fraction wb)", "=p_BmMC/100", "", "0.0000")
    w.put("d_Solids", "Dry solids", '=IF(p_TBasis="wet_feed",d_T*(1-d_win),IF(p_TBasis="dry_solids",d_T,'
                                    'd_T*(1-d_wout)))', "lb/hr", "#,##0.0", si=(LB2KG, "kg/h"))
    w.put("d_Wet", "Wet feed", "=d_Solids/(1-d_win)", "lb/hr", "#,##0.0", si=(LB2KG, "kg/h"))
    w.put("d_WaterIn", "Water in", "=d_Wet-d_Solids", "lb/hr", "#,##0.0")
    w.put("d_Product", "Dried product", "=d_Solids/(1-d_wout)", "lb/hr", "#,##0.0", si=(LB2KG, "kg/h"))
    w.put("d_WaterOut", "Water out in product", "=d_Product-d_Solids", "lb/hr", "#,##0.0")
    w.put("d_EvapFresh", "Evaporation (fresh feed)", "=d_WaterIn-d_WaterOut", "lb/hr", "#,##0.0")
    w.put("d_BmWet", "Backmix", "=p_BmRatio*d_Wet", "lb/hr", "#,##0.0")
    w.put("d_BmSolids", "Backmix solids", "=d_BmWet*(1-d_wbm)", "lb/hr", "#,##0.0")
    w.put("d_BmWater", "Backmix water", "=d_BmWet-d_BmSolids", "lb/hr", "#,##0.0")
    w.put("d_DrumSolids", "Drum solids", "=d_Solids+d_BmSolids", "lb/hr", "#,##0.0")
    w.put("d_DrumWaterIn", "Drum water in", "=d_WaterIn+d_BmWater", "lb/hr", "#,##0.0")
    w.put("d_DrumIn", "Drum infeed", "=d_Wet+d_BmWet", "lb/hr", "#,##0.0")
    w.put("d_DrumOut", "Drum discharge", "=d_DrumSolids/(1-d_wout)", "lb/hr", "#,##0.0")
    w.put("d_DrumWaterOut", "Drum water out", "=d_DrumOut-d_DrumSolids", "lb/hr", "#,##0.0")
    w.put("d_Evap", "Evaporation", "=d_DrumWaterIn-d_DrumWaterOut", "lb/hr", "#,##0.0", si=(LB2KG, "kg/h"))
    w.put("d_MixedMC", "Mixed infeed MC", "=d_DrumWaterIn/(d_DrumSolids+d_DrumWaterIn)*100", "% wb", "0.00")
    w.put("d_MCinDB", "Infeed MC, dry basis", "=d_win/(1-d_win)*100", "% db", "0.00")
    w.put("d_MCoutDB", "Product MC, dry basis", "=d_wout/(1-d_wout)*100", "% db", "0.00")
    w.put("d_MassCloseDrum", "Drum mass closure", "=(d_DrumIn-(d_DrumOut+d_Evap))/d_DrumIn*100", "%", "0.0E+00")

    # ---- enthalpies
    w.section("b. Product heat (steam-table enthalpies)")

    def hf(tname):  # saturated liquid, BTU/lb
        t = f"(({tname}-32)/1.8)"
        return f"((((k_hfa*{t}+k_hfb)*{t}+k_hfc)*{t}+k_hfd)*{t})*k_kJ2BTU"

    w.put("d_hfFeed", "h liquid at feed temperature", f"={hf('p_FeedT')}", "BTU/lb", "0.00", "IAPWS-95 fit")
    w.put("d_hfBm", "h liquid at backmix temperature", f"={hf('p_BmT')}", "BTU/lb", "0.00")
    w.put("d_hfProd", "h liquid at product temperature", f"={hf('p_ProdT')}", "BTU/lb", "0.00")
    w.put("d_hvExh", "h vapor at exhaust temperature", "=INDEX(g_hTexh,5)/mw_H2O", "BTU/lb", "0.00",
          "ideal gas from hfg(32 F) = 1,075.2 BTU/lb")
    w.put("d_Qsolids", "Solids sensible heat", "=p_Cp*(d_Solids*(p_ProdT-p_FeedT)+d_BmSolids*(p_ProdT-p_BmT))",
          "BTU/hr", "#,##0", si=(BTU2KW, "kW"))
    w.put("d_HwIn", "Enthalpy of water in", "=d_WaterIn*d_hfFeed+d_BmWater*d_hfBm", "BTU/hr", "#,##0")
    w.put("d_hlIn", "Mean h of water in", "=d_HwIn/d_DrumWaterIn", "BTU/lb", "0.00")
    w.put("d_Qresid", "Residual water sensible heat", "=d_DrumWaterOut*(d_hfProd-d_hlIn)", "BTU/hr", "#,##0",
          si=(BTU2KW, "kW"))
    w.put("d_EvapPerLb", "Evaporation enthalpy", "=d_hvExh-d_hlIn", "BTU/lb", "0.0", "h vapor(T exh) - h liquid(T feed)")
    w.put("d_Qevap", "Evaporation heat", "=d_Evap*d_EvapPerLb", "BTU/hr", "#,##0", si=(BTU2KW, "kW"))
    w.put("d_QProduct", "Product heat total", "=d_Qsolids+d_Qresid+d_Qevap", "BTU/hr", "#,##0", si=(BTU2KW, "kW"))
    w.put("d_QProductPerLb", "Product heat per lb water", "=d_QProduct/d_Evap", "BTU/lb water", "#,##0.0")
    w.put("d_Hfeed", "Feed enthalpy (reference state)",
          "=p_Cp*(d_Solids*(p_FeedT-32)+d_BmSolids*(p_BmT-32))+d_HwIn", "BTU/hr", "#,##0")
    w.put("d_Hprod", "Product enthalpy (reference state)", "=p_Cp*d_DrumSolids*(p_ProdT-32)+d_DrumWaterOut*d_hfProd",
          "BTU/hr", "#,##0")

    # ---- fuel
    w.section("c. Fuel and combustion (per lb fuel as fired)")
    w.put("d_FuelKind", "Fuel kind", "=INDEX(fu_kind,MATCH(f_Fuel,fu_label,0))", "", "@")
    w.put("d_IsGas", "Gas fuel (1/0)", '=IF(d_FuelKind="gas",1,0)', "", "0")
    w.put("d_IsWood", "Biomass (wood) fuel (1/0)", '=IF(INDEX(fu_key,MATCH(f_Fuel,fu_label,0))="biomass",1,0)', "", "0")
    w.put("d_SelfFuel", "Burner fires the dried product (1/0)",
          '=IF(AND(d_IsWood=1,INDEX(m_is_wood,MATCH(p_Material,m_label,0))="Yes"),1,0)', "", "0")
    w.put("d_M", "Fuel moisture (fraction)", "=IF(d_IsGas=1,0,f_MC/100)", "", "0.0000")
    w.put("d_UltSum", "Ultimate analysis sum (dry)", "=f_uC+f_uH+f_uO+f_uN+f_uS+f_uash", "%", "0.00",
          "must be 100 +/- 0.5")
    for u in ULT:
        w.put(f"d_n{u}", f"{u} normalized, as fired", f"=IF(d_UltSum>0,f_u{u}/d_UltSum*(1-d_M),0)", "lb/lb",
              "0.00000")
    w.put("d_O2s", "O2 demand (solid/liquid)", "=d_nC/mw_C+d_nH/mw_H2*0.5+d_nS/mw_S-d_nO/mw_O2", "lbmol/lb", "0.000000")
    w.put("d_HHVd", "HHV dry (Channiwala-Parikh 2002)",
          "=IF(d_UltSum>0,(0.3491*f_uC+1.1783*f_uH+0.1005*f_uS-0.1034*f_uO-0.0151*f_uN-0.0211*f_uash)"
          "/d_UltSum*100*1000*k_kJ2BTU,0)", "BTU/lb", "#,##0")
    w.put("d_LHVd", "LHV dry", "=d_HHVd-k_HFG77B*mw_H2O/mw_H2*IF(d_UltSum>0,f_uH/d_UltSum,0)", "BTU/lb", "#,##0")
    w.put("d_LHVs", "LHV as fired from analysis (solid)", "=d_LHVd*(1-d_M)-k_HFG77B*d_M", "BTU/lb", "#,##0")
    w.put("d_GasSum", "Gas composition sum", "=" + "+".join(f"f_g{g}" for g in GAS_COMPONENTS), "%", "0.00",
          "must be 100 +/- 0.5")
    gsum = "+".join(f"f_g{g}*INDEX(gc_{{c}},{i + 1})" for i, g in enumerate(GAS_COMPONENTS))

    def gs(col):
        return "(" + gsum.replace("{c}", col) + ")"

    w.put("d_MWgas", "Gas MW", f"=IF(d_GasSum>0,{gs('MW')}/d_GasSum,0)", "lb/lbmol", "0.000")
    w.put("d_O2g", "O2 demand (gas)", f"=IF(d_GasSum>0,{gs('O2')}/d_GasSum/d_MWgas,0)", "lbmol/lb", "0.000000")
    w.put("d_LHVg", "LHV from composition (gas)", f"=IF(d_GasSum>0,{gs('LHV')}/d_GasSum/d_MWgas*k_kJ2BTU,0)",
          "BTU/lb", "#,##0")
    w.put("d_H2Og_mol", "H2O formed (gas)", f"=IF(d_GasSum>0,{gs('H2O')}/d_GasSum/d_MWgas,0)", "lbmol/lb",
          "0.000000")
    w.put("d_HHVg", "HHV from composition (gas)", "=d_LHVg+d_H2Og_mol*k_HFG25*k_kJ2BTU", "BTU/lb", "#,##0")
    w.put("d_O2st", "O2 demand used", "=IF(d_IsGas=1,d_O2g,d_O2s)", "lbmol/lb", "0.000000")
    w.put("d_CO2f", "CO2 formed", f"=IF(d_IsGas=1,IF(d_GasSum>0,{gs('CO2')}/d_GasSum/d_MWgas,0),d_nC/mw_C)",
          "lbmol/lb", "0.000000")
    w.put("d_H2Of", "H2O formed (incl. fuel moisture)", "=IF(d_IsGas=1,d_H2Og_mol,d_nH/mw_H2+d_M/mw_H2O)",
          "lbmol/lb", "0.000000")
    w.put("d_SO2f", "SO2 formed", f"=IF(d_IsGas=1,IF(d_GasSum>0,{gs('SO2')}/d_GasSum/d_MWgas,0),d_nS/mw_S)",
          "lbmol/lb", "0.000000")
    w.put("d_N2f", "N2 from fuel", "=IF(d_IsGas=1,IF(d_GasSum>0,f_gN2/d_GasSum/d_MWgas,0),d_nN/mw_N2)", "lbmol/lb",
          "0.000000")
    w.put("d_Ash", "Ash", "=IF(d_IsGas=1,0,d_nash)", "lb/lb", "0.00000")
    w.put("d_Wf", "Water formed", "=d_H2Of*mw_H2O", "lb/lb", "0.0000")
    w.put("d_LHVcalc", "LHV as fired from analysis", "=IF(d_IsGas=1,d_LHVg,d_LHVs)", "BTU/lb", "#,##0")
    w.put("d_HHVcalc", "HHV as fired from analysis", "=IF(d_IsGas=1,d_HHVg,d_HHVd*(1-d_M))", "BTU/lb", "#,##0")
    w.put("d_Hdry", "H dry fraction (normalized)", "=IF(d_UltSum>0,f_uH/d_UltSum,0)", "", "0.0000")
    w.put("d_LHVent", "LHV as fired from the entered value",
          '=IF(d_IsGas=1,IF(f_HVbasis="net_as_fired",f_HV,f_HV*d_LHVg/d_HHVg),'
          'IF(f_HVbasis="net_as_fired",f_HV,IF(f_HVbasis="net_dry",f_HV*(1-d_M)-k_HFG77B*d_M,'
          'IF(f_HVbasis="gross_dry",(f_HV-k_HFG77B*mw_H2O/mw_H2*d_Hdry)*(1-d_M)-k_HFG77B*d_M,'
          '(f_HV/(1-d_M)-k_HFG77B*mw_H2O/mw_H2*d_Hdry)*(1-d_M)-k_HFG77B*d_M))))', "BTU/lb", "#,##0",
          "ISO 18125: LHV_ar = LHV_d (1 - M) - 1,050 M")
    w.put("d_LHV", "LHV as fired USED", '=IF(f_HVsource="analysis",d_LHVcalc,d_LHVent)', "BTU/lb", "#,##0",
          si=("X/0.429923", "kJ/kg"))
    w.put("d_HHV", "HHV as fired", "=d_LHV+k_HFG77B*d_Wf", "BTU/lb", "#,##0")
    w.put("d_HVdev", "Entered vs analysis LHV", "=(d_LHVent-d_LHVcalc)/d_LHVcalc*100", "%", "0.0",
          "flagged above 5%")
    w.put("d_LHVdryBack", "Wood LHV back to dry basis", "=(d_LHV+k_HFG77B*d_M)/(1-d_M)", "BTU/lb", "#,##0",
          "typical wood 7,400 to 8,600")
    w.put("d_StoichAir", "Stoichiometric dry air", "=d_O2st/0.20946*d_MWair", "lb/lb fuel", "0.0000",
          "= 11.53C + 34.34(H - O/8) + 4.29S for solids")
    w.put("d_StoichMassFormula", "Mass formula 11.53C + 34.34(H - O/8) + 4.29S", "=IF(d_IsGas=1,0,11.53*d_nC+"
          "34.34*(d_nH-d_nO/8)+4.29*d_nS)", "lb/lb fuel", "0.0000", "check (solids only)")
    w.put("d_Lambda", "Air / stoichiometric", "=1+f_EA/100", "", "0.000")
    w.put("d_CombAir", "Combustion air (dry)", "=d_StoichAir*d_Lambda", "lb/lb fuel", "0.0000")
    w.put("d_FlueMass", "Combustion products", "=SUMPRODUCT(g_f,g_MW)", "lb/lb fuel", "0.0000",
          "= humid air + 1 - ash")
    w.put("d_FuelIn", "Fuel energy on the reference state",
          "=f_Eff*d_LHV+d_Wf*k_HFG32B+f_Cp*(f_T-32)", "BTU/lb fuel", "#,##0.0",
          "eta LHV + latent of combustion water at 32 F + sensible")
    w.put("d_TflameStart", "Flame temperature iteration start", 2000, "F", "0")
    w.put("d_Tflame", "Adiabatic flame temperature", "=g_TflameEnd", "F", "#,##0", "Newton iteration on Gas sheet",
          si=(F2C, "C"))

    # ---- Gas sheet ------------------------------------------------------------------------
    gs_ = gas
    for c in range(1, 60):
        gs_.column_dimensions[CL(c)].width = 11
    gs_.column_dimensions["B"].width = 22
    gs_.cell(1, 2, "Gas: species tables (lbmol per lb fuel, per lb dry dilution air, per hr)").font = \
        _font(12, True, head=True)
    cols = ["species", "MW", "a", "b", "c", "d", "latent", "airfrac", "fuel prod", "a: comb air", "f: flue",
            "d: dil air", "v: evap", "h(T amb)", "h(T in)", "h(T exh)", "h(T rec)",
            "Lf", "Ld", "L0", "Ef", "Ed", "E0", "Mf", "Md", "M0", "Rf", "Rd", "R0",
            "combustion_air", "dilution_air", "leakage_air", "fuel_gas", "dryer_inlet", "dryer_exhaust", "recycle",
            "stack"]
    C = {n: 2 + i for i, n in enumerate(cols)}
    hdr_r, r0 = 4, 5
    for n, c in C.items():
        cell = gs_.cell(hdr_r, c, n)
        cell.font = _font(8, True, WHITE)
        cell.fill = _fill(BLACK)
        cell.alignment = Alignment(wrap_text=True)
    rows = {s: r0 + i for i, s in enumerate(SPECIES)}
    rN = r0 + len(SPECIES) - 1
    air = dict(P.AIR_MOLE_FRAC)
    for s, r in rows.items():
        a, b, c, d = P._CP[s]
        gs_.cell(r, C["species"], s)
        gs_.cell(r, C["MW"], f"=mw_{s}")
        for k, v in zip("abcd", (a, b, c, d)):
            gs_.cell(r, C[k], v)
        gs_.cell(r, C["latent"], "=k_HFG32B*mw_H2O" if s == "H2O" else 0)
        gs_.cell(r, C["airfrac"], air.get(s, 0.0))
        prod = {"N2": "=d_N2f", "O2": "=-d_O2st", "Ar": 0, "CO2": "=d_CO2f", "H2O": "=d_H2Of", "SO2": "=d_SO2f"}[s]
        gs_.cell(r, C["fuel prod"], prod)
        A = CL(C["airfrac"])
        if s == "H2O":
            gs_.cell(r, C["a: comb air"], "=d_CombAir*s_W/mw_H2O")
            gs_.cell(r, C["d: dil air"], "=s_W/mw_H2O")
            gs_.cell(r, C["v: evap"], "=d_Evap/mw_H2O")
        else:
            gs_.cell(r, C["a: comb air"], f"=d_CombAir/d_MWair*{A}{r}")
            gs_.cell(r, C["d: dil air"], f"={A}{r}/d_MWair")
            gs_.cell(r, C["v: evap"], 0)
        gs_.cell(r, C["f: flue"], f"={CL(C['a: comb air'])}{r}+{CL(C['fuel prod'])}{r}")
        for key, tn in (("h(T amb)", "s_Tamb"), ("h(T in)", "r_Tin"), ("h(T exh)", "r_Texh"), ("h(T rec)", "r_Trec")):
            tk = f"(({tn}+459.67)/1.8)"
            co = {k: f"{CL(C[k])}{r}" for k in "abcd"}
            gs_.cell(r, C[key], f"=({co['a']}*({tk}-k_T0K)+{co['b']}/2*({tk}^2-k_T0K^2)+{co['c']}/3*({tk}^3-k_T0K^3)"
                                f"+{co['d']}/4*({tk}^4-k_T0K^4))*k_kJ2BTU+{CL(C['latent'])}{r}")
        dcell = f"{CL(C['d: dil air'])}{r}"
        gs_.cell(r, C["Lf"], f"=d_lam*d_mmf*{dcell}/d_dmass")
        gs_.cell(r, C["Ld"], f"=d_lam*d_mmd*{dcell}/d_dmass")
        gs_.cell(r, C["L0"], f"=d_lam*d_mm0*{dcell}/d_dmass")
        f_ = f"{CL(C['f: flue'])}{r}"
        v_ = f"{CL(C['v: evap'])}{r}"
        gs_.cell(r, C["Ef"], f"=({f_}+{CL(C['Lf'])}{r})/(1-r_Recycle)")
        gs_.cell(r, C["Ed"], f"=({dcell}+{CL(C['Ld'])}{r})/(1-r_Recycle)")
        gs_.cell(r, C["E0"], f"=({v_}+{CL(C['L0'])}{r})/(1-r_Recycle)")
        gs_.cell(r, C["Mf"], f"={f_}+r_Recycle*{CL(C['Ef'])}{r}")
        gs_.cell(r, C["Md"], f"={dcell}+r_Recycle*{CL(C['Ed'])}{r}")
        gs_.cell(r, C["M0"], f"=r_Recycle*{CL(C['E0'])}{r}")
        for k1, k2 in (("Rf", "Ef"), ("Rd", "Ed"), ("R0", "E0")):
            gs_.cell(r, C[k1], f"=r_Recycle*{CL(C[k2])}{r}")
        # final streams per hour
        gs_.cell(r, C["combustion_air"], f"=d_mf*{CL(C['a: comb air'])}{r}")
        gs_.cell(r, C["dilution_air"], f"=d_md*{dcell}")
        gs_.cell(r, C["leakage_air"], f"=d_mf*{CL(C['Lf'])}{r}+d_md*{CL(C['Ld'])}{r}+{CL(C['L0'])}{r}")
        gs_.cell(r, C["fuel_gas"], f"=d_mf*{f_}")
        gs_.cell(r, C["dryer_inlet"], f"=d_mf*{CL(C['Mf'])}{r}+d_md*{CL(C['Md'])}{r}+{CL(C['M0'])}{r}")
        gs_.cell(r, C["dryer_exhaust"], f"=d_mf*{CL(C['Ef'])}{r}+d_md*{CL(C['Ed'])}{r}+{CL(C['E0'])}{r}")
        gs_.cell(r, C["recycle"], f"=r_Recycle*{CL(C['dryer_exhaust'])}{r}")
        gs_.cell(r, C["stack"], f"=(1-r_Recycle)*{CL(C['dryer_exhaust'])}{r}")
        for c in range(3, C["stack"] + 1):
            gs_.cell(r, c).number_format = "0.000000"
    alias = {"MW": "MW", "a": "a", "b": "b", "c": "c", "d": "d", "latent": "latent", "airfrac": "airfrac",
             "fuel prod": "prod", "a: comb air": "aa", "f: flue": "f", "d: dil air": "dd", "v: evap": "v",
             "h(T amb)": "hTa", "h(T in)": "hTin", "h(T exh)": "hTexh", "h(T rec)": "hTrec"}
    for k in ["Lf", "Ld", "L0", "Ef", "Ed", "E0", "Mf", "Md", "M0", "Rf", "Rd", "R0"]:
        alias[k] = k
    stream_names = {"combustion_air": "sCA", "dilution_air": "sDA", "leakage_air": "sLA", "fuel_gas": "sFG",
                    "dryer_inlet": "sIN", "dryer_exhaust": "sEX", "recycle": "sRC", "stack": "sST"}
    alias.update(stream_names)
    for k, a in alias.items():
        bk.name(f"g_{a}", gs_, f"${CL(C[k])}${r0}:${CL(C[k])}${rN}")

    # stream summary rows under the species table
    sr = rN + 2
    stream_T = {"combustion_air": "s_Tamb", "dilution_air": "s_Tamb", "leakage_air": "s_Tamb", "fuel_gas": "d_Tflame",
                "dryer_inlet": "r_Tin", "dryer_exhaust": "r_Texh", "recycle": "r_Trec", "stack": "r_Texh"}
    metrics = [("lbmol/hr", "SUM({col})"), ("lb/hr", "SUMPRODUCT({col},g_MW)"), ("H2O lb/hr", "INDEX({col},5)*mw_H2O"),
               ("dry gas lb/hr", "{lb}-{h2o}"), ("humidity lb/lb dry", "IF({dry}>0,{h2o}/{dry},0)"),
               ("temperature F", "{T}"), ("SCFM", "{mol}*k_StdVol/60"),
               ("ACFM", "{mol}*k_R*({T}+459.67)/d_Psite/60"), ("density lb/ft3", "IF({acfm}>0,{lb}/60/{acfm},0)"),
               ("O2 vol % dry", "IF({mol}>INDEX({col},5),INDEX({col},2)/({mol}-INDEX({col},5))*100,0)"),
               ("H2O vol %", "IF({mol}>0,INDEX({col},5)/{mol}*100,0)")]
    gs_.cell(sr - 1, 2, "Stream summary").font = _font(9, True)
    for i, (lab, _) in enumerate(metrics):
        gs_.cell(sr + i, 2, lab).font = _font(8, True)
    for sname, short in stream_names.items():
        col = C[sname]
        cl = CL(col)
        rng = f"{cl}{r0}:{cl}{rN}"
        refs = {"col": rng, "mol": f"{cl}{sr}", "lb": f"{cl}{sr + 1}", "h2o": f"{cl}{sr + 2}", "dry": f"{cl}{sr + 3}",
                "T": stream_T[sname], "acfm": f"{cl}{sr + 7}"}
        for i, (lab, expr) in enumerate(metrics):
            cell = gs_.cell(sr + i, col, "=" + expr.format(**refs))
            cell.number_format = "#,##0.00" if i not in (4, 9, 10, 8) else "0.0000"
        for i, key in enumerate(["mol", "lb", "h2o", "dry", "W", "T", "scfm", "acfm", "rho", "o2", "h2ovol"]):
            bk.name(f"x_{short}_{key}", gs_, _abs(col, sr + i))

    # flame temperature Newton iteration
    fr = sr + len(metrics) + 2
    gs_.cell(fr, 2, "Adiabatic flame temperature (Newton, products of 1 lb fuel at the stated excess air)").font = \
        _font(9, True)
    gs_.cell(fr + 1, 2, "Target H (BTU/lb fuel)")
    gs_.cell(fr + 1, 3, "=d_FuelIn+SUMPRODUCT(g_aa,g_hTa)")
    bk.name("g_Htarget", gs_, _abs(3, fr + 1))
    gs_.cell(fr + 2, 2, "iteration")
    gs_.cell(fr + 2, 3, "T (F)")
    gs_.cell(fr + 2, 4, "H(T)")
    gs_.cell(fr + 2, 5, "cp total")
    it0 = fr + 3
    for i in range(14):
        r = it0 + i
        gs_.cell(r, 2, i)
        gs_.cell(r, 3, "=d_TflameStart" if i == 0 else f"=C{r - 1}-(D{r - 1}-g_Htarget)/E{r - 1}")
        tk = f"((C{r}+459.67)/1.8)"
        gs_.cell(r, 4, f"=SUMPRODUCT(g_f,g_a*({tk}-k_T0K)+g_b/2*({tk}^2-k_T0K^2)+g_c/3*({tk}^3-k_T0K^3)"
                       f"+g_d/4*({tk}^4-k_T0K^4))*k_kJ2BTU+SUMPRODUCT(g_f,g_latent)")
        gs_.cell(r, 5, f"=SUMPRODUCT(g_f,g_a+g_b*{tk}+g_c*{tk}^2+g_d*{tk}^3)*0.238845897")
    bk.name("g_TflameEnd", gs_, _abs(3, it0 + 13))

    # ---- gas side solve (back on Calc)
    w.section("d. Gas side heat and mass balance (closed form at fixed inlet temperature)")
    w.put("d_lam", "Leakage fraction", "=r_Leak/100", "", "0.0000")
    w.put("d_fmass", "|f| products per lb fuel", "=SUMPRODUCT(g_f,g_MW)", "lb/lb", "0.0000")
    w.put("d_dmass", "|d| humid air per lb dry air", "=1+s_W", "lb/lb", "0.0000")
    w.put("d_k", "k = 1 - r (1 + leak)", "=1-r_Recycle*(1+d_lam)", "", "0.000000")
    w.put("d_ef", "e_f", "=(1+d_lam)*d_fmass/d_k", "", "0.000000")
    w.put("d_ed", "e_d", "=(1+d_lam)*d_dmass/d_k", "", "0.000000")
    w.put("d_e0", "e_0", "=d_Evap/d_k", "", "0.000")
    w.put("d_mmf", "inlet mass per lb fuel", "=d_fmass+r_Recycle*d_ef", "", "0.000000")
    w.put("d_mmd", "inlet mass per lb dilution air", "=d_dmass+r_Recycle*d_ed", "", "0.000000")
    w.put("d_mm0", "inlet mass constant", "=r_Recycle*d_e0", "", "0.000")
    w.put("d_A1", "Furnace: coefficient on fuel",
          "=d_FuelIn+SUMPRODUCT(g_aa,g_hTa)+SUMPRODUCT(g_Rf,g_hTrec)-SUMPRODUCT(g_Mf,g_hTin)", "BTU/lb", "#,##0.000")
    w.put("d_B1", "Furnace: coefficient on dilution air",
          "=SUMPRODUCT(g_dd,g_hTa)+SUMPRODUCT(g_Rd,g_hTrec)-SUMPRODUCT(g_Md,g_hTin)", "BTU/lb", "#,##0.000")
    w.put("d_C1", "Furnace: constant", "=SUMPRODUCT(g_R0,g_hTrec)-SUMPRODUCT(g_M0,g_hTin)", "BTU/hr", "#,##0.0")
    w.put("d_A2", "Drum: coefficient on fuel",
          '=SUMPRODUCT(g_Mf,g_hTin)+SUMPRODUCT(g_Lf,g_hTa)-SUMPRODUCT(g_Ef,g_hTexh)'
          '-IF(r_ShellMethod="percent",r_ShellPct/100*d_LHV,0)', "BTU/lb", "#,##0.000")
    w.put("d_B2", "Drum: coefficient on dilution air",
          "=SUMPRODUCT(g_Md,g_hTin)+SUMPRODUCT(g_Ld,g_hTa)-SUMPRODUCT(g_Ed,g_hTexh)", "BTU/lb", "#,##0.000")
    w.put("d_C2base", "Drum: constant before shell loss",
          "=SUMPRODUCT(g_M0,g_hTin)+SUMPRODUCT(g_L0,g_hTa)-SUMPRODUCT(g_E0,g_hTexh)+d_Hfeed-d_Hprod", "BTU/hr",
          "#,##0.0")
    w.put("d_Det", "Determinant", "=d_A1*d_B2-d_A2*d_B1", "", "#,##0.000")
    w.put("d_dT_shell", "Shell driving temperature", "=(r_Tin+r_Texh)/2-s_Tamb", "F", "#,##0.0")
    w.put("d_UAon", "UA method (1/0)", '=IF(r_ShellMethod="UA",1,0)', "", "0")
    w.put("d_Forced", "Forced drum (1/0)", "=IF(AND(r_ForceD>0,r_ForceL>0),1,0)", "", "0")
    passes = {}
    for p, ua in (("A", "=0*d_UAon"), ("B", "=d_UAon*r_U*IF(d_Forced=1,PI()*r_ForceD*r_ForceL,dr_A_Shell)"),
                  ("C", "=d_UAon*r_U*IF(d_Forced=1,PI()*r_ForceD*r_ForceL,dr_B_Shell)"),
                  ("D", "=IF(d_DrumAlternates=1,d_UAon*r_U*PI()*dr_Z_D*dr_Z_L,d_UA_C)")):
        w.put(f"d_UA_{p}", f"Pass {p}: shell UA", ua, "BTU/hr-F", "#,##0.0",
              {"A": "no shell loss", "B": "UA from the pass A drum", "C": "UA from the pass B drum",
               "D": "final: = pass C, or the kept drum when the pass B and C drums alternate"}[p])
        w.put(f"d_C2_{p}", f"Pass {p}: drum constant", f"=d_C2base-d_UA_{p}*d_dT_shell", "BTU/hr", "#,##0.0")
        w.put(f"d_mf_{p}", f"Pass {p}: fuel", f"=(-d_C1*d_B2+d_C2_{p}*d_B1)/d_Det", "lb/hr", "#,##0.00")
        w.put(f"d_md_{p}", f"Pass {p}: dilution air", f"=(-d_A1*d_C2_{p}+d_A2*d_C1)/d_Det", "lb/hr", "#,##0.0")
        w.put(f"d_GinMass_{p}", f"Pass {p}: dryer inlet gas",
              f"=SUMPRODUCT(g_Mf,g_MW)*d_mf_{p}+SUMPRODUCT(g_Md,g_MW)*d_md_{p}+SUMPRODUCT(g_M0,g_MW)", "lb/hr",
              "#,##0.0")
        w.put(f"d_GoutMass_{p}", f"Pass {p}: dryer exhaust gas",
              f"=SUMPRODUCT(g_Ef,g_MW)*d_mf_{p}+SUMPRODUCT(g_Ed,g_MW)*d_md_{p}+SUMPRODUCT(g_E0,g_MW)", "lb/hr",
              "#,##0.0")
        w.put(f"d_ACFM_{p}", f"Pass {p}: exhaust ACFM",
              f"=(SUM(g_Ef)*d_mf_{p}+SUM(g_Ed)*d_md_{p}+SUM(g_E0))*k_R*(r_Texh+459.67)/d_Psite/60", "ACFM",
              "#,##0.0")
        passes[p] = True
    w.put("d_mf", "FUEL", "=d_mf_D", "lb/hr", "#,##0.00", "final (pass D)", si=(LB2KG, "kg/h"))
    w.put("d_md", "DILUTION (MAKE-UP) AIR", "=d_md_D", "lb/hr", "#,##0.0", "negative = inlet temperature not "
                                                                         "reachable at this excess air",
          si=(LB2KG, "kg/h"))
    w.put("d_ResFurnace", "Furnace balance residual", "=d_A1*d_mf+d_B1*d_md+d_C1", "BTU/hr", "0.0E+00")
    w.put("d_ResDrum", "Drum balance residual", "=d_A2*d_mf+d_B2*d_md+d_C2_D", "BTU/hr", "0.0E+00")

    # ---- psychrometrics
    w.section("Exhaust psychrometrics (IAPWS-IF97 Region 4)")
    w.put("d_pw", "H2O partial pressure", "=x_sEX_h2ovol/100*d_Psite", "psia", "0.0000")
    w.put("d_pwMPa", "  in MPa", "=d_pw*k_PSIKPA/1000", "MPa", "0.000000")
    w.put("d_beta", "  beta = p^0.25", "=d_pwMPa^0.25", "", "0.000000")
    w.put("d_Eif", "  E", "=d_beta^2+k_if3*d_beta+k_if6", "", "0.000000")
    w.put("d_Fif", "  F", "=k_if1*d_beta^2+k_if4*d_beta+k_if7", "", "0.000000")
    w.put("d_Gif", "  G", "=k_if2*d_beta^2+k_if5*d_beta+k_if8", "", "0.000000")
    w.put("d_Dif", "  D", "=2*d_Gif/(-d_Fif-SQRT(d_Fif^2-4*d_Eif*d_Gif))", "", "0.000000")
    w.put("d_Tdew", "Exhaust dew point",
          "=(k_if10+d_Dif-SQRT((k_if10+d_Dif)^2-4*(k_if9+k_if10*d_Dif)))/2*1.8-459.67", "F", "0.0",
          si=(F2C, "C"))
    w.put("d_DewMargin", "Margin above dew point", "=r_Texh-d_Tdew", "F", "0.0")
    tk = "((r_Texh+459.67)/1.8)"
    w.put("d_th", "  theta", f"={tk}+k_if9/({tk}-k_if10)", "", "0.000000")
    w.put("d_Aif", "  A", "=d_th^2+k_if1*d_th+k_if2", "", "0.000000")
    w.put("d_Bif", "  B", "=k_if3*d_th^2+k_if4*d_th+k_if5", "", "0.000000")
    w.put("d_Cif", "  C", "=k_if6*d_th^2+k_if7*d_th+k_if8", "", "0.000000")
    w.put("d_psat", "Saturation pressure at exhaust temperature",
          "=(2*d_Cif/(-d_Bif+SQRT(d_Bif^2-4*d_Aif*d_Cif)))^4*1000/k_PSIKPA", "psia", "0.0000")
    w.put("d_RH", "Relative humidity", "=d_pw/d_psat*100", "%", "0.0")
    w.put("d_Wsat", "Saturation humidity", "=IF(d_psat<d_Psite,mw_H2O/(x_sEX_dry/(x_sEX_mol-INDEX(g_sEX,5)))"
                                           "*d_psat/(d_Psite-d_psat),0)", "lb/lb dry gas", "0.0000")
    w.put("d_PctSat", "Percent saturation", "=IF(d_Wsat>0,x_sEX_W/d_Wsat*100,0)", "%", "0.0")
    w.put("d_GasToProduct", "Exhaust gas to product", "=x_sEX_lb/d_Product", "lb/lb", "0.00")

    # ---- losses and energy balance
    w.section("e. Losses and energy balance (LHV basis)")
    w.put("d_Qfuel", "Fuel input (LHV)", "=d_mf*d_LHV", "BTU/hr", "#,##0", si=(BTU2KW, "kW"))
    w.put("d_Qshell", "Shell loss", '=IF(r_ShellMethod="UA",d_UA_D*d_dT_shell,r_ShellPct/100*d_Qfuel)', "BTU/hr",
          "#,##0", si=(BTU2KW, "kW"))
    w.put("d_Qfurnace", "Furnace loss (unburned + radiation)", "=(1-f_Eff)*d_Qfuel", "BTU/hr", "#,##0")
    w.put("d_Qrecduct", "Recycle duct loss", "=SUMPRODUCT(g_sRC,g_hTexh)-SUMPRODUCT(g_sRC,g_hTrec)", "BTU/hr", "#,##0")
    w.put("d_HairIn", "Air enthalpy in (all air at ambient)",
          "=SUMPRODUCT(g_sCA,g_hTa)+SUMPRODUCT(g_sDA,g_hTa)+SUMPRODUCT(g_sLA,g_hTa)", "BTU/hr", "#,##0")
    w.put("d_FuelDatum", "Fuel latent + sensible terms", "=d_mf*(d_Wf*k_HFG32B+f_Cp*(f_T-32))", "BTU/hr", "#,##0")
    w.put("d_Hstack", "Stack gas enthalpy", "=SUMPRODUCT(g_sST,g_hTexh)", "BTU/hr", "#,##0")
    w.put("d_Qstack", "Stack loss", "=d_Hstack-d_Evap*d_hvExh-d_HairIn-d_FuelDatum", "BTU/hr", "#,##0",
          si=(BTU2KW, "kW"))
    w.put("d_Qleak", "  of which leakage air heating", "=SUMPRODUCT(g_sLA,g_hTexh)-SUMPRODUCT(g_sLA,g_hTa)", "BTU/hr",
          "#,##0")
    w.put("d_Uses", "Sum of uses", "=d_Qevap+d_Qsolids+d_Qresid+d_Qstack+d_Qshell+d_Qfurnace+d_Qrecduct", "BTU/hr",
          "#,##0")
    w.put("d_CloseBreak", "Breakdown closure", "=(d_Qfuel-d_Uses)/d_Qfuel*100", "%", "0.0E+00", "< 0.5% required")
    w.put("d_Ein", "Reference-state energy in", "=d_mf*d_FuelIn+d_HairIn+d_Hfeed+d_Qfurnace", "BTU/hr", "#,##0")
    w.put("d_Eout", "Reference-state energy out", "=d_Hstack+d_Hprod+d_Qshell+d_Qrecduct+d_Qfurnace", "BTU/hr", "#,##0")
    w.put("d_CloseE", "Energy closure", "=(d_Ein-d_Eout)/d_Ein*100", "%", "0.0E+00", "< 0.5% required")
    w.put("d_Min", "Mass in (feed + fuel + air)", "=d_Wet+d_mf+x_sCA_lb+x_sDA_lb+x_sLA_lb", "lb/hr", "#,##0.0")
    w.put("d_Mout", "Mass out (product + stack + ash)", "=d_Product+x_sST_lb+d_mf*d_Ash", "lb/hr", "#,##0.0")
    w.put("d_CloseM", "Mass closure", "=(d_Min-d_Mout)/d_Min*100", "%", "0.0E+00", "< 0.1% required")

    # ---- results
    w.section("f. Results")
    w.put("d_BurnerOp", "Burner operating (LHV)", "=d_Qfuel/1000000", "MMBtu/hr", "0.00", si=("X*293.071", "kW"))
    w.put("d_BurnerHHV", "Burner operating (HHV)", "=d_mf*d_HHV/1000000", "MMBtu/hr", "0.00", si=("X*293.071", "kW"))
    w.put("d_BurnerDesign", "Burner design rating (LHV)", "=d_BurnerOp*r_BurnerMargin", "MMBtu/hr", "0.00",
          si=("X*293.071", "kW"))
    w.put("d_BtuLb", "Specific heat use (LHV)", "=d_Qfuel/d_Evap", "BTU/lb water", "#,##0",
          si=("X/0.429923", "kJ/kg"))
    w.put("d_BtuLbHHV", "Specific heat use (HHV)", "=d_mf*d_HHV/d_Evap", "BTU/lb water", "#,##0")
    w.put("d_FuelSCFH", "Gas fuel volume", "=IF(d_IsGas=1,d_mf/d_MWgas*k_StdVol,0)", "SCFH", "#,##0",
          "70 F, 29.92 in. Hg", si=("X*0.0283168", "Sm3/h"))
    w.put("d_FuelFt3", "Solid / liquid fuel volume", "=IF(d_IsGas=1,0,d_mf/f_Density)", "ft3/hr", "#,##0.0")
    w.put("d_FuelGal", "Liquid fuel volume", '=IF(d_FuelKind="liquid",d_mf/f_Density*7.48052,0)', "gal/hr", "#,##0.0")
    w.put("d_AnnFuel", "Annual fuel", "=d_mf*p_Hours/2000", "tons/yr", "#,##0")
    w.put("d_AnnMMBtu", "Annual fuel energy (LHV)", "=d_BurnerOp*p_Hours", "MMBtu/yr", "#,##0")
    w.put("d_AnnProduct", "Annual product", "=d_Product*p_Hours/2000", "tons/yr", "#,##0")
    w.put("d_NetProduct", "Net product after self-fueling", "=IF(d_SelfFuel=1,d_Product-d_mf,d_Product)", "lb/hr",
          "#,##0", "wood or biomass fuel = dried product")
    w.put("d_FracBurned", "Share of product burned", "=IF(d_SelfFuel=1,d_mf/d_Product,0)", "", "0.0%")

    # ---- drum (from Drum sheet)
    w.section("g. Drum (from the Drum sheet)")
    w.put("d_DrumD", "Drum diameter", "=IF(d_Forced=1,r_ForceD,dr_D_D)", "ft", "0", si=("X*0.3048", "m"))
    w.put("d_DrumL", "Drum length", "=IF(d_Forced=1,r_ForceL,dr_D_L)", "ft", "0", si=("X*0.3048", "m"))
    for nm, lab, key, fmt, unit in (("d_DrumVER", "VER", "VER", "0.00", "lb H2O/hr-ft3"),
                                    ("d_DrumVel", "Gas velocity (free area)", "Vel", "#,##0", "FPM"),
                                    ("d_DrumRes", "Residence time", "Theta", "0.0", "min"),
                                    ("d_DrumFill", "Fill", "Fill", "0.0", "%"),
                                    ("d_DrumSlope", "Slope", "Slope", "0.000", "in/ft"),
                                    ("d_DrumRPM", "Speed", "N", "0.00", "rpm"),
                                    ("d_DrumNc", "Critical speed", "Nc", "0.00", "rpm"),
                                    ("d_DrumLD", "L/D", "LD", "0.00", ""),
                                    ("d_DrumPass", "Passes all checks (1/0)", "PassAll", "0", ""),
                                    ("d_DrumGasTerm", "F&M gas drag term", "GasTerm", "0.00", "min")):
        w.put(nm, lab, f"=IF(d_Forced=1,dr_F_{key},dr_D_{key})", unit, fmt)
    w.put("d_DrumSize", "Recommended drum",
          '=IF(d_DrumD>0,TEXT(d_DrumD,"0")&" ft dia x "&TEXT(d_DrumL,"0")&" ft long","NONE PASSES")', "", "@")
    w.put("d_DrumNext", "Next size up",
          '=IF(AND(d_Forced=0,dr_D_NextD>0),TEXT(dr_D_NextD,"0")&" ft x "&TEXT(dr_D_NextL,"0")&" ft","-")', "", "@")
    w.put("d_DrumAlt", "Smaller alternate (slightly over target velocity)",
          '=IF(AND(d_Forced=0,dr_D_AltD>0),TEXT(dr_D_AltD,"0")&" ft x "&TEXT(dr_D_AltL,"0")&" ft","-")', "", "@")
    w.put("d_DrumAlternates", "Pass B and C drums alternate (1/0)",
          "=IF(AND(d_Forced=0,d_UAon=1,dr_B_D>0,dr_C_D>0,OR(dr_B_D<>dr_C_D,dr_B_L<>dr_C_L)),1,0)", "", "0",
          "each drum's shell loss selects the other: the larger diameter is kept (pass D)")

    # ---- air system
    w.section("h. Air system")
    w.put("d_VConvey", "Minimum conveying velocity", "=a_ConvCoeff*SQRT(p_RhoDry)*a_ConvFactor", "FPM", "#,##0")

    def duct(nm, lab, acfm, convey=False):
        w.put(f"{nm}_acfm", f"{lab}: ACFM", f"={acfm}", "ACFM", "#,##0")
        w.put(f"{nm}_dx", f"{lab}: exact diameter", f"=SQRT(4*{nm}_acfm/(PI()*a_DuctV))*12", "in", "0.0")
        rnd = f"MAX(a_DuctInc,ROUND({nm}_dx/a_DuctInc,0)*a_DuctInc)"
        if convey:
            vmax = f"MAX(a_DuctInc,FLOOR(SQRT(4*{nm}_acfm/(PI()*d_VConvey))*12/a_DuctInc,1)*a_DuctInc)"
            w.put(f"{nm}_d", f"{lab}: diameter", f'=IF(a_Conveyed="Yes",MIN({rnd},{vmax}),{rnd})', "in", "0.0")
        else:
            w.put(f"{nm}_d", f"{lab}: diameter", f"={rnd}", "in", "0.0")
        w.put(f"{nm}_v", f"{lab}: velocity", f"={nm}_acfm/(PI()*({nm}_d/12)^2/4)", "FPM", "#,##0")

    duct("du_in", "Duct furnace to drum", "x_sIN_acfm")
    duct("du_dc", "Duct drum to cyclone", "x_sEX_acfm", convey=True)
    duct("du_st", "Duct stack", "x_sST_acfm")
    duct("du_rc", "Duct recycle", "x_sRC_acfm")
    w.put("d_ConveyOK", "Air conveying check (1/0)",
          '=IF(a_Conveyed="Yes",IF(AND(d_GasToProduct>=a_MinRatio,du_dc_v>=d_VConvey),1,0),1)', "", "0")
    w.put("d_FanP", "Fan inlet pressure", "=d_Psite+a_FanStatic*k_INWC", "psia", "0.000")
    w.put("d_FanACFM", "Fan ACFM", "=x_sEX_mol*k_R*(r_Texh+459.67)/d_FanP/60", "ACFM", "#,##0",
          si=("X*1.699011", "Am3/h"))
    w.put("d_FanRho", "Gas density at fan", "=x_sEX_lb/60/d_FanACFM", "lb/ft3", "0.00000")
    w.put("d_RhoCold", "Ambient air density (cold start)",
          "=d_Psite*(d_MWair*(1+s_W)/(1+s_W*d_MWair/mw_H2O))/(k_R*(s_Tamb+459.67))", "lb/ft3", "0.00000")
    w.put("d_SPop", "SP at operating density", '=IF(a_SPbasis="standard_air",a_SP*d_FanRho/k_AMCA,a_SP)',
          "in. w.c.", "0.00", si=("X*249.08", "Pa"))
    w.put("d_SPstd", "SP at standard air", "=d_SPop*k_AMCA/d_FanRho", "in. w.c.", "0.00")
    w.put("d_SPcold", "SP at cold start", "=d_SPstd*d_RhoCold/k_AMCA", "in. w.c.", "0.00")
    w.put("d_BHPop", "Fan BHP, hot", "=d_FanACFM*d_SPop/(6356*a_FanEff)", "HP", "0.0", si=("X*0.7457", "kW"))
    w.put("d_BHPcold", "Fan BHP, cold start", "=d_FanACFM*d_SPcold/(6356*a_FanEff)", "HP", "0.0")
    w.put("d_Motor", "Fan motor (NEMA)", '=_xlfn.MINIFS(t_NEMA,t_NEMA,">="&IF(a_VFD="Yes",d_BHPop,'
                                         'MAX(d_BHPop,d_BHPcold))-0.000000001)', "HP", "0")
    w.put("d_SheetHP", "Old sheet method HP (comparison only)", "=d_FanACFM*18*5.2/33000*1.75", "HP", "0.0")

    # ---- handoffs
    w.section("i. Feed and discharge handoffs (design = operating x design factor)")
    w.put("h_InLb", "Infeed airlock / screw", "=d_DrumIn*r_DesignFactor", "lb/hr", "#,##0")
    w.put("h_InFt3", "Infeed airlock / screw volume", "=d_DrumIn/p_RhoWet*r_DesignFactor", "ft3/hr", "#,##0")
    w.put("h_OutLb", "Discharge airlock / screw", "=d_DrumOut*r_DesignFactor", "lb/hr", "#,##0")
    w.put("h_OutFt3", "Discharge airlock / screw volume", "=d_DrumOut/p_RhoDry*r_DesignFactor", "ft3/hr", "#,##0")
    w.put("h_FuelFt3", "Solid fuel feed volume", '=IF(d_FuelKind="solid",d_mf/f_Density*r_DesignFactor,0)', "ft3/hr",
          "#,##0.0")
    w.put("h_CycACFM", "Cyclone / baghouse inlet", "=x_sEX_acfm", "ACFM", "#,##0")

    # ---- checks
    w.section("Checks (text appears when the check is not met)")
    checks = [
        ("ck_Ult", '=IF(AND(d_IsGas=0,ABS(d_UltSum-100)>0.5),"Fuel ultimate analysis sums to "&TEXT(d_UltSum,"0.00")'
                   '&"%, not 100%.","")'),
        ("ck_Gas", '=IF(AND(d_IsGas=1,ABS(d_GasSum-100)>0.5),"Gas composition sums to "&TEXT(d_GasSum,"0.00")&"%.","")'),
        ("ck_N", '=IF(AND(d_IsWood=1,f_uN>1),"Wood fuel nitrogen "&TEXT(f_uN,"0.00")&"% is unrealistic (0.1 to 0.5%).","")'),
        ("ck_HV", '=IF(ABS(d_HVdev)>5,"Entered heating value is "&TEXT(d_HVdev,"0.0")&"% from the analysis LHV.","")'),
        ("ck_Wood", '=IF(AND(d_IsWood=1,OR(d_LHVdryBack>8600,d_LHVdryBack<7400)),"Wood LHV back to dry basis "&'
                    'TEXT(d_LHVdryBack,"#,##0")&" BTU/lb is outside 7,400 to 8,600.","")'),
        ("ck_Dil", '=IF(d_md<0,"Inlet temperature is not reachable at this excess air (dilution air negative).","")'),
        ("ck_Flame", '=IF(r_Tin>d_Tflame,"Inlet temperature is above the flame temperature.","")'),
        ("ck_ProdT", '=IF(p_ProdT>p_MaxT,"Product temperature exceeds the material limit.","")'),
        ("ck_ProdEx", '=IF(p_ProdT>r_Texh,"Product leaves hotter than the exhaust gas: confirm where exhaust '
                      'temperature is measured.","")'),
        ("ck_Dew", '=IF(d_DewMargin<r_DewMargin,"Exhaust only "&TEXT(d_DewMargin,"0")&" F above its dew point.","")'),
        ("ck_Spec", '=IF(OR(d_BtuLb<1400,d_BtuLb>1900),"Specific heat "&TEXT(d_BtuLb,"#,##0")&" BTU/lb water is '
                    'outside the typical 1,400 to 1,900.","")'),
        ("ck_Drum", '=IF(d_DrumD=0,"No standard drum passes every check: raise inlet temperature or split the '
                    'duty.",IF(d_DrumPass=0,"The forced drum fails a check.",""))'),
        ("ck_Long", '=IF(d_DrumL>r_Lnormal,"Drum is longer than the normal "&TEXT(r_Lnormal,"0")&" ft.","")'),
        ("ck_Changed", '=IF(d_DrumAlternates=1,"Shell loss makes two drums alternate: the larger diameter is kept with '
                       'its own shell loss.","")'),
        ("ck_Kept", '=IF(AND(d_DrumAlternates=1,dr_D_PassAll=0),"The kept drum fails a check at its own gas flow.","")'),
        ("ck_Convey", '=IF(d_ConveyOK=0,"Air conveying check not met (gas ratio or duct velocity).","")'),
        ("ck_Fire", '=IF(AND(p_Fire="high",r_Tin>k_FireT),"High fire risk material above "&TEXT(k_FireT,"#,##0")&'
                    '" F inlet.","")'),
        ("ck_FM", '=IF(AND(d_DrumD>0,d_DrumGasTerm>d_DrumRes),"Residence time correlation outside its data (gas '
                  'drag): confirm with test data.","")'),
        ("ck_Range", '=IF(COUNTIF(Inputs!$I$1:$I$200,"OUT OF RANGE")>0,COUNTIF(Inputs!$I$1:$I$200,"OUT OF RANGE")'
                     '&" input(s) out of range on the Inputs sheet.","")'),
    ]
    crit = "+".join(f'(em_{k}_pte>=em_Major)*1' for k in ("NOx", "CO", "SO2", "PM", "VOC"))
    checks.append(("ck_PTE", f'=IF(({crit})>0,"Potential to emit is at or above "&TEXT(em_Major,"0")&" tpy for one or '
                             f'more pollutants: see the Emissions sheet.","")'))
    assert len(checks) == N_CHECKS, len(checks)
    ck0 = w.r
    for nm, f in checks:
        w.put(nm, nm.replace("ck_", "Check: "), f, "", "@")
    bk.name("ck_All", calc, f"$C${ck0}:$C${w.r - 1}")
    w.put("d_Warnings", "Active warnings", '=_xlfn.TEXTJOIN(" | ",TRUE,ck_All)', "", "@")
    w.put("d_WarnCount", "Number of active warnings", '=SUMPRODUCT(--(ck_All<>""))', "", "0")
    calc.freeze_panes = "C6"
    return calc, gas


# --------------------------------------------------------------------------------------- Drum
DRUM_COLS = ["D", "L", "Area", "Vol", "Shell", "Nc", "N", "G", "Fs", "GasTerm", "ThetaFill", "Theta", "Slope",
             "Holdup", "Fill", "Vel", "VER", "LD", "okVER", "okVel", "okEnt", "okFill", "okSlope", "okSpeed", "okLD",
             "PassAll", "Above", "PassT", "VolT"]


def _drum_rows(ws, r0, sizes, pfx, duty):
    """Write candidate rows; duty = dict(acfm=, gin=, gout=) names."""
    C = {k: 2 + i for i, k in enumerate(DRUM_COLS)}
    for j, k in enumerate(DRUM_COLS):
        c = ws.cell(r0 - 1, 2 + j, k)
        c.font = _font(8, True, WHITE)
        c.fill = _fill(BLACK)
    for i, (d, l) in enumerate(sizes):
        r = r0 + i
        L = lambda k: f"{CL(C[k])}{r}"  # noqa: E731
        ws.cell(r, C["D"], d)
        ws.cell(r, C["L"], l)
        f = {
            "Area": f"=PI()*{L('D')}^2/4", "Vol": f"={L('Area')}*{L('L')}", "Shell": f"=PI()*{L('D')}*{L('L')}",
            "Nc": f"=60/(2*PI())*SQRT(2*k_g/{L('D')})", "N": f"=r_Crit/100*{L('Nc')}",
            "G": f"=0.5*({duty['gin']}+{duty['gout']})/{L('Area')}", "Fs": f"=d_DrumSolids/{L('Area')}",
            "GasTerm": f"=0.6*dr_B*{L('L')}*{L('G')}/{L('Fs')}",
            "ThetaFill": f"=r_FillMin/100*{L('Vol')}*dr_RhoAvg/dr_FlowAvg",
            "Theta": f"=MAX(p_Residence,{L('ThetaFill')})",
            "Slope": f"=0.23*{L('L')}/({L('N')}^0.9*{L('D')}*({L('Theta')}+{L('GasTerm')}))*12",
            "Holdup": f"=dr_FlowAvg*{L('Theta')}", "Fill": f"={L('Holdup')}/dr_RhoAvg/{L('Vol')}*100",
            "Vel": f"={duty['acfm']}/({L('Area')}*(1-MIN({L('Fill')},50)/100))",
            "VER": f"=d_Evap/{L('Vol')}", "LD": f"={L('L')}/{L('D')}",
            "okVER": f"=IF({L('VER')}<=p_VERmax+1E-9,1,0)",
            "okVel": f"=IF({L('Vel')}<=r_Vtarget*(1+r_Vtol/100)+1E-9,1,0)",
            "okEnt": f'=IF(OR(a_Conveyed="Yes",{L("Vel")}<=r_EntFrac*{duty["ut"]}*60),1,0)',
            "okFill": f"=IF(AND({L('Fill')}>=r_FillMin-1E-9,{L('Fill')}<=r_FillMax+1E-9),1,0)",
            "okSlope": f"=IF(AND({L('Slope')}>=r_SlopeMin-1E-9,{L('Slope')}<=r_SlopeMax+1E-9),1,0)",
            "okSpeed": "=IF(AND(r_Crit>=r_CritMin,r_Crit<=r_CritMax),1,0)",
            "okLD": f"=IF(AND({L('LD')}>=r_LDmin-1E-9,{L('LD')}<=r_LDmax+1E-9),1,0)",
            "PassAll": f"={L('okVER')}*{L('okVel')}*{L('okEnt')}*{L('okFill')}*{L('okSlope')}*{L('okSpeed')}*{L('okLD')}",
            "Above": f"=IF({L('Vel')}>r_Vtarget+1E-9,1,0)",
            "PassT": f"={L('PassAll')}*(1-{L('Above')})",
            "VolT": f'=IF({L("PassT")}=1,{L("Vol")},"")',
        }
        for k, v in f.items():
            cell = ws.cell(r, C[k], v)
            cell.number_format = "0.000" if k not in ("Vol", "Area", "Shell", "Holdup", "Vel") else "#,##0.0"
    rN = r0 + len(sizes) - 1
    return C, rN


def build_drum(bk: Book):
    ws = bk.sheet("Drum")
    for c in range(1, 34):
        ws.column_dimensions[CL(c)].width = 10
    ws.column_dimensions["B"].width = 30
    ws.cell(1, 2, "Drum: standard drum candidates (Friedman & Marshall 1949 residence time; Haider & Levenspiel 1989 "
                  "terminal velocity)").font = _font(12, True, head=True)
    # common constants
    r = 3
    rows = [("dr_B", "F&M B = 5 Dp^-0.5 (Dp microns)", "=5*(p_Dp*25400)^-0.5"),
            ("dr_FlowAvg", "Average solids + water flow", "=0.5*(d_DrumIn+d_DrumOut)/60"),
            ("dr_RhoAvg", "Average bulk density", "=0.5*(p_RhoWet+p_RhoDry)"),
            ("dr_Mu", "Gas viscosity (Sutherland, air)",
             "=1.716E-05*(((r_Texh+459.67)/1.8)/273.15)^1.5*(273.15+110.4)/(((r_Texh+459.67)/1.8)+110.4)*0.67196897514"),
            ("dr_dft", "Particle diameter", "=p_Dp/12"),
            ("dr_HA", "H&L A", "=EXP(2.3288-6.4581*p_Phi+2.4486*p_Phi^2)"),
            ("dr_HB", "H&L B", "=0.0964+0.5565*p_Phi"),
            ("dr_HC", "H&L C", "=EXP(4.905-13.8944*p_Phi+18.4222*p_Phi^2-10.2599*p_Phi^3)"),
            ("dr_HD", "H&L D", "=EXP(1.4681+12.2584*p_Phi-20.7322*p_Phi^2+15.8855*p_Phi^3)")]
    for nm, lab, f in rows:
        ws.cell(r, 2, lab)
        ws.cell(r, 3, f).number_format = "0.000000"
        bk.name(nm, ws, _abs(3, r))
        r += 1
    # terminal velocity: fixed-point iteration, one column per pass (each pass uses its own exhaust density)
    ws.cell(r, 2, "Terminal velocity iteration (ft/s), pass A / B / C / D").font = _font(9, True)
    r += 1
    ws.cell(r, 2, "Exhaust gas density")
    for j, p in enumerate("ABCD"):
        ws.cell(r, 3 + 2 * j, f"=d_GoutMass_{p}/60/d_ACFM_{p}").number_format = "0.00000"
        bk.name(f"dr_RhoG_{p}", ws, _abs(3 + 2 * j, r))
    r += 1
    it0 = r
    for i in range(40):
        rr = it0 + i
        for j, p in enumerate("ABCD"):
            uc, cc = CL(3 + 2 * j), CL(4 + 2 * j)
            rho = f"dr_RhoG_{p}"
            if i == 0:
                ws.cell(rr, 3 + 2 * j, 5.0)
            else:
                ws.cell(rr, 3 + 2 * j, f"=0.5*({uc}{rr - 1}+SQRT(4*k_g*dr_dft*(p_RhoP-{rho})/(3*{cc}{rr - 1}*{rho})))")
            re = f"MAX({rho}*{uc}{rr}*dr_dft/dr_Mu,1E-12)"
            ws.cell(rr, 4 + 2 * j, f"=24/{re}*(1+dr_HA*{re}^dr_HB)+dr_HC/(1+dr_HD/{re})")
        ws.row_dimensions[rr].hidden = i not in (0, 39)
    for j, p in enumerate("ABCD"):
        bk.name(f"dr_Ut_{p}", ws, _abs(3 + 2 * j, it0 + 39))
    ws.cell(it0 + 39, 2, "Terminal velocity, converged (ft/s)")
    r = it0 + 41
    sizes = [(d, l) for d in STANDARD_DRUM_DIAMETERS_FT for l in STANDARD_DRUM_LENGTHS_FT]
    nL = len(STANDARD_DRUM_LENGTHS_FT)
    for p in ("A", "B", "C", "D"):
        ws.cell(r, 2, f"Pass {p}: shell loss from "
                      + {"A": "none", "B": "the pass A drum", "C": "the pass B drum",
                         "D": "the pass C drum, or the kept drum when B and C alternate (final)"}[p]).font = \
            _font(10, True, ORANGE, head=True)
        sel0 = r + 1
        top = sel0 + 8
        Cc, rN = _drum_rows(ws, top + 1, sizes, p,
                            {"acfm": f"d_ACFM_{p}", "gin": f"d_GinMass_{p}", "gout": f"d_GoutMass_{p}",
                             "ut": f"dr_Ut_{p}"})
        rng = lambda k: f"${CL(Cc[k])}${top + 1}:${CL(Cc[k])}${rN}"  # noqa: E731
        lrng = f"${CL(Cc['L'])}${top + 1}:${CL(Cc['L'])}${top + nL}"
        if p == "D":
            sel = [("VolMin", f"=_xlfn.MINIFS({rng('Vol')},{rng('PassT')},1)"),
                   ("Row", f"=IF(d_DrumAlternates=1,MATCH(dr_Z_D,{rng('D')},0)+MATCH(dr_Z_L,{lrng},0)-1,"
                           f"IF(dr_D_VolMin>0,MATCH(dr_D_VolMin,{rng('VolT')},0),0))"),
                   ("VolRec", f"=IF(dr_D_Row>0,INDEX({rng('Vol')},dr_D_Row),0)")]
        else:
            sel = [("VolRec", f"=_xlfn.MINIFS({rng('Vol')},{rng('PassT')},1)"),
                   ("Row", f"=IF(dr_{p}_VolRec>0,MATCH(dr_{p}_VolRec,{rng('VolT')},0),0)")]
        sel += [
                ("D", f"=IF(dr_{p}_Row>0,INDEX({rng('D')},dr_{p}_Row),0)"),
                ("L", f"=IF(dr_{p}_Row>0,INDEX({rng('L')},dr_{p}_Row),0)"),
                ("Shell", f"=PI()*dr_{p}_D*dr_{p}_L"),
                ("NextVol", f"=IF(dr_{p}_VolRec>0,_xlfn.MINIFS({rng('Vol')},{rng('PassT')},1,{rng('Vol')},"
                            f"\">\"&dr_{p}_VolRec*1.0001),0)"),
                ("AltVol", f"=_xlfn.MINIFS({rng('Vol')},{rng('PassAll')},1,{rng('Above')},1,{rng('Vol')},"
                           f"\"<\"&IF(dr_{p}_VolRec>0,dr_{p}_VolRec*0.9999,1E+99))")]
        for i, (k, f) in enumerate(sel):
            ws.cell(sel0 + i, 2, f"Pass {p} {k}")
            ws.cell(sel0 + i, 3, f)
            bk.name(f"dr_{p}_{k}", ws, _abs(3, sel0 + i))
        if p == "D":
            ws.cell(sel0, 5, "Next D")
            ws.cell(sel0, 6, f"=IF(dr_D_NextVol>0,INDEX({rng('D')},MATCH(dr_D_NextVol,{rng('VolT')},0)),0)")
            ws.cell(sel0 + 1, 5, "Next L")
            ws.cell(sel0 + 1, 6, f"=IF(dr_D_NextVol>0,INDEX({rng('L')},MATCH(dr_D_NextVol,{rng('VolT')},0)),0)")
            ws.cell(sel0 + 2, 5, "Alt D")
            ws.cell(sel0 + 2, 6, f"=IF(dr_D_AltVol>0,INDEX({rng('D')},MATCH(dr_D_AltVol,{rng('Vol')},0)),0)")
            ws.cell(sel0 + 3, 5, "Alt L")
            ws.cell(sel0 + 3, 6, f"=IF(dr_D_AltVol>0,INDEX({rng('L')},MATCH(dr_D_AltVol,{rng('Vol')},0)),0)")
            for i, k in enumerate(["NextD", "NextL", "AltD", "AltL"]):
                bk.name(f"dr_D_{k}", ws, _abs(6, sel0 + i))
            # kept drum when the pass B and C drums alternate: the larger diameter (then length)
            ws.cell(sel0 + 6, 5, "Kept D")
            ws.cell(sel0 + 6, 6, "=IF(d_DrumAlternates=1,IF(OR(dr_B_D>dr_C_D,AND(dr_B_D=dr_C_D,dr_B_L>dr_C_L)),dr_B_D,"
                                 "dr_C_D),dr_C_D)")
            ws.cell(sel0 + 7, 5, "Kept L")
            ws.cell(sel0 + 7, 6, "=IF(d_DrumAlternates=1,IF(OR(dr_B_D>dr_C_D,AND(dr_B_D=dr_C_D,dr_B_L>dr_C_L)),dr_B_L,"
                                 "dr_C_L),dr_C_L)")
            bk.name("dr_Z_D", ws, _abs(6, sel0 + 6))
            bk.name("dr_Z_L", ws, _abs(6, sel0 + 7))
            # selected drum metrics
            mrow = sel0 + 4
            for j, k in enumerate(["VER", "Vel", "Theta", "Fill", "Slope", "N", "Nc", "LD", "PassAll", "GasTerm"]):
                ws.cell(mrow + (j // 5), 5 + 2 * (j % 5), k)
                ws.cell(mrow + (j // 5), 6 + 2 * (j % 5), f"=IF(dr_D_Row>0,INDEX({rng(k)},dr_D_Row),0)")
                bk.name(f"dr_D_{k}", ws, _abs(6 + 2 * (j % 5), mrow + (j // 5)))
        r = rN + 3
    # forced drum row
    ws.cell(r, 2, "Forced drum (Inputs: force diameter and length)").font = _font(10, True, ORANGE, head=True)
    Cf, rN = _drum_rows(ws, r + 2, [(0, 0)], "F", {"acfm": "d_ACFM_D", "gin": "d_GinMass_D", "gout": "d_GoutMass_D",
                                                         "ut": "dr_Ut_D"})
    ws.cell(r + 2, Cf["D"], "=MAX(r_ForceD,1)")
    ws.cell(r + 2, Cf["L"], "=MAX(r_ForceL,1)")
    for k in ["VER", "Vel", "Theta", "Fill", "Slope", "N", "Nc", "LD", "PassAll", "GasTerm"]:
        bk.name(f"dr_F_{k}", ws, _abs(Cf[k], r + 2))
    ws.freeze_panes = "C3"
    return ws


# --------------------------------------------------------------------------------------- Diagram
COLW = 3.4  # character units -> about 24 px
ROWH = 15.0  # points = 20 px
PX_PER_COL = 24
PX_PER_ROW = 20
EMU_PX = 9525


def _img(ws, path, col, row, w_px, h_px, dx_px=0, dy_px=0):
    img = XLImage(str(path))
    marker = AnchorMarker(col=col - 1, colOff=int(dx_px * EMU_PX), row=row - 1, rowOff=int(dy_px * EMU_PX))
    img.anchor = OneCellAnchor(_from=marker, ext=XDRPositiveSize2D(int(w_px * EMU_PX), int(h_px * EMU_PX)))
    ws.add_image(img)


def _hline(ws, row, c1, c2, color, style="medium"):
    """Line along the bottom edge of `row` from column c1 to c2 inclusive."""
    for c in range(c1, c2 + 1):
        cell = ws.cell(row, c)
        b = cell.border
        cell.border = Border(left=b.left, right=b.right, top=b.top, bottom=Side(style=style, color=color))


def _vline(ws, col, r1, r2, color, style="medium"):
    """Line along the left edge of `col` from row r1 to r2 inclusive."""
    for r in range(r1, r2 + 1):
        cell = ws.cell(r, col)
        b = cell.border
        cell.border = Border(left=Side(style=style, color=color), right=b.right, top=b.top, bottom=b.bottom)


def _arrow(ws, kind, color, col, row):
    """Arrowhead with its TIP at the point (left edge of `col`, bottom edge of `row`), the end of a border line.
    Diagram rows from 6 down are all PX_PER_ROW tall and every column PX_PER_COL wide."""
    s_ = 14
    px = (col - 1) * PX_PER_COL
    py = (row - 5) * PX_PER_ROW  # measured from the top of row 6
    x0, y0 = {"right": (px - s_, py - s_ / 2), "left": (px, py - s_ / 2), "down": (px - s_ / 2, py - s_),
              "up": (px - s_ / 2, py)}[kind]
    c = int(x0 // PX_PER_COL) + 1
    r = int(y0 // PX_PER_ROW) + 6
    _img(ws, ASSETS / f"arrow_{kind}_{color}.png", c, r, s_, s_, dx_px=x0 - (c - 1) * PX_PER_COL,
         dy_px=y0 - (r - 6) * PX_PER_ROW)


def _box(ws, col, row, width, title, lines):
    """Data box: black title bar + rows of (value formula, unit). Returns last row."""
    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col + width - 1)
    t = ws.cell(row, col, title)
    t.font = _font(8.5, True, WHITE, head=True)
    t.fill = _fill(BLACK)
    t.alignment = Alignment(horizontal="center", vertical="center")
    for c in range(col, col + width):
        ws.cell(row, c).fill = _fill(BLACK)
    # orange tab under the title
    for i, (val, unit, fmt) in enumerate(lines):
        r = row + 1 + i
        vw = width // 2 + (width % 2)
        ws.merge_cells(start_row=r, start_column=col, end_row=r, end_column=col + vw - 1)
        v = ws.cell(r, col, val)
        v.number_format = fmt
        v.font = _font(9, True)
        v.alignment = Alignment(horizontal="right", vertical="center")
        ws.merge_cells(start_row=r, start_column=col + vw, end_row=r, end_column=col + width - 1)
        u = ws.cell(r, col + vw, unit)
        u.font = _font(7.5, color=STEEL)
        u.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        for c in range(col, col + width):
            ws.cell(r, c).fill = _fill(WHITE)
    last = row + len(lines)
    # outline
    for r in range(row, last + 1):
        for c in range(col, col + width):
            cell = ws.cell(r, c)
            cell.border = Border(left=BOX if c == col else None, right=BOX if c == col + width - 1 else None,
                                 top=Side(style="thin", color=STEEL) if r == row else None,
                                 bottom=Side(style="medium", color=ORANGE) if r == row else
                                 (BOX if r == last else None))
    return last


def build_diagram(bk: Book):
    ws = bk.wb.create_sheet("Mass-Energy Balance", 0)
    ws.sheet_view.showGridLines = False
    ncol = 46
    for c in range(1, ncol + 1):
        ws.column_dimensions[CL(c)].width = COLW
    for r in range(1, 75):
        ws.row_dimensions[r].height = ROWH
    for r in range(1, 75):
        for c in range(1, ncol + 1):
            ws.cell(r, c).font = _font(9)

    # header band
    for r in range(1, 5):
        ws.row_dimensions[r].height = 18
        for c in range(1, ncol + 1):
            ws.cell(r, c).fill = _fill(BLACK)
    _img(ws, ASSETS / "mce_logo_520.png", 2, 1, 236, 72, dx_px=0, dy_px=4)
    ws.merge_cells(start_row=1, start_column=18, end_row=2, end_column=ncol - 1)
    c = ws.cell(1, 18, "DEHYDRATION SYSTEM MASS-ENERGY BALANCE")
    c.font = Font(name=HEAD_FONT, size=18, bold=True, color=WHITE)
    c.alignment = Alignment(horizontal="right", vertical="center")
    ws.merge_cells(start_row=3, start_column=18, end_row=3, end_column=ncol - 1)
    c = ws.cell(3, 18, '="Rotary drum dryer  |  "&IF(j_Case="","Case 1",j_Case)')
    c.font = Font(name=HEAD_FONT, size=11, bold=True, color=ORANGE)
    c.alignment = Alignment(horizontal="right", vertical="center")
    ws.merge_cells(start_row=4, start_column=18, end_row=4, end_column=ncol - 1)
    c = ws.cell(4, 18, '="Prepared for "&IF(j_Customer="","-",j_Customer)&"   |   Job "&IF(j_Job="","-",j_Job)'
                       '&"   |   "&IF(j_Date="",TEXT(TODAY(),"m/d/yyyy"),j_Date)&"   |   Prepared by "&'
                       'IF(j_PreparedBy="","MCE",j_PreparedBy)')
    c.font = Font(name=BODY_FONT, size=8, color=SILVER)
    c.alignment = Alignment(horizontal="right", vertical="center")
    ws.row_dimensions[5].height = 4
    for cc in range(1, ncol + 1):
        ws.cell(5, cc).fill = _fill(ORANGE)

    # case lines
    def text(r, c, f, size=10, bold=False, color="000000", merge=14, align="left"):
        ws.merge_cells(start_row=r, start_column=c, end_row=r, end_column=c + merge - 1)
        cell = ws.cell(r, c, f)
        cell.font = _font(size, bold, color)
        cell.alignment = Alignment(horizontal=align, vertical="center")
        return cell

    text(7, 2, '=TEXT(d_Wet/2000,"0.00")&" TPH wet "&LOWER(p_Material)', 11, True, merge=20)
    text(8, 2, '=TEXT(p_MCin,"0.0")&"% to "&TEXT(p_MCout,"0.0")&"% moisture (wet basis), "&TEXT(p_ProdT,"0")&'
               '" F product"', 9, merge=20)
    text(9, 2, '=IF(d_DrumD>0,d_DrumSize&" MCE rotary drum dryer","Drum: see warnings")', 10, True, merge=20)
    text(10, 2, '="Elevation "&TEXT(s_Elev,"#,##0")&" ft  |  ambient "&TEXT(s_Tamb,"0")&" F  |  "&'
                'TEXT(d_Psite,"0.00")&" psia"', 8, color=STEEL, merge=20)

    # ---------------- equipment images
    _img(ws, ASSETS / "burner.png", 6, 20, 150, 105)
    _img(ws, ASSETS / "drum.png", 20, 19, 230, 115)
    _img(ws, ASSETS / "cyclone.png", 34, 17, 85, 235)
    _img(ws, ASSETS / "fan.png", 30, 10, 76, 76)

    def label(r, c, s, merge=6, color=STEEL):
        text(r, c, s, 8, True, color, merge=merge, align="center")

    label(26, 6, "BURNER", 7)
    label(26, 21, "=IF(d_DrumD>0,d_DrumSize,\"ROTARY DRUM DRYER\")", 9, BLACK)
    label(27, 21, "ROTARY DRUM DRYER", 9)
    label(25, 37, "CYCLONE", 4)
    label(14, 30, "DRYER FAN", 4)

    # ---------------- boxes
    _box(ws, 2, 12, 7, '=INDEX(fu_short,MATCH(f_Fuel,fu_label,0))', [
        ("=d_LHV", "BTU/lb net", "#,##0"),
        ('=IF(d_IsGas=1,d_FuelSCFH,d_mf)', '=IF(d_IsGas=1,"SCFH","lb/hr")', "#,##0"),
        ("=d_BurnerOp", "MMBtu/hr", "0.00")])
    _box(ws, 2, 29, 7, "Combustion Air", [
        ("=x_sCA_scfm", "SCFM", "#,##0"), ("=s_Tamb", "deg F", "0"), ("=f_EA", "% excess air", "0")])
    _box(ws, 11, 12, 6, "Make-Up Air", [("=x_sDA_scfm", "SCFM", "#,##0"), ("=s_Tamb", "deg F", "0")])
    _box(ws, 18, 12, 7, "Mixed Inlet Gases", [
        ("=x_sIN_scfm", "SCFM", "#,##0"), ("=x_sIN_acfm", "ACFM", "#,##0"), ("=r_Tin", "deg F", "0")])
    _box(ws, 17, 30, 7, "Wet Feed", [
        ("=p_MCin/100", "moisture", "0.00%"), ("=d_Solids", "lb/hr solids", "#,##0"),
        ("=d_WaterIn", "lb/hr water", "#,##0"), ("=d_Wet", "lb/hr total", "#,##0")])
    _box(ws, 39, 7, 7, "Exhaust Gases", [("=x_sST_acfm", "ACFM", "#,##0"), ("=d_BHPop", "fan BHP", "0.0")])
    _box(ws, 39, 12, 7, "Dryer Outlet Gases", [
        ("=x_sEX_acfm", "ACFM", "#,##0"), ("=r_Texh", "deg F", "0"), ("=d_Tdew", "dew point F", "0")])
    _box(ws, 35, 31, 7, "Dry Material", [
        ("=p_MCout/100", "moisture", "0.00%"), ("=d_Solids", "lb/hr solids", "#,##0"),
        ("=d_WaterOut", "lb/hr water", "#,##0"), ("=d_Product", "lb/hr total", "#,##0"),
        ("=p_ProdT", "deg F", "0")])
    _box(ws, 27, 31, 6, '=IF(d_SelfFuel=1,"Dry Fuel to Burner","Fuel to Burner")', [
        ('=IF(d_IsGas=1,d_FuelSCFH,d_mf)', '=IF(d_IsGas=1,"SCFH","lb/hr")', "#,##0")])
    _box(ws, 27, 34, 6, "Net Dry Product", [("=d_NetProduct", "lb/hr", "#,##0")])

    # evaporation call-out
    ws.merge_cells(start_row=28, start_column=25, end_row=28, end_column=31)
    c = ws.cell(28, 25, "EVAPORATION RATE")
    c.font = _font(8, True, STEEL, head=True)
    c.alignment = Alignment(horizontal="center")
    ws.merge_cells(start_row=29, start_column=25, end_row=29, end_column=31)
    c = ws.cell(29, 25, '=TEXT(d_Evap,"#,##0")&" lb/hr H2O"')
    c.font = _font(11, True)
    c.alignment = Alignment(horizontal="center")
    ws.merge_cells(start_row=30, start_column=25, end_row=30, end_column=31)
    c = ws.cell(30, 25, '=TEXT(d_BtuLb,"#,##0")&" BTU/lb water"')
    c.font = Font(name=HEAD_FONT, size=12, bold=True, color=ORANGE)
    c.alignment = Alignment(horizontal="center")

    # ---------------- flow lines (cell borders) and arrows; see _arrow for the tip geometry
    hot, mat, exh = ORANGE, BLACK, STEEL
    # fuel: down from the fuel box into the burner fuel port
    _vline(ws, 8, 16, 19, mat)
    _arrow(ws, "down", "black", 8, 19)
    # combustion air: up from its box, right into the burner
    _vline(ws, 4, 23, 28, hot)
    _hline(ws, 22, 4, 5, hot)
    _arrow(ws, "right", "orange", 6, 22)
    # hot gas: burner outlet to the drum inlet breeching
    _hline(ws, 21, 12, 19, hot)
    _arrow(ws, "right", "orange", 20, 21)
    # make-up air joins the hot gas duct
    _vline(ws, 14, 15, 21, hot)
    _arrow(ws, "down", "orange", 14, 21)
    # mixed inlet gas call-out
    _vline(ws, 18, 16, 21, STEEL, "thin")
    _arrow(ws, "down", "steel", 18, 21)
    # wet feed up into the drum inlet
    _vline(ws, 21, 25, 29, mat)
    _arrow(ws, "up", "black", 21, 24)
    # drum discharge to the cyclone tangential inlet
    _hline(ws, 21, 29, 31, mat)
    _vline(ws, 32, 19, 21, mat)
    _hline(ws, 18, 32, 33, mat)
    _arrow(ws, "right", "black", 34, 18)
    # cyclone outlet up and left to the fan
    _vline(ws, 36, 13, 16, exh)
    _hline(ws, 12, 33, 35, exh)
    _arrow(ws, "left", "steel", 33, 12)
    # fan outlet up and right to the stack
    _vline(ws, 32, 8, 9, exh)
    _hline(ws, 7, 32, 38, exh)
    _arrow(ws, "right", "steel", 39, 7)
    # cyclone airlock down into the dry material box
    _vline(ws, 36, 29, 30, mat)
    _arrow(ws, "down", "black", 36, 30)
    # dry material split: fuel to the burner and net product
    _hline(ws, 31, 33, 34, mat)
    _arrow(ws, "left", "black", 33, 31)
    _hline(ws, 34, 33, 34, mat)
    _arrow(ws, "left", "black", 33, 34)

    # ---------------- bottom panels
    r0 = 41
    for c in range(2, ncol):
        ws.cell(r0, c).fill = _fill(STEEL)
    ws.cell(r0, 1).fill = _fill(ORANGE)
    ws.cell(r0, 2, "HEAT BALANCE (LHV)").font = _font(9, True, WHITE, head=True)
    ws.cell(r0, 18, "KEY RESULTS").font = _font(9, True, WHITE, head=True)
    ws.cell(r0, 33, "NOTES").font = _font(9, True, WHITE, head=True)
    heads = [("Heat use", 2, 6), ("MMBtu/hr", 8, 3), ("%", 11, 2), ("BTU/lb water", 13, 3)]
    for h, c, m in heads:
        ws.merge_cells(start_row=r0 + 1, start_column=c, end_row=r0 + 1, end_column=c + m - 1)
        cell = ws.cell(r0 + 1, c, h)
        cell.font = _font(7.5, True)
        cell.fill = _fill(HEADER)
        cell.alignment = Alignment(horizontal="center")
        for cc in range(c, c + m):
            ws.cell(r0 + 1, cc).fill = _fill(HEADER)
    uses = [("Evaporation", "d_Qevap"), ("Solids heating", "d_Qsolids"), ("Residual water heating", "d_Qresid"),
            ("Stack (gas to exhaust temp)", "d_Qstack"), ("Shell", "d_Qshell"), ("Furnace", "d_Qfurnace"),
            ("Recycle duct", "d_Qrecduct"), ("Burner input", "d_Qfuel")]
    for i, (lab, nm) in enumerate(uses):
        r = r0 + 2 + i
        bold = nm == "d_Qfuel"
        for c, m, v, fmt in ((2, 6, lab, "@"), (8, 3, f"={nm}/1000000", "0.000"), (11, 2, f"={nm}/d_Qfuel", "0.0%"),
                             (13, 3, f"={nm}/d_Evap", "#,##0")):
            ws.merge_cells(start_row=r, start_column=c, end_row=r, end_column=c + m - 1)
            cell = ws.cell(r, c, v)
            cell.number_format = fmt
            cell.font = _font(8, bold, ORANGE if bold and c > 2 else "000000")
            cell.alignment = Alignment(horizontal="left" if c == 2 else "right")
            if bold:
                for cc in range(c, c + m):
                    ws.cell(r, cc).border = Border(top=Side(style="thin", color=STEEL))
    res = [("Burner operating (LHV)", '=TEXT(d_BurnerOp,"0.00")&" MMBtu/hr"', '=TEXT(d_BurnerOp*293.071,"#,##0")&" kW"'),
           ("Burner design rating", '=TEXT(d_BurnerDesign,"0.00")&" MMBtu/hr"',
            '=TEXT(d_BurnerDesign*293.071,"#,##0")&" kW"'),
           ("Evaporation", '=TEXT(d_Evap,"#,##0")&" lb/hr"', '=TEXT(d_Evap*0.45359237,"#,##0")&" kg/h"'),
           ("Product", '=TEXT(d_Product,"#,##0")&" lb/hr"', '=TEXT(d_Product*0.45359237,"#,##0")&" kg/h"'),
           ("Fuel", '=IF(d_IsGas=1,TEXT(d_FuelSCFH,"#,##0")&" SCFH",TEXT(d_mf,"#,##0")&" lb/hr")',
            '=TEXT(d_mf*0.45359237,"#,##0")&" kg/h"'),
           ("Dryer exhaust", '=TEXT(x_sEX_acfm,"#,##0")&" ACFM"', '=TEXT(x_sEX_acfm*1.699011,"#,##0")&" Am3/h"'),
           ("Drum", "=d_DrumSize", '=IF(d_DrumD>0,TEXT(d_DrumD*0.3048,"0.00")&" x "&TEXT(d_DrumL*0.3048,"0.0")&" m","")'),
           ("Fan motor", '=TEXT(d_Motor,"0")&" HP ("&TEXT(d_BHPop,"0.0")&" BHP hot)"',
            '=TEXT(d_Motor*0.7457,"0")&" kW"'),
           ("Annual fuel", '=TEXT(d_AnnFuel,"#,##0")&" tons/yr"', '=TEXT(d_AnnMMBtu,"#,##0")&" MMBtu/yr"'),
           ("Recycle gas", '=IF(r_Recycle>0,TEXT(r_Recycle,"0%")&" of exhaust","none")',
            '=IF(r_Recycle>0,TEXT(x_sRC_acfm,"#,##0")&" ACFM","")')]
    for i, (lab, imp, si) in enumerate(res):
        r = r0 + 1 + i
        for c, m, v, b in ((18, 5, lab, False), (23, 5, imp, True), (28, 4, si, False)):
            ws.merge_cells(start_row=r, start_column=c, end_row=r, end_column=c + m - 1)
            cell = ws.cell(r, c, v)
            cell.font = _font(8, b, STEEL if c == 28 else "000000")
            cell.alignment = Alignment(horizontal="left" if c == 18 else "right")
    ws.merge_cells(start_row=r0 + 1, start_column=33, end_row=r0 + 10, end_column=ncol - 1)
    c = ws.cell(r0 + 1, 33, '=IF(d_WarnCount=0,"No warnings.",d_Warnings)&"  Basis: LHV as fired; SCFM at 70 F, '
                            '29.92 in. Hg; ACFM at site pressure. Mass closure "&TEXT(d_CloseM,"0.0E+00")&"%, energy '
                            'closure "&TEXT(d_CloseE,"0.0E+00")&"%."')
    c.font = _font(7.5, color=STEEL)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    # footer
    fr = r0 + 12
    ws.row_dimensions[fr].height = 3
    for cc in range(1, ncol + 1):
        ws.cell(fr, cc).border = Border(top=Side(style="thin", color=SILVER))
    for cc in range(1, 5):
        ws.cell(fr, cc).fill = _fill(ORANGE)
    ws.merge_cells(start_row=fr + 1, start_column=2, end_row=fr + 1, end_column=22)
    c = ws.cell(fr + 1, 2, "MIDWEST CUSTOM ENGINEERING     PRECISION. QUALITY. INTEGRITY.")
    c.font = Font(name=HEAD_FONT, size=9, bold=True, color=STEEL)
    ws.merge_cells(start_row=fr + 1, start_column=24, end_row=fr + 1, end_column=ncol - 1)
    c = ws.cell(fr + 1, 24, f'="Sizing record "&IF(j_Record="","not saved",j_Record)&"   |   {WB_VERSION}   |   '
                            f'Page 1/1"')
    c.font = _font(7.5, color=MUTED)
    c.alignment = Alignment(horizontal="right")
    # print setup
    ws.print_area = f"A1:{CL(ncol)}{fr + 1}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    ws.page_margins.left = ws.page_margins.right = 0.3
    ws.page_margins.top = ws.page_margins.bottom = 0.3
    return ws


# --------------------------------------------------------------------------------------- Notes
NOTES = [
    ("Purpose", "Rotary drum dryer mass and energy balance, burner, drum, fan and duct sizing for Midwest Custom "
                "Engineering quotes. The Python engine (mce_engineering/equipment/dryer_calc) is the reference and "
                "this workbook is tested against it."),
    ("How to use", "Pick the material and fuel on the Inputs sheet and type into the orange ENTRY column. The "
                   "Mass-Energy Balance sheet is the customer page; print it on one landscape page."),
    ("Reference state", "32 F (0 C), 14.696 psia: liquid water h = 0; dry air and all ideal-gas species h = 0 at 32 F; "
                        "water vapor from liquid at 32 F (hfg 1,075.2 BTU/lb at the triple point). Fuel energy = "
                        "LHV as fired + latent heat of its combustion water at 32 F."),
    ("Standard conditions", "SCFM / SCFH at 70 F and 29.92 in. Hg for every gas. ACFM at the actual temperature and "
                            "the site barometric pressure (ASHRAE)."),
    ("Gas side", "At a fixed inlet temperature the furnace and drum energy balances are linear in fuel and dilution "
                 "air, solved directly (Calc section d). Shell loss U A dT depends on the drum, so three passes are "
                 "made: no shell loss, then the pass A drum, then the pass B drum. To fix exhaust ACFM or inlet gas "
                 "flow instead, use Data > What-If Analysis > Goal Seek on the inlet temperature."),
    ("Properties", "IAPWS-IF97 Region 4 (saturation, dew point); IAPWS-95 fit (liquid water); Cengel & Boles Table "
                   "A-2(c) ideal-gas cp polynomials; heats of formation Cengel Table A-26 and NIST-JANAF; Channiwala "
                   "& Parikh (2002) HHV correlation; ISO 18125 moisture correction."),
    ("Drum", "Friedman & Marshall (1949) residence time as given in Perry's Handbook Sec. 12; Haider & Levenspiel "
             "(1989) drag. 350 FPM is the MCE target drum velocity; drums up to the allowance over it appear only as "
             "a smaller alternate. Standard sizes: whole-foot diameters 3 to 13 ft, lengths 10 to 80 ft (over 60 ft "
             "flagged); placeholder grid until the MCE list is set."),
    ("Burner", "Furnace efficiency covers unburned fuel and furnace radiation only (98% gas, 93% biomass); stack loss "
               "is computed. Dry wood fuel: 8,000 BTU/lb dry basis net = 7,095 BTU/lb as fired at 10% MC, checked "
               "against a burner supplier's quoted fuel rate (internal back-check on file)."),
    ("Not in this workbook", "Dryer type selector, fixed-ACFM and fixed-gas-flow modes (use Goal Seek), inlet gas wet "
                             "bulb, sizing record storage. These run in the Python engine."),
    ("Version", WB_VERSION + "; engine " + CALC_VERSION),
]


def build_notes(bk: Book):
    ws = bk.sheet("Notes")
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 120
    ws.cell(1, 2, "Notes and method").font = _font(13, True, head=True)
    for i, (k, v) in enumerate(NOTES):
        ws.cell(3 + i, 2, k).font = _font(9, True)
        c = ws.cell(3 + i, 3, v)
        c.font = _font(9)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[3 + i].height = 30


# --------------------------------------------------------------------------------------- reports
def _sheet_head(ws, title, sub, widths):
    for k, v in widths.items():
        ws.column_dimensions[k].width = v
    ws.cell(1, 2, "MIDWEST CUSTOM ENGINEERING").font = _font(14, True, head=True)
    ws.cell(2, 2, title).font = _font(11, True, ORANGE, head=True)
    c = ws.cell(3, 2, sub)
    c.font = _font(8, italic=True, color=STEEL)
    ws.cell(4, 2, '="Job "&IF(j_Job="","-",j_Job)&"   Customer "&IF(j_Customer="","-",j_Customer)&"   "&p_Material&", "'
                  '&TEXT(d_T,"#,##0")&" lb/hr, "&TEXT(p_MCin,"0.0")&"% to "&TEXT(p_MCout,"0.0")&"% MC, "&f_Fuel').font = \
        _font(9, True)


def _hdr(ws, r, heads, c0=2):
    for j, h in enumerate(heads):
        c = ws.cell(r, c0 + j, h)
        c.font = _font(9, True, WHITE, head=True)
        c.fill = _fill(BLACK)
        c.alignment = Alignment(wrap_text=True, vertical="top")


EM_POLL = [("NOx", "Nitrogen oxides"), ("CO", "Carbon monoxide"), ("SO2", "Sulfur dioxide"),
           ("PM", "Particulate (stack)"), ("VOC", "Volatile organic compounds"), ("CO2", "Carbon dioxide")]


def build_emissions(bk: Book):
    ws = bk.sheet("Emissions")
    _sheet_head(ws, "Emissions estimate (potential to emit)",
                "Screening estimate for permitting discussions. The burner vendor's guarantee and the state permit "
                "govern. Verify factors against the current AP-42 edition before an application.",
                {"A": 1.5, "B": 34, "C": 15, "D": 15, "E": 15, "F": 15, "G": 90})
    # factor table
    r = 6
    ws.cell(r, 2, "AP-42 uncontrolled factors, lb/MMBtu of fuel (HHV)").font = _font(10, True, head=True)
    r += 1
    _hdr(ws, r, ["Fuel key", "NOx", "CO", "PM (burner)", "VOC", "Source"])
    r += 1
    f0 = r
    for key, ef in EM.EMISSION_FACTORS.items():
        ws.cell(r, 2, key).font = _font(9)
        for j, k in enumerate(("NOx", "CO", "PM", "VOC")):
            c = ws.cell(r, 3 + j, ef[k])
            c.number_format = "0.0000"
            c.font = _font(9, color=INPUT_BLUE)
        n = ws.cell(r, 7, ef["source"])
        n.font = _font(8, color=MUTED)
        n.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 24
        r += 1
    for j, k in enumerate(("key", "NOx", "CO", "PM", "VOC")):
        bk.name(f"ef_{k}", ws, f"${CL(2 + j)}${f0}:${CL(2 + j)}${r - 1}")
    r += 1
    ws.cell(r, 2, "Major-source threshold (criteria pollutant)").font = _font(9)
    ws.cell(r, 3, EM.MAJOR_SOURCE_TPY).font = _font(9, color=INPUT_BLUE)
    ws.cell(r, 4, "tpy").font = _font(8, color=STEEL)
    ws.cell(r, 7, "Title V, attainment area. Lower thresholds apply in nonattainment areas; check the state.").font = \
        _font(8, color=MUTED)
    bk.name("em_Major", ws, _abs(3, r))
    r += 1
    ws.cell(r, 2, "Hours for potential to emit").font = _font(9)
    ws.cell(r, 3, 8760).font = _font(9, color=INPUT_BLUE)
    ws.cell(r, 4, "hr/yr").font = _font(8, color=STEEL)
    bk.name("em_PTEhr", ws, _abs(3, r))
    r += 2
    # basis
    ws.cell(r, 2, "Basis").font = _font(10, True, head=True)
    r += 1
    w = CalcWriter(bk, ws)
    w.r = r
    w.put("em_Key", "Fuel", "=INDEX(fu_key,MATCH(f_Fuel,fu_label,0))", "", "@")
    w.put("em_MMBtu", "Fuel fired (HHV)", "=d_mf*d_HHV/1000000", "MMBtu/hr", "0.000", "fuel lb/hr x HHV as fired")
    w.put("em_DSCFM", "Stack flow, dry standard", "=(x_sST_mol-INDEX(g_sST,5))*k_StdVol/60", "DSCFM", "#,##0",
          "70 F, 29.92 in. Hg (EPA uses 68 F; 0.4% difference)")
    w.put("em_O2", "Stack O2, dry", "=x_sST_o2", "vol %", "0.0")
    w.put("em_ODT", "Product dry solids", "=d_Solids/2000", "ODT/hr", "0.000")
    for k in ("NOx", "CO", "PM", "VOC"):
        w.put(f"em_ef{k}", f"{k} factor used", f"=INDEX(ef_{k},MATCH(em_Key,ef_key,0))", "lb/MMBtu", "0.0000")
    w.put("em_BurnerPM", "Burner PM before the collector", "=em_efPM*em_MMBtu", "lb/hr", "0.000",
          "the collector outlet loading below sets stack PM")
    r = w.r + 1
    # results
    ws.cell(r, 2, "Emissions").font = _font(10, True, head=True)
    r += 1
    _hdr(ws, r, ["Pollutant", "lb/hr", "tons/yr at operating hours", "PTE tons/yr (8,760 hr)", "Major source?",
                 "Basis"])
    ws.row_dimensions[r].height = 26
    r += 1
    lbhr = {"NOx": "=em_efNOx*em_MMBtu", "CO": "=em_efCO*em_MMBtu", "SO2": "=d_mf*d_SO2f*mw_SO2",
            "PM": "=a_Grain*em_DSCFM*60/7000", "VOC": "=em_efVOC*em_MMBtu+p_VOC*em_ODT",
            "CO2": "=d_mf*d_CO2f*mw_CO2"}
    basis = {"NOx": "AP-42 factor x fuel fired (HHV)", "CO": "AP-42 factor x fuel fired (HHV)",
             "SO2": "mass balance: all fuel sulfur to SO2",
             "PM": '="collector outlet "&TEXT(a_Grain,"0.000")&" gr/dscf x "&TEXT(em_DSCFM,"#,##0")&" DSCFM"',
             "VOC": '="burner factor + product "&TEXT(p_VOC,"0.00")&" lb/ODT"&IF(p_VOC=0," (product VOC NOT '
                    'estimated)","")',
             "CO2": '="mass balance: all fuel carbon to CO2"&IF(em_Key="biomass"," (biogenic)","")'}
    for k, lab in EM_POLL:
        ws.cell(r, 2, f"{lab} ({k})").font = _font(9)
        c = ws.cell(r, 3, lbhr[k])
        c.number_format = "#,##0.00"
        c.font = _font(9, True)
        c = ws.cell(r, 4, f"=C{r}*p_Hours/2000")
        c.number_format = "#,##0.0"
        c = ws.cell(r, 5, f"=C{r}*em_PTEhr/2000")
        c.number_format = "#,##0.0"
        c.font = _font(9, True)
        ws.cell(r, 6, "n/a" if k == "CO2" else f'=IF(E{r}>=em_Major,"YES: review","no")').font = _font(9, True)
        b = ws.cell(r, 7, basis[k])
        b.data_type = "s" if not basis[k].startswith("=") else b.data_type
        b.font = _font(8, color=MUTED)
        for j, nm in enumerate(("lb", "tpy", "pte")):
            bk.name(f"em_{k}_{nm}", ws, _abs(3 + j, r))
        r += 1
    ws.cell(r, 2, "CO2 is shown for greenhouse-gas reporting (40 CFR 98 threshold 25,000 metric tons CO2e/yr).").font = \
        _font(8, italic=True, color=MUTED)
    r += 2
    ws.cell(r, 2, "Summary").font = _font(10, True, head=True)
    r += 1
    crit = "+".join(f'(em_{k}_pte>=em_Major)*1' for k in ("NOx", "CO", "SO2", "PM", "VOC"))
    c = ws.cell(r, 2, f'=IF(({crit})>0,"One or more pollutants have a potential to emit at or above "&TEXT(em_Major,'
                      f'"0")&" tpy: Title V major-source review is likely.","No criteria pollutant reaches "&'
                      f'TEXT(em_Major,"0")&" tpy potential to emit at these conditions (synthetic minor or minor '
                      f'source likely; confirm with the state).")')
    c.font = _font(9, True)
    bk.name("em_Summary", ws, _abs(2, r))
    r += 2
    notes = ["Factors are uncontrolled. Low-NOx burners, a baghouse or an RTO change the result; use vendor guarantees "
             "when available.",
             "Wood and ag dryers release VOC from the product (terpenes, organic acids). It often sets the permit. "
             "Enter a factor (lb per oven-dry ton) on the Inputs sheet from AP-42 Ch.10.6 or a stack test.",
             "Biomass factors are AP-42 Ch.1.6 for dry wood under 20% moisture; wet fuel or ag residue differ.",
             "Hazardous air pollutants (formaldehyde, acetaldehyde, methanol from wood) are not estimated here.",
             "Sulfur in natural gas and propane is taken from the fuel composition (0 unless entered)."]
    ws.cell(r, 2, "Notes").font = _font(10, True, head=True)
    r += 1
    for n in notes:
        c = ws.cell(r, 2, n)
        c.font = _font(8)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=7)
        r += 1
    return ws


def build_equipment(bk: Book):
    ws = bk.sheet("Equipment")
    _sheet_head(ws, "Equipment summary and handoffs",
                "Sizes come from this calculator. Design values include the burner margin and the design throughput "
                "factor on the Inputs sheet.", {"A": 1.5, "B": 38, "C": 18, "D": 14, "E": 14, "F": 12, "G": 60})
    items = [
        ("Rotary drum dryer", None),
        ("Drum size", "=d_DrumSize", "", "@", ""),
        ("Next size up", "=d_DrumNext", "", "@", ""),
        ("Smaller alternate", "=d_DrumAlt", "", "@", "slightly over the target drum velocity"),
        ("Speed", "=d_DrumRPM", "rpm", "0.0", '="critical "&TEXT(d_DrumNc,"0.0")&" rpm"'),
        ("Slope", "=d_DrumSlope", "in/ft", "0.000", ""),
        ("Residence time", "=d_DrumRes", "min", "0.0", ""),
        ("Fill", "=d_DrumFill", "%", "0.0", ""),
        ("Volumetric evaporation rate", "=d_DrumVER", "lb H2O/hr-ft3", "0.00", ""),
        ("Gas velocity", "=d_DrumVel", "FPM", "#,##0", '="target "&TEXT(r_Vtarget,"0")&" FPM"'),
        ("Insulated shell", "=r_Insulated", "", "@", ""),
        ("Burner and furnace", None),
        ("Burner operating (LHV)", "=d_BurnerOp", "MMBtu/hr", "0.00", ""),
        ("Burner design rating (LHV)", "=d_BurnerDesign", "MMBtu/hr", "0.00", '="margin "&TEXT(r_BurnerMargin,"0.00")'),
        ("Fuel", "=f_Fuel", "", "@", ""),
        ("Fuel rate", "=d_mf", "lb/hr", "#,##0", ""),
        ("Fuel rate, gas", "=IF(d_IsGas=1,d_FuelSCFH,0)", "SCFH", "#,##0", "gas fuels"),
        ("Fuel rate, liquid", "=d_FuelGal", "gal/hr", "#,##0.0", "liquid fuels"),
        ("Solid fuel feed volume (design)", "=h_FuelFt3", "ft3/hr", "#,##0.0", "biomass burner metering bin / screw"),
        ("Dryer inlet temperature", "=r_Tin", "F", "#,##0", ""),
        ("Combustion air", "=x_sCA_scfm", "SCFM", "#,##0", '="excess air "&TEXT(f_EA,"0")&"%"'),
        ("Dilution (tempering) air", "=x_sDA_scfm", "SCFM", "#,##0", ""),
        ("Exhaust fan", None),
        ("Fan flow at fan inlet", "=d_FanACFM", "ACFM", "#,##0", '="at "&TEXT(r_Texh,"0")&" F"'),
        ("Static pressure (operating density)", "=d_SPop", "in. w.c.", "0.0", ""),
        ("Fan brake HP, hot", "=d_BHPop", "HP", "0.0", ""),
        ("Fan brake HP, cold start", "=d_BHPcold", "HP", "0.0", ""),
        ("Fan motor", "=d_Motor", "HP", "0", '=IF(a_VFD="Yes","VFD or inlet damper","sized for cold start")'),
        ("Collector and ducts", None),
        ("Cyclone / baghouse inlet", "=h_CycACFM", "ACFM", "#,##0", ""),
        ("Duct furnace to drum", "=du_in_d", "in. dia", "0", '=TEXT(du_in_v,"#,##0")&" FPM"'),
        ("Duct drum to cyclone", "=du_dc_d", "in. dia", "0", '=TEXT(du_dc_v,"#,##0")&" FPM"'),
        ("Duct stack", "=du_st_d", "in. dia", "0", '=TEXT(du_st_v,"#,##0")&" FPM"'),
        ("Duct recycle", "=IF(r_Recycle>0,du_rc_d,0)", "in. dia", "0", '=IF(r_Recycle>0,TEXT(du_rc_v,"#,##0")&" FPM","none")'),
        ("Feed and discharge (design)", None),
        ("Infeed airlock / screw", "=h_InLb", "lb/hr", "#,##0", '=TEXT(h_InFt3,"#,##0")&" ft3/hr"'),
        ("Discharge airlock / screw", "=h_OutLb", "lb/hr", "#,##0", '=TEXT(h_OutFt3,"#,##0")&" ft3/hr"'),
        ("Dried product", "=d_Product", "lb/hr", "#,##0", '=TEXT(d_AnnProduct,"#,##0")&" tons/yr"'),
    ]
    r = 6
    _hdr(ws, r, ["Item", "Value", "Unit", "", "", "Note"])
    r += 1
    for it in items:
        if it[1] is None:
            r += 1
            for c in range(2, 8):
                ws.cell(r, c).fill = _fill(STEEL)
            ws.cell(r, 1).fill = _fill(ORANGE)
            ws.cell(r, 2, it[0].upper()).font = _font(10, True, WHITE, head=True)
            r += 1
            continue
        lab, f, unit, fmt, note = it
        ws.cell(r, 2, lab).font = _font(9)
        c = ws.cell(r, 3, f)
        c.number_format = fmt
        c.font = _font(9, True)
        ws.cell(r, 4, unit).font = _font(8, color=STEEL)
        n = ws.cell(r, 7, note)
        if not note.startswith("="):
            n.data_type = "s"
        n.font = _font(8, color=MUTED)
        r += 1
    return ws


OPEN_ITEMS = [
    ("Product specific heat (dry solids)", "=p_Cp", "BTU/lb-F",
     "USDA Wood Handbook (wood) or Choi & Okos from typical composition (other products). Confirm by lab test for "
     "a new product."),
    ("Product bulk density, particle size and density", '=TEXT(p_RhoDry,"0.0")&" lb/ft3, "&TEXT(p_Dp,"0.00")&" in"',
     "", "MCE assumption per product; sets drum fill, entrainment and airlock sizing. Confirm from a customer sample."),
    ("Typical infeed and product moisture", '=TEXT(p_MCin,"0")&"% to "&TEXT(p_MCout,"0")&"%"', "% wb",
     "Product library defaults; use the customer's measured values."),
    ("Target residence time and VER range", '=TEXT(p_Residence,"0")&" min, VER "&TEXT(p_VERmin,"0.0")&" to "&'
     'TEXT(p_VERmax,"0.0")', "", "MCE assumption per product; confirm from MCE job history or a test."),
    ("Maximum product temperature", "=p_MaxT", "F", "Heat-sensitive products (food, pet food, DDGS) need the "
     "customer's limit."),
    ("Standard drum grid", "3 to 13 ft dia, 10 to 80 ft long", "", "Placeholder grid; replace with the MCE standard "
     "drum list when set. Over 60 ft is flagged."),
    ("Drum target velocity and allowance", '=TEXT(r_Vtarget,"0")&" FPM + "&TEXT(r_Vtol,"0")&"%"', "",
     "Target per MCE; the allowance only offers a smaller alternate."),
    ("Shell heat-loss coefficient", "=r_U", "BTU/hr-ft2-F", "Estimate accepted by MCE; confirm with field data."),
    ("Leakage air", "=r_Leak", "% of exhaust", "MCE assumption; depends on seals and airlocks."),
    ("Fuel heating value", '=TEXT(f_HV,"#,##0")&" BTU/lb ("&f_HVbasis&")"', "",
     "Biomass 8,000 BTU/lb dry net per MCE; confirm with a fuel analysis for each job."),
    ("Fuel moisture (biomass)", "=f_MC", "% wb", "MCE assumption for dried wood fuel."),
    ("Excess air", "=f_EA", "%", "Burner vendor value governs."),
    ("Furnace efficiency", "=f_Eff", "", "98% gas, 93% biomass per MCE."),
    ("Burner design margin", "=r_BurnerMargin", "", "1.10 per MCE."),
    ("Design throughput factor (handoffs)", "=r_DesignFactor", "", "MCE assumption; confirm per job."),
    ("Fan static pressure", "=a_SP", "in. w.c.", "MCE assumption; replace with the system pressure drop (drum, "
     "cyclone or baghouse, ducts)."),
    ("Ambient humidity", "=s_W", "lb/lb dry air", "Design value; use the site summer design condition if critical."),
    ("Collector outlet loading", "=a_Grain", "gr/dscf", "Sets stack PM. Use the cyclone or baghouse guarantee."),
    ("Product VOC factor", "=p_VOC", "lb/ODT", "0 = not estimated. Needed for wood permits (AP-42 Ch.10.6 or a "
     "stack test)."),
    ("Emission factors", "AP-42 uncontrolled", "", "Screening values; the burner vendor guarantee and the permit "
     "govern."),
    ("Fire risk inlet temperature", "=k_FireT", "F", "Inlet default 900 F; above this a fire-risk warning is shown."),
    ("Dryer type selector", "Python engine only", "", "Rules and thresholds are DRAFT for MCE review."),
]


def build_open_items(bk: Book):
    ws = bk.sheet("Open Items")
    _sheet_head(ws, "Open items and assumptions to confirm",
                "Every value here is an input that can be overridden on the Inputs sheet (or the Products sheet). "
                "Values shown are the ones used in this run.",
                {"A": 1.5, "B": 42, "C": 26, "D": 16, "E": 14, "F": 2, "G": 90})
    r = 6
    _hdr(ws, r, ["Item", "Value used", "Unit", "Status", "", "Note"])
    r += 1
    for lab, f, unit, note in OPEN_ITEMS:
        ws.cell(r, 2, lab).font = _font(9)
        c = ws.cell(r, 3, f)
        if not str(f).startswith("="):
            c.data_type = "s"
        c.font = _font(9, True)
        c.alignment = Alignment(horizontal="left")
        ws.cell(r, 4, unit).font = _font(8, color=STEEL)
        ws.cell(r, 5, "MCE to confirm").font = _font(8, True, ORANGE)
        n = ws.cell(r, 7, note)
        n.data_type = "s"
        n.font = _font(8, color=MUTED)
        n.alignment = Alignment(wrap_text=True, vertical="top")
        r += 1
    r += 1
    ws.cell(r, 2, "Checks raised in this run").font = _font(10, True, head=True)
    r += 1
    ws.cell(r, 2, '=IF(d_WarnCount=0,"None.",TEXT(d_WarnCount,"0")&" active (also listed on the Calc sheet):")').font = \
        _font(9)
    r += 1
    for i in range(1, N_CHECKS + 1):
        c = ws.cell(r, 2, f'=IF(INDEX(ck_All,{i})="","",INDEX(ck_All,{i}))')
        c.font = _font(9, color=ORANGE)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=7)
        r += 1
    return ws


# --------------------------------------------------------------------------------------- entry mapping
def entries_from_request(req: DryerRequest) -> dict[str, Any]:
    """Only fields the request sets explicitly go into the ENTRY column; the rest stay at the default."""
    R = resolve(req)
    p, s, f, r, a = (R.values[b] for b in ("process", "site", "fuel", "rotary", "air"))
    e: dict[str, Any] = {}
    setp = req.process.model_fields_set
    sets = req.site.model_fields_set
    setf = req.fuel.model_fields_set
    setr = req.rotary.model_fields_set
    seta = req.air.model_fields_set
    if req.process.material != "wood_shavings":
        e["p_Material"] = MATERIALS[req.process.material]["label"]
    pm = {"throughput": "p_Throughput", "throughput_unit": "p_TUnit", "throughput_basis": "p_TBasis",
          "infeed_mc_wb": "p_MCin", "target_mc_wb": "p_MCout", "backmix_ratio": "p_BmRatio",
          "backmix_mc_wb": "p_BmMC", "backmix_temp_F": "p_BmT", "feed_temp_F": "p_FeedT",
          "product_temp_F": "p_ProdT", "material_cp": "p_Cp", "bulk_density_dry": "p_RhoDry",
          "bulk_density_wet": "p_RhoWet", "particle_size_in": "p_Dp", "particle_density": "p_RhoP",
          "sphericity": "p_Phi", "max_product_temp_F": "p_MaxT", "annual_hours": "p_Hours",
          "product_voc_lb_odt": "p_VOC"}
    for k, nm in pm.items():
        if k in setp and getattr(req.process, k) is not None:
            e[nm] = p[k]
    for k, nm in {"ambient_temp_F": "s_Tamb", "humidity_lb_lb": "s_W", "elevation_ft": "s_Elev"}.items():
        if k in sets:
            e[nm] = s[k]
    if req.fuel.fuel != "biomass":
        e["f_Fuel"] = FUELS[req.fuel.fuel]["label"]
    fm = {"heating_value": "f_HV", "heating_value_basis": "f_HVbasis", "heating_value_source": "f_HVsource",
          "moisture_wb": "f_MC", "density": "f_Density", "excess_air_pct": "f_EA", "furnace_efficiency": "f_Eff",
          "fuel_temp_F": "f_T"}
    for k, nm in fm.items():
        if k in setf and getattr(req.fuel, k) is not None:
            e[nm] = f[k]
    if req.fuel.ultimate_dry_pct:
        for u in ULT:
            e[f"f_u{u}"] = float(req.fuel.ultimate_dry_pct.get(u, 0.0))
    if req.fuel.gas_composition_pct:
        for g in GAS_COMPONENTS:
            e[f"f_g{g}"] = float(req.fuel.gas_composition_pct.get(g, 0.0))
    rm = {"inlet_temp_F": "r_Tin", "exhaust_temp_F": "r_Texh", "recycle_fraction": "r_Recycle",
          "recycle_temp_F": "r_Trec", "leakage_pct": "r_Leak", "shell_loss_method": "r_ShellMethod",
          "shell_U": "r_U", "shell_loss_pct": "r_ShellPct", "burner_design_margin": "r_BurnerMargin",
          "design_throughput_factor": "r_DesignFactor", "drum_design_velocity_fpm": "r_Vtarget",
          "drum_velocity_tolerance_pct": "r_Vtol", "entrainment_fraction": "r_EntFrac",
          "residence_target_min": "p_Residence", "critical_speed_pct": "r_Crit", "min_dew_point_margin_F": "r_DewMargin"}
    for k, nm in rm.items():
        if k in setr and getattr(req.rotary, k) is not None:
            e[nm] = r[k]
    if "insulated" in setr:
        e["r_Insulated"] = "Yes" if r["insulated"] else "No"
    if "ver_range" in setr and req.rotary.ver_range:
        e["p_VERmin"], e["p_VERmax"] = r["ver_range"]
    if "fill_range_pct" in setr:
        e["r_FillMin"], e["r_FillMax"] = r["fill_range_pct"]
    if "ld_range" in setr:
        e["r_LDmin"], e["r_LDmax"] = r["ld_range"]
    if "slope_range_in_per_ft" in setr:
        e["r_SlopeMin"], e["r_SlopeMax"] = r["slope_range_in_per_ft"]
    if "critical_speed_range_pct" in setr:
        e["r_CritMin"], e["r_CritMax"] = r["critical_speed_range_pct"]
    if req.rotary.force_drum:
        e["r_ForceD"], e["r_ForceL"] = req.rotary.force_drum
    am = {"duct_velocity_fpm": "a_DuctV", "duct_size_increment_in": "a_DuctInc", "min_gas_to_product": "a_MinRatio",
          "convey_velocity_coeff": "a_ConvCoeff", "convey_velocity_factor": "a_ConvFactor", "fan_sp_in_wc": "a_SP",
          "fan_sp_basis": "a_SPbasis", "fan_efficiency": "a_FanEff", "fan_inlet_static_in_wc": "a_FanStatic",
          "collector_outlet_gr_dscf": "a_Grain"}
    for k, nm in am.items():
        if k in seta and getattr(req.air, k) is not None:
            e[nm] = a[k]
    if "product_air_conveyed" in seta:
        e["a_Conveyed"] = "Yes" if a["product_air_conveyed"] else "No"
    if "fan_vfd_or_damper" in seta:
        e["a_VFD"] = "Yes" if a["fan_vfd_or_damper"] else "No"
    if req.rotary.gas_mode != "inlet_temp":
        raise ValueError("the workbook fixes the inlet temperature; run the engine for other gas modes, then pass "
                         "its solved inlet temperature")
    return e


def build_workbook(request: dict | DryerRequest | None = None, path: str | Path = "rotary_dryer.xlsx",
                   record_index: str = "") -> Path:
    req = request if isinstance(request, DryerRequest) else DryerRequest.model_validate(request or {})
    entries = entries_from_request(req)
    job = {"j_Job": req.job.job_number if req.job.job_number != "UNASSIGNED" else "",
           "j_Customer": req.job.customer, "j_Location": req.job.location, "j_PreparedBy": req.job.prepared_by,
           "j_Date": dt.date.today().strftime("%m/%d/%Y"), "j_Case": "", "j_Record": record_index}
    bk = Book()
    build_data(bk)
    build_products(bk)
    build_inputs(bk, entries, job)
    build_gas_and_calc(bk)
    build_drum(bk)
    build_diagram(bk)
    build_emissions(bk)
    build_equipment(bk)
    build_open_items(bk)
    build_notes(bk)
    order = ["Mass-Energy Balance", "Inputs", "Equipment", "Emissions", "Open Items", "Calc", "Gas", "Drum",
             "Products", "Data", "Notes"]
    bk.wb._sheets = [bk.wb[n] for n in order]
    tabs = {"Mass-Energy Balance": ORANGE, "Inputs": BLACK, "Equipment": ORANGE, "Emissions": ORANGE,
            "Open Items": ORANGE, "Calc": STEEL, "Gas": SILVER, "Drum": SILVER, "Products": STEEL, "Data": SILVER,
            "Notes": SILVER}
    for n, col in tabs.items():
        bk.wb[n].sheet_properties.tabColor = col
    for n in ("Inputs", "Equipment", "Emissions", "Open Items", "Calc", "Notes"):
        ws = bk.wb[n]
        ws.page_setup.orientation = "landscape"
        ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.oddFooter.left.text = "MIDWEST CUSTOM ENGINEERING  |  " + WB_VERSION
        ws.oddFooter.right.text = "Page &P of &N"
    bk.wb["Inputs"].column_dimensions["C"].width = 30
    bk.wb["Inputs"].column_dimensions["E"].width = 30
    bk.wb.active = 0
    bk.wb.calculation.fullCalcOnLoad = True
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bk.wb.save(path)
    return path


# --------------------------------------------------------------------------------------- entries -> request
_P = {"p_Throughput": "throughput", "p_TUnit": "throughput_unit", "p_TBasis": "throughput_basis",
      "p_MCin": "infeed_mc_wb", "p_MCout": "target_mc_wb", "p_BmRatio": "backmix_ratio", "p_BmMC": "backmix_mc_wb",
      "p_BmT": "backmix_temp_F", "p_FeedT": "feed_temp_F", "p_ProdT": "product_temp_F", "p_Cp": "material_cp",
      "p_RhoDry": "bulk_density_dry", "p_RhoWet": "bulk_density_wet", "p_Dp": "particle_size_in",
      "p_RhoP": "particle_density", "p_Phi": "sphericity", "p_MaxT": "max_product_temp_F", "p_Fire": "fire_risk",
      "p_Hours": "annual_hours", "p_VOC": "product_voc_lb_odt"}
_S = {"s_Tamb": "ambient_temp_F", "s_W": "humidity_lb_lb", "s_Elev": "elevation_ft"}
_F = {"f_HV": "heating_value", "f_HVbasis": "heating_value_basis", "f_HVsource": "heating_value_source",
      "f_MC": "moisture_wb", "f_Density": "density", "f_EA": "excess_air_pct", "f_Eff": "furnace_efficiency",
      "f_T": "fuel_temp_F"}
_R = {"r_Tin": "inlet_temp_F", "r_Texh": "exhaust_temp_F", "r_Recycle": "recycle_fraction",
      "r_Trec": "recycle_temp_F", "r_Leak": "leakage_pct", "r_ShellMethod": "shell_loss_method", "r_U": "shell_U",
      "r_ShellPct": "shell_loss_pct", "r_BurnerMargin": "burner_design_margin",
      "r_DesignFactor": "design_throughput_factor", "r_Vtarget": "drum_design_velocity_fpm",
      "r_Vtol": "drum_velocity_tolerance_pct", "r_EntFrac": "entrainment_fraction", "p_Residence": "residence_target_min",
      "r_Crit": "critical_speed_pct", "r_DewMargin": "min_dew_point_margin_F"}
_A = {"a_DuctV": "duct_velocity_fpm", "a_DuctInc": "duct_size_increment_in", "a_MinRatio": "min_gas_to_product",
      "a_ConvCoeff": "convey_velocity_coeff", "a_ConvFactor": "convey_velocity_factor", "a_SP": "fan_sp_in_wc",
      "a_SPbasis": "fan_sp_basis", "a_FanEff": "fan_efficiency", "a_FanStatic": "fan_inlet_static_in_wc",
      "a_Grain": "collector_outlet_gr_dscf"}
_PAIRS = {("p_VERmin", "p_VERmax"): ("rotary", "ver_range"), ("r_FillMin", "r_FillMax"): ("rotary", "fill_range_pct"),
          ("r_LDmin", "r_LDmax"): ("rotary", "ld_range"), ("r_SlopeMin", "r_SlopeMax"): ("rotary", "slope_range_in_per_ft"),
          ("r_CritMin", "r_CritMax"): ("rotary", "critical_speed_range_pct")}
WORKBOOK_ONLY = {"f_Cp", "r_Lnormal", "j_Location", "j_Case", "j_Date", "j_Record"}


def request_from_entries(entries: dict[str, Any]) -> tuple[dict, list[str]]:
    """Inverse of entries_from_request: workbook ENTRY values -> engine request. Returns (request, ignored names)."""
    e = {k: v for k, v in entries.items() if v not in (None, "")}
    req: dict[str, Any] = {"process": {}, "site": {}, "fuel": {}, "rotary": {}, "air": {}, "job": {}}
    ignored = []
    mat_keys = {m["label"]: k for k, m in MATERIALS.items()}
    fuel_keys = {f["label"]: k for k, f in FUELS.items()}
    if "p_Material" in e:
        req["process"]["material"] = mat_keys[e.pop("p_Material")]
    if "f_Fuel" in e:
        req["fuel"]["fuel"] = fuel_keys[e.pop("f_Fuel")]
    for blk, table in (("process", _P), ("site", _S), ("fuel", _F), ("rotary", _R), ("air", _A)):
        for nm, field in table.items():
            if nm in e:
                req[blk][field] = e.pop(nm)
    if "r_Insulated" in e:
        req["rotary"]["insulated"] = e.pop("r_Insulated") == "Yes"
    if "a_Conveyed" in e:
        req["air"]["product_air_conveyed"] = e.pop("a_Conveyed") == "Yes"
    if "a_VFD" in e:
        req["air"]["fan_vfd_or_damper"] = e.pop("a_VFD") == "Yes"
    probe = resolve(DryerRequest.model_validate({k: v for k, v in req.items() if k != "job"}))
    for (lo, hi), (blk, field) in _PAIRS.items():
        if lo in e or hi in e:
            d = probe.values[blk][field]
            req[blk][field] = [e.pop(lo, d[0]), e.pop(hi, d[1])]
    if e.get("r_ForceD") and e.get("r_ForceL"):
        req["rotary"]["force_drum"] = [e.pop("r_ForceD"), e.pop("r_ForceL")]
    e.pop("r_ForceD", None), e.pop("r_ForceL", None)
    ult = {u: e.pop(f"f_u{u}") for u in ULT if f"f_u{u}" in e}
    if ult:
        base = dict(probe.values["fuel"]["ultimate_dry_pct"] or {})
        req["fuel"]["ultimate_dry_pct"] = {**base, **ult}
    gas = {g: e.pop(f"f_g{g}") for g in GAS_COMPONENTS if f"f_g{g}" in e}
    if gas:
        base = dict(probe.values["fuel"]["gas_composition_pct"] or {})
        req["fuel"]["gas_composition_pct"] = {k: v for k, v in {**base, **gas}.items() if v}
    for nm, field in (("j_Job", "job_number"), ("j_Customer", "customer"), ("j_PreparedBy", "prepared_by"),
                      ("j_Location", "location")):
        if nm in e:
            req["job"][field] = str(e.pop(nm))
    ignored = sorted(k for k in e if k not in WORKBOOK_ONLY) + sorted(k for k in e if k in WORKBOOK_ONLY)
    return {k: v for k, v in req.items() if v}, ignored


def workbook_from_entries(entries: dict[str, Any], record_index: str = "") -> bytes:
    """Calculator entries -> the live MCE workbook for those inputs (as .xlsx bytes)."""
    import tempfile

    req, _ = request_from_entries(entries)
    with tempfile.TemporaryDirectory() as tmp:
        p = build_workbook(req, Path(tmp) / "rotary_dryer.xlsx",
                           record_index=record_index or str(entries.get("j_Record") or ""))
        return p.read_bytes()


def workbook_filename(entries: dict[str, Any]) -> str:
    job = str(entries.get("j_Job") or entries.get("j_Record") or "case")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in job)
    return f"MCE_rotary_dryer_{safe}.xlsx"
