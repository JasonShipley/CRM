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
import json
import os
from typing import List, Literal, Optional, get_args, get_origin

from pydantic import BaseModel, Field, ValidationError

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
    dust_collection: Optional[Literal["baghouse", "cyclone"]] = Field(
        None, description='Which dust collection the rep named, if they named one: '
                          '"baghouse" for a bag/dust filter or collector, "cyclone" for a '
                          "cyclone. Null if they only said \"air system\" or named neither "
                          "— do not infer one from the rest of the request.")
    include_magnet: bool = Field(False, description="Rep asked for a magnet or magnet adapter.")
    system_cfm: Optional[float] = Field(
        None, description="An airflow the rep stated directly, in CFM or SCFM — e.g. "
                          "\"4,680 SCFM through the mill\". Only if they gave a number.")
    sizing_only: bool = Field(
        False, description="True when the rep asked to SIZE equipment rather than quote a "
                           "mill — e.g. \"size me a fan, baghouse and airlock for ...\". "
                           "False when they asked for a mill quote.")
    air_swept: bool = Field(
        False, description="Rep asked for an air-swept mill, a drop-down air pan, or a drop "
                           "down airpan. These go together and change how the air is sized.")
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


TIMEOUT_S = 180.0
MAX_TOKENS = 4000

def _field_spec(name, field):
    """One line of the JSON contract for a field, derived from the model itself.

    Hand-writing these is how the first attempt went wrong: the instruction named
    the keys but not the allowed values, so the model sent `"round"` for a cup
    type and `true` for a magnet cleanout. Generating them means the contract
    cannot drift from what JobRequest will actually accept.
    """
    ann = field.annotation
    optional = type(None) in get_args(ann)
    if get_origin(ann) in (list, List):
        inner = ann                                # a list is not an Optional to unwrap
    else:
        args = [a for a in get_args(ann) if a is not type(None)]
        inner = args[0] if len(args) == 1 else ann

    if get_origin(inner) is Literal:
        allowed = ", ".join(json.dumps(v) for v in get_args(inner))
        kind = f"one of {allowed}"
    elif inner is bool:
        kind = "true or false (never null)"
    elif inner is int:
        kind = "a whole number"
    elif inner is float:
        kind = "a number"
    elif get_origin(inner) in (list, List):
        kind = "an array of strings, [] if none"
    elif inner is str:
        kind = "a string"
    else:
        kind = "an object"
    if optional:
        kind += ", or null if the rep did not state it"
    # The description carries what each code MEANS — without it the model cannot
    # know that a "SS round cup" is "ss" — so it goes into the contract too.
    note = (field.description or "").strip()
    return f"  {name}: {kind}" + (f"\n      {note}" if note else "")


def _json_instruction():
    lines = [_field_spec(n, f) for n, f in JobRequest.model_fields.items()
             if n != "feeder"]
    feeder = [_field_spec(n, f) for n, f in FeederSpec.model_fields.items()]
    return ("Reply with a single JSON object and nothing else — no prose before or "
            "after it, no code fence. Every key below must be present:\n\n"
            + "\n".join(lines)
            + "\n  feeder: an object with these keys:\n"
            + "\n".join("  " + line for line in feeder)
            + "\n\nUse null for anything the rep did not state. Never invent a value to "
              "fill a key, and never substitute your own wording for one of the listed "
              "values — if the rep's wording does not match one of them exactly, use null "
              "and say why in ambiguities.")


JSON_INSTRUCTION = _json_instruction()


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

    client = anthropic.Anthropic(timeout=TIMEOUT_S, max_retries=1)

    # Why this asks for JSON in an ordinary message rather than using
    # `messages.parse(output_format=JobRequest)`:
    #
    # Structured outputs would be the better tool — the API constrains the model to
    # the schema, so the reply cannot come back malformed. It is not usable for THIS
    # schema. JobRequest has 20 fields, a nested FeederSpec and six enums, and the
    # API answers "Schema is too complex" to it — sometimes rejecting in under a
    # second, sometimes hanging past a 180s timeout, while plain calls generating
    # the same number of tokens return in about fifteen. Trimming the schema flat
    # did not clear it either.
    #
    # So the contract goes in the prompt instead (JSON_INSTRUCTION, generated from
    # JobRequest so it cannot drift from what will actually validate) and the reply
    # is validated here against the same model. That gives up the API-side guarantee,
    # which is why _parse_json_reply refuses anything it is not sure of rather than
    # half-reading it.
    #
    # To go back to structured outputs if the limit lifts: call client.messages.parse
    # with output_format=JobRequest and drop JSON_INSTRUCTION from the system prompt.
    # tests/test_json_fallback.py covers this path and needs no API key.
    try:
        reply = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS,
            system=SYSTEM + "\n\n" + JSON_INSTRUCTION,
            messages=[{"role": "user", "content": text}],
        )
    except Exception as e:                         # noqa: BLE001 - surface, don't 500
        raise InterpretError(f"Could not read that request: {e}") from e
    if reply.stop_reason == "refusal":
        raise InterpretError("That request was declined by the model. Fill the quote in by hand.")
    return _parse_json_reply(reply)


def _text_of(reply):
    """Concatenate the text blocks, skipping thinking and any other block type."""
    return "".join(getattr(b, "text", "") for b in reply.content if b.type == "text")


def _parse_json_reply(reply):
    """The model's reply -> JobRequest, or InterpretError with something actionable.

    Strict on purpose: this path has no API-side schema, so it is the only thing
    standing between a malformed reply and a wrong quote.
    """
    raw = _text_of(reply).strip()
    if raw.startswith("```"):                       # ```json ... ``` fence
        raw = raw.split("```", 2)[1]
        raw = raw.split("\n", 1)[1] if raw.lower().startswith("json") else raw
        raw = raw.rsplit("```", 1)[0]
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise InterpretError("Could not read that request. Try rephrasing it, or fill the "
                             "quote in by hand.")
    try:
        data = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        raise InterpretError("Could not read that request. Try rephrasing it, or fill the "
                             "quote in by hand.") from e
    try:
        return JobRequest.model_validate(data)
    except ValidationError as e:
        raise InterpretError(
            "That request came back in a shape the quote builder could not use. Try "
            "rephrasing it, or fill the quote in by hand.") from e
