"""Typed input schema for every MCE dryer calculator (JSON in).

Every field carries: unit, sane range, default and the default's source. A field left
at None takes its value from the selected material or fuel preset; setting it is an
override of that preset. Setting any field away from its default is recorded as an
override in the sizing record, and any value outside its sane range is flagged with
the reason (never silently accepted, never blocked).

The process block is shared by all dryer types so flash, belt and infrared calculators
plug in later; the rotary block is rotary-drum specific.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .presets import FUELS, MATERIALS, MCE_CONFIRM

MaterialKey = Literal[tuple(MATERIALS)]  # type: ignore[valid-type]
FuelKey = Literal[tuple(FUELS)]  # type: ignore[valid-type]
Level = Literal["none", "low", "moderate", "high"]
FireRisk = Literal["low", "moderate", "high"]


def F(default: Any, unit: str = "", lo: float | None = None, hi: float | None = None, src: str = "",
      desc: str = "", preset: str | None = None, reason: str = "") -> Any:
    """Field with MCE metadata. `preset` names the preset key used when the value is None."""
    extra = {"unit": unit, "sane_range": [lo, hi], "source": src}
    if preset:
        extra["preset"] = preset
    if reason:
        extra["range_reason"] = reason
    return Field(default, description=desc, json_schema_extra=extra)


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobBlock(_M):
    job_number: str = F("UNASSIGNED", desc="MCE job or quote number")
    customer: str = F("", desc="Customer name (internal record only)")
    location: str = F("", desc="Site location")
    prepared_by: str = F("", desc="Salesperson or engineer running the case")


class ProcessInputs(_M):
    material: MaterialKey = F("wood_shavings", desc="Material pick (sets the preset properties below)",
                              src="pull-down")
    throughput: float = F(3000.0, "per throughput_unit", 1.0, 400000.0, "test case: 1.5 TPH wet",
                          desc="Throughput value")
    throughput_unit: Literal["lb/hr", "TPH"] = F("lb/hr", desc="Unit of throughput (TPH = US short tons/hr)")
    throughput_basis: Literal["wet_feed", "dry_solids", "product"] = F(
        "wet_feed", desc="wet_feed = dryer infeed as received; dry_solids = bone dry; product = dried product")
    infeed_mc_wb: float = F(50.0, "% wet basis", 2.0, 75.0, "test case", desc="Infeed moisture, wet basis",
                            reason="rotary drums rarely see over 65 to 70% wb without backmix")
    target_mc_wb: float = F(10.0, "% wet basis", 0.5, 40.0, "SHEET Input F15", desc="Product moisture, wet basis")
    backmix_ratio: float = F(0.0, "lb backmix / lb fresh wet feed", 0.0, 3.0, "SHEET Input A14",
                             desc="Dried product returned to the infeed")
    backmix_mc_wb: float | None = F(None, "% wet basis", 0.5, 40.0, "SHEET Input A15 (= product MC)",
                                    desc="Backmix moisture; None = product MC")
    backmix_temp_F: float | None = F(None, "F", -20.0, 250.0, "MCE assumption: backmix cools to ambient",
                                     desc="Backmix temperature at the infeed; None = ambient")
    feed_temp_F: float | None = F(None, "F", -20.0, 200.0, "SHEET Input D14 (mixed infeed 60 F = ambient)",
                                  desc="Fresh feed temperature; None = ambient")
    product_temp_F: float = F(200.0, "F", 100.0, 400.0, "SHEET Input F14", desc="Product discharge temperature")
    material_cp: float | None = F(None, "BTU/lb-F", 0.2, 0.9, "material preset", preset="cp",
                                  desc="Dry solids specific heat")
    bulk_density_dry: float | None = F(None, "lb/ft3", 2.0, 120.0, "material preset", preset="bulk_density_dry",
                                       desc="Dry product bulk density (one value used everywhere)")
    bulk_density_wet: float | None = F(None, "lb/ft3", 2.0, 150.0,
                                       "computed = dry bulk density x (1 + dry-basis MC), no shrink/swell; "
                                       + MCE_CONFIRM, desc="Wet infeed bulk density; None = computed")
    particle_size_in: float | None = F(None, "in", 0.002, 4.0, "material preset", preset="particle_size_in",
                                       desc="Volume-equivalent sphere diameter of the design particle (entrainment and Friedman-Marshall Dp)")
    particle_density: float | None = F(None, "lb/ft3", 5.0, 200.0, "material preset", preset="particle_density",
                                       desc="Particle (envelope) density")
    sphericity: float | None = F(None, "-", 0.1, 1.0, "material preset", preset="sphericity",
                                 desc="Particle sphericity for the drag correlation")
    max_product_temp_F: float | None = F(None, "F", 100.0, 600.0, "material preset", preset="max_product_temp_F",
                                         desc="Maximum allowable product temperature")
    heat_sensitivity: Level | None = F(None, src="material preset", preset="heat_sensitivity",
                                       desc="Heat sensitivity class")
    fire_risk: FireRisk | None = F(None, src="material preset", preset="fire_risk", desc="Fire risk class")
    sticky: bool | None = F(None, src="material preset", preset="sticky", desc="Sticky when wet")
    surface_moisture: bool = F(False, src="MCE assumption: bound moisture (conservative)",
                               desc="True if the water is mostly surface moisture (selector input)")
    residence_need: Literal["short", "medium", "long"] = F("medium", src="selector input",
                                                           desc="Drying time the product needs")
    footprint: Literal["normal", "tight"] = F("normal", src="selector input", desc="Plant footprint constraint")
    product_value: Literal["normal", "high"] = F("normal", src="selector input", desc="High value / specialty product")
    precise_temperature: bool = F(False, src="selector input", desc="Product needs precise temperature control")
    heat_source: Literal["fuel", "waste_heat", "steam", "electric"] = F(
        "fuel", src="selector input", desc="fuel = direct fired on the fuel pick below")
    annual_hours: float = F(7500.0, "hr/yr", 100.0, 8760.0, "SHEET Input H31 (FLOW R19 says 8,000; Input used)",
                            desc="Operating hours per year")


class SiteInputs(_M):
    ambient_temp_F: float = F(60.0, "F", -40.0, 120.0, "SHEET Input D4", desc="Ambient (and air intake) temperature")
    humidity_lb_lb: float = F(0.002, "lb H2O/lb dry air", 0.0, 0.03, "SHEET Input D6", desc="Ambient humidity ratio")
    elevation_ft: float = F(1200.0, "ft", -300.0, 10000.0, "SHEET Input A10", desc="Site elevation")


class FuelInputs(_M):
    fuel: FuelKey = F("dry_wood", desc="Fuel pick", src="pull-down")
    heating_value: float | None = F(None, "BTU/lb", 1000.0, 25000.0, "fuel preset", preset="heating_value",
                                    desc="Heating value in the basis below")
    heating_value_basis: Literal["net_as_fired", "net_dry", "gross_dry", "gross_as_fired"] | None = F(
        None, src="fuel preset", preset="heating_value_basis", desc="Basis of the heating value entered")
    heating_value_source: Literal["entered", "analysis"] = F(
        "entered", src="MCE rule: use the entered value, cross-check against the analysis",
        desc="'analysis' uses the LHV computed from the fuel analysis instead")
    moisture_wb: float | None = F(None, "% wet basis", 0.0, 60.0, "fuel preset", preset="moisture_wb",
                                  desc="Fuel moisture as fired")
    ultimate_dry_pct: dict[str, float] | None = F(None, "mass % dry", src="fuel preset", preset="ultimate",
                                                  desc="Solid/liquid fuel: C, H, O, N, S, ash (dry basis, = 100)")
    gas_composition_pct: dict[str, float] | None = F(None, "mol %", src="fuel preset", preset="composition",
                                                     desc="Gas fuel: CH4, C2H6, C3H8, C4H10, H2, CO, CO2, N2, O2, H2S")
    density: float | None = F(None, "lb/ft3", 0.01, 70.0, "fuel preset", preset="density",
                              desc="Solid bulk density or liquid density (gas: cross-check only)")
    excess_air_pct: float | None = F(None, "% excess air", 0.0, 400.0, "fuel preset", preset="excess_air_pct",
                                     desc="% excess air over stoichiometric (130 = 2.3 x stoich air)")
    furnace_efficiency: float | None = F(None, "fraction", 0.80, 1.0, "fuel preset", preset="furnace_efficiency",
                                         desc="Covers unburned fuel and furnace/burner radiation only (stack loss "
                                              "is computed separately)")
    fuel_temp_F: float | None = F(None, "F", -40.0, 200.0, "ambient", desc="Fuel temperature; None = ambient")


class RotaryInputs(_M):
    gas_mode: Literal["inlet_temp", "inlet_gas_flow", "exhaust_acfm"] = F(
        "inlet_temp", desc="Which gas-side quantity is fixed; the solver finds the rest")
    inlet_temp_F: float = F(900.0, "F", 250.0, 1800.0,
                            "MCE (Jason, 2026-11-07): 900 F default; 1,000 F acceptable",
                            desc="Dryer inlet gas temperature (used when gas_mode = inlet_temp)",
                            reason="above 1,800 F is outside the gas property fit and a fire risk for organics")
    inlet_gas_lb_hr: float | None = F(None, "lb/hr", 100.0, 1.0e6, "user",
                                      desc="Dryer inlet total wet gas flow (gas_mode = inlet_gas_flow)")
    exhaust_acfm_target: float | None = F(None, "ACFM", 100.0, 1.0e6, "user (SHEET Input H23 had a 34,000 target)",
                                          desc="Dryer exhaust ACFM at exhaust temp (gas_mode = exhaust_acfm)")
    exhaust_temp_F: float = F(180.0, "F", 120.0, 400.0, "SHEET Input F24", desc="Dryer exhaust gas temperature")
    recycle_fraction: float = F(0.0, "fraction of exhaust", 0.0, 0.8, "SHEET Input H28 (0)",
                                desc="Fraction of dryer exhaust returned to the furnace mixing chamber")
    recycle_temp_F: float | None = F(None, "F", 100.0, 400.0, "SHEET Input F29 (= exhaust - 5 F)",
                                     desc="Recycle gas temperature at the mixing chamber; None = exhaust - 5 F")
    leakage_pct: float = F(5.0, "% of dryer inlet gas mass", 0.0, 30.0, "Seal leakage at ambient. " + MCE_CONFIRM,
                           desc="Ambient air drawn in at the drum seals")
    shell_loss_method: Literal["UA", "percent"] = F("UA", desc="UA = U x A x (T gas avg - T ambient)")
    insulated: bool = F(False, src=MCE_CONFIRM, desc="Insulation jacket on the drum shell")
    shell_U: float | None = F(None, "BTU/hr-ft2-F", 0.05, 6.0,
                              "None = 1.5 bare / 0.5 jacketed, combined convection + radiation (estimate accepted by "
                              "Jason 2026-11-07)",
                              desc="Overall shell heat loss coefficient")
    shell_loss_pct: float = F(5.0, "% of burner heat (LHV)", 0.0, 20.0,
                              "Fallback when shell_loss_method = percent (sheet used 5% of latent heat). " + MCE_CONFIRM)
    burner_design_margin: float = F(1.10, "x operating", 1.0, 2.0,
                                    "MCE (Jason 2026-11-07): about 1.10, how the 6.5 MMBtu/hr burner on the "
                                    "3,460 lb/hr duty was sized",
                                    desc="Burner design rating / operating firing rate")
    design_throughput_factor: float = F(1.25, "x operating", 1.0, 3.0, MCE_CONFIRM,
                                        desc="Design throughput for feeders, airlocks and screws")
    drum_design_velocity_fpm: float = F(350.0, "FPM", 100.0, 1500.0,
                                        "MCE target (Jason 2026-11-07): above it wet material starts air conveying",
                                        desc="Target gas velocity through the drum free area at exhaust conditions")
    drum_velocity_tolerance_pct: float = F(10.0, "% over target", 0.0, 50.0,
                                           "MCE: 'could be slightly higher' (Jason 2026-11-07); 10% " + MCE_CONFIRM,
                                           desc="Drums up to this much over the target velocity are shown as a "
                                                "smaller alternate, never as the recommendation")
    entrainment_fraction: float = F(0.5, "x particle terminal velocity", 0.1, 1.0, MCE_CONFIRM,
                                    desc="Drum velocity limit as a fraction of the design particle terminal velocity. "
                                         "Hard check only when the product is NOT air conveyed out of the drum")
    ver_range: list[float] | None = F(None, "lb H2O/hr-ft3", 0.2, 15.0, "material preset", preset="ver_range",
                                      desc="[min, max] volumetric evaporation rate")
    residence_target_min: float | None = F(None, "min", 1.0, 90.0, "material preset", preset="residence_target_min",
                                           desc="Required drum residence time")
    fill_range_pct: list[float] = F([5.0, 15.0], "% of drum volume", 1.0, 25.0,
                                    "Commonly quoted 10 to 15% for flighted drums, widened to 5% for low density "
                                    "wood. " + MCE_CONFIRM, desc="Allowed material holdup")
    critical_speed_pct: float = F(25.0, "% of critical", 5.0, 50.0, MCE_CONFIRM,
                                  desc="Design drum speed as % of critical speed")
    critical_speed_range_pct: list[float] = F([15.0, 35.0], "% of critical", 5.0, 50.0, MCE_CONFIRM)
    slope_range_in_per_ft: list[float] = F([0.0, 1.0], "in/ft", 0.0, 2.0,
                                           "0 to 8 cm/m is the usual range for rotary dryers. " + MCE_CONFIRM)
    ld_range: list[float] = F([4.0, 10.0], "L/D", 2.0, 15.0, "Usual rotary dryer L/D 4 to 10. " + MCE_CONFIRM)
    standard_diameters_ft: list[float] | None = F(None, "ft", src="presets.STANDARD_DRUM_DIAMETERS_FT (placeholder)")
    standard_lengths_ft: list[float] | None = F(None, "ft", src="presets.STANDARD_DRUM_LENGTHS_FT (placeholder)")
    force_drum: list[float] | None = F(None, "[D ft, L ft]", src="user",
                                       desc="Check this drum instead of picking one (still runs every check)")
    min_dew_point_margin_F: float = F(30.0, "F", 0.0, 150.0, MCE_CONFIRM,
                                      desc="Required margin of exhaust temperature above its dew point")


class AirSystemInputs(_M):
    duct_velocity_fpm: float | None = F(None, "FPM", 1500.0, 8000.0,
                                        "SHEET Input A23: 4,500 FPM, 5,200 FPM if bulk density > 12 lb/ft3",
                                        desc="Target duct velocity; None = sheet rule")
    duct_size_increment_in: float = F(1.0, "in", 0.5, 6.0, MCE_CONFIRM, desc="Round duct diameter increment")
    product_air_conveyed: bool = F(True, src="SHEET Input A25:A27 (product conveyed to cyclone by dryer gas)",
                                   desc="Dried product leaves the drum in the gas stream")
    min_gas_to_product: float = F(3.0, "lb gas/lb product", 0.5, 20.0, "SHEET Input A26",
                                  desc="Minimum gas-to-product ratio for air conveying")
    convey_velocity_coeff: float = F(920.0, "FPM per sqrt(lb/ft3)", 100.0, 3000.0,
                                     "SHEET FLOW R15 (source of the 920 coefficient unknown). " + MCE_CONFIRM)
    convey_velocity_factor: float = F(1.3, "-", 1.0, 3.0, "SHEET FLOW R15 safety factor")
    fan_sp_in_wc: float = F(18.0, "in. w.c.", 1.0, 60.0, "SHEET DESIGN B29", desc="Fan static pressure")
    fan_sp_basis: Literal["standard_air", "operating"] = F(
        "standard_air", src=MCE_CONFIRM, desc="standard_air: SP rated at 0.075 lb/ft3 and corrected to gas density")
    fan_efficiency: float = F(0.571, "fraction", 0.3, 0.9, "SHEET DESIGN B29 factor 1.75 = 1/0.571. " + MCE_CONFIRM,
                              desc="Fan static efficiency")
    fan_inlet_static_in_wc: float = F(0.0, "in. w.c. gauge", -60.0, 10.0, "0 = ACFM at site barometric pressure",
                                      desc="Static pressure at the fan inlet (negative = suction)")
    fan_vfd_or_damper: bool = F(True, src=MCE_CONFIRM, desc="If False the motor is sized for cold start")


class DryerRequest(_M):
    contract: Literal["mce.dryer.v1"] = "mce.dryer.v1"
    dryer_type: Literal["auto", "rotary", "flash", "belt", "infrared"] = F(
        "rotary", desc="auto = run the dryer type selector first")
    job: JobBlock = Field(default_factory=JobBlock)
    process: ProcessInputs = Field(default_factory=ProcessInputs)
    site: SiteInputs = Field(default_factory=SiteInputs)
    fuel: FuelInputs = Field(default_factory=FuelInputs)
    rotary: RotaryInputs = Field(default_factory=RotaryInputs)
    air: AirSystemInputs = Field(default_factory=AirSystemInputs)
    override_reasons: dict[str, str] = F({}, desc="Reason per overridden field, keyed 'block.field'")
    save_record: bool = F(True, desc="Write the sizing record to the audit store")


BLOCKS = ("process", "site", "fuel", "rotary", "air")


def field_meta(block_model: type[BaseModel], name: str) -> dict:
    f = block_model.model_fields[name]
    return dict(f.json_schema_extra or {}) | {"default": f.default, "description": f.description or ""}


def input_json_schema() -> dict:
    return DryerRequest.model_json_schema()
