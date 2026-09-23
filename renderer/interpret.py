#!/usr/bin/env python3
"""Turn a sales rep's sentence into a structured job request.

    "quote Dennis Heideman at Fairview Mills a 4430 with 200hp for grinding a
     grain ration pet food 15tph on a 6/64\" screen, including an SS round cup
     10\" auto selfclean feeder, plenum chamber, screw, and air system"

The split here is deliberate and load-bearing:

  * Claude does **extraction only**. It reads the sentence and fills in fields
    that were actually stated. It is told, and schema-constrained, never to
    invent a capacity, a horsepower, a model, a size or a price, and to push
    anything it cannot resolve into `ambiguities` rather than guess.
  * **MCE's calculators do all the engineering.** Every number that reaches the
    proposal comes out of calculators/, which are the verified ports of MCE's
    own tools. Nothing the model says becomes a quoted figure.

That keeps the rule the quote-builder skill states plainly — prices come from
MCE's basis, sizes come from MCE's calculators — true even though the intake is
free text.
"""
import os
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from calculators._data import PRODUCTS

MODEL = os.environ.get("INTERPRET_MODEL", "claude-opus-5")

PRODUCT_NAMES = [p["name"] for p in PRODUCTS]


class FeederSpec(BaseModel):
    """The rotary feeder, as described. Any field the text doesn't pin down stays None."""
    diameter_in: Optional[Literal["10", "14"]] = Field(
        None, description='Feeder rotor diameter in inches, only if stated (e.g. 10" dia).')
    cup_type: Optional[Literal["nylon", "ss", "tt"]] = Field(
        None, description='Cup type: "nylon" for nylon cup, "ss" for stainless round cup, '
                          '"tt" for tight-tolerance stainless. Only if stated.')
    rows: Optional[int] = Field(
        None, description="Number of cup rows, only if unambiguously stated. If the text "
                          'gives something unclear like "8-4row", leave this null and '
                          "record the problem in ambiguities.")
    magnet_clean: Optional[Literal["sma", "scmam", "scmaa"]] = Field(
        None, description='Magnet cleanout: "sma" manual clean, "scmam" manual self-clean, '
                          '"scmaa" auto self-clean. Only if stated.')
    as_written: Optional[str] = Field(
        None, description="The feeder phrase exactly as the rep wrote it.")


class JobRequest(BaseModel):
    """Everything the rep stated. Absent means absent — never fill a gap."""

    customer_company: Optional[str] = Field(None, description="Customer company name.")
    customer_contact: Optional[str] = Field(None, description="Named contact at the customer.")

    mill_model: Optional[str] = Field(
        None, description='Hammermill model, normalised to MCE form: a bare "4430" becomes '
                          '"XM-4430". Null if no model was named.')
    motor_hp: Optional[float] = Field(
        None, description="Motor horsepower, only if the rep stated one.")

    product_as_written: Optional[str] = Field(
        None, description="The material being ground, in the rep's own words.")
    product_match: Optional[str] = Field(
        None, description="The closest entry in MCE's product table, copied exactly, or null "
                          "if none clearly fits.")
    product_confidence: Literal["stated", "inferred", "unsure"] = Field(
        "unsure", description='"stated" if the rep named a product that matches one table '
                              'entry and only one; "inferred" if you had to reason to pick '
                              'between entries; "unsure" if it could reasonably be more than '
                              "one. Prefer inferred/unsure over false confidence.")

    capacity_tph: Optional[float] = Field(
        None, description="Throughput in tons per hour, if stated in TPH.")
    capacity_pph: Optional[float] = Field(
        None, description="Throughput in pounds per hour, if stated in PPH.")
    screen_64ths: Optional[float] = Field(
        None, description='Screen hole size in 64ths of an inch. A 6/64" screen is 6. A '
                          'screen given as a fraction like 3/32" is 6 (3/32 = 6/64).')

    feeder: FeederSpec = Field(default_factory=FeederSpec)

    include_plenum: bool = Field(False, description="Rep asked for a plenum chamber.")
    include_screw: bool = Field(False, description="Rep asked for a discharge/transfer screw.")
    include_air_system: bool = Field(
        False, description="Rep asked for an air system (fans, cyclone, filter, ducting).")
    include_magnet: bool = Field(False, description="Rep asked for a magnet or magnet adapter.")
    other_items: List[str] = Field(
        default_factory=list,
        description="Anything else the rep asked for, verbatim, that has no field above.")

    quantity: int = Field(1, description="Number of mill lines, if stated. Default 1.")

    ambiguities: List[str] = Field(
        default_factory=list,
        description="One plain-English line for anything you could not resolve, could not "
                    "read, or had to leave null — written for the sales rep, naming what you "
                    "need from them. Never guess to keep this list empty.")


SYSTEM = f"""You read a Midwest Custom Engineering sales rep's shorthand request for an \
equipment quote and turn it into structured fields.

You are doing EXTRACTION ONLY. MCE's own sizing calculators do all the engineering \
downstream from you. Your output must contain nothing the rep did not say.

Rules, in order of importance:

1. Never invent a value. If the rep did not state a capacity, a horsepower, a model, a \
screen size, a feeder detail or a quantity, leave that field null. A null field is correct \
and useful; a guessed field is a wrong quote.
2. Never resolve an ambiguity by picking the likelier option. Leave the field null and write \
a line in `ambiguities` saying exactly what you need. For example, a feeder written as \
"8-4row" could be 8 rows or 4 rows — that is an ambiguity, not an 8.
3. Do not do arithmetic beyond unit normalisation that the rep clearly implied \
(tons per hour stays in capacity_tph; pounds per hour stays in capacity_pph; a screen \
written as a fraction of an inch converts to 64ths).
4. Mill models: MCE mills are written XM-#### — a bare "4430" is "XM-4430".
5. For product_match, copy one of these strings EXACTLY, or null if none clearly fits:
{chr(10).join('   - ' + n for n in PRODUCT_NAMES)}
   Several of these are close together (the two pet food entries grind very differently). \
If the rep's wording does not clearly select one, set product_confidence to "unsure" and \
say so in `ambiguities` — do not pick the more common one.
6. `ambiguities` is for the rep to act on. Write it as short, specific questions or \
statements, not as a list of field names."""


class InterpretError(RuntimeError):
    """The request could not be interpreted (no key, API failure, unusable text)."""


def available():
    """True when an API credential is configured."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def interpret(text):
    """Sentence -> JobRequest. Raises InterpretError with something a rep can act on."""
    text = (text or "").strip()
    if not text:
        raise InterpretError("Type the job description first.")
    if not available():
        raise InterpretError(
            "The job-description box needs an Anthropic API key. Set ANTHROPIC_API_KEY in "
            "deploy/.env and restart, or fill the quote in by hand below.")
    try:
        import anthropic
    except ImportError as e:                       # pragma: no cover - deployment issue
        raise InterpretError("The anthropic package is not installed in this container.") from e

    client = anthropic.Anthropic(timeout=90.0, max_retries=2)
    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=8000,
            system=SYSTEM,
            messages=[{"role": "user", "content": text}],
            output_format=JobRequest,
        )
    except Exception as e:                         # noqa: BLE001 - surface, don't 500
        raise InterpretError(f"Could not read that request: {e}") from e

    if response.stop_reason == "refusal":
        raise InterpretError("That request was declined by the model. Fill the quote in by hand.")
    job = response.parsed_output
    if job is None:
        raise InterpretError("Could not read that request. Try rephrasing it, or fill the "
                             "quote in by hand.")
    return job
