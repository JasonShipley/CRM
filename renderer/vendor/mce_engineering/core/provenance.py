"""Traceability primitives: every value carries its source; every rule hit is a flag.

Standing MCE rule: every calculator allows manual override of any value and
flags (never blocks) rule violations. A missing source is itself a flag.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SourceKind = Literal[
    "CEMA",  # CEMA standards (350 screw conveyors, etc.)
    "AWS", "ASME", "AISC", "ASTM", "NEMA",
    "vendor",  # manufacturer catalog / price book
    "MCE",  # MCE decision or verified shop practice (docs/decisions.md, knowledge base)
    "derived",  # computed from other sourced values
    "user",  # job input supplied by the requester
    "override",  # manual override of a computed or tabulated value
    "estimate",  # agent estimate Jason asked for (D-028); always flagged until replaced with shop data
    "placeholder",  # no valid source yet; always flagged
]


class Source(BaseModel):
    kind: SourceKind
    ref: str = Field(..., description="Document + section/table/page, decision id, or formula")
    note: str = ""

    def label(self) -> str:
        return f"{self.kind}: {self.ref}" + (f" ({self.note})" if self.note else "")


class Quantity(BaseModel):
    """A named value with unit and source. Overrides keep the original value."""

    name: str
    value: Any
    unit: str = ""
    source: Source
    original_value: Any = None
    original_source: Source | None = None
    override_reason: str = ""

    @property
    def overridden(self) -> bool:
        return self.original_source is not None


Severity = Literal["info", "warning", "violation", "needs_verification", "blocked"]


class Flag(BaseModel):
    """A rule hit. 'blocked' means a required source is missing, not that the run stopped."""

    severity: Severity
    code: str
    message: str
    ref: str = ""


class Override(BaseModel):
    name: str
    value: Any
    reason: str
    by: str = ""


def apply_override(q: Quantity, ov: Override) -> Quantity:
    return Quantity(
        name=q.name, value=ov.value, unit=q.unit,
        source=Source(kind="override", ref=f"manual override by {ov.by or 'user'}", note=ov.reason),
        original_value=q.value, original_source=q.source, override_reason=ov.reason,
    )


class Ledger:
    """Collects quantities and flags during a calculation run, applying overrides as values are set."""

    def __init__(self, overrides: list[Override] | None = None):
        self.q: dict[str, Quantity] = {}
        self.flags: list[Flag] = []
        self._ov = {o.name: o for o in (overrides or [])}
        self._used: set[str] = set()

    def set(self, name: str, value: Any, unit: str, source: Source) -> Any:
        q = Quantity(name=name, value=value, unit=unit, source=source)
        if name in self._ov:
            q = apply_override(q, self._ov[name])
            self._used.add(name)
            self.flag("info", "OVERRIDE", f"{name} overridden: {q.original_value} -> {q.value} {unit} ({q.override_reason})")
        if source.kind == "placeholder" and not q.overridden:
            self.flag("needs_verification", "PLACEHOLDER", f"{name} uses a placeholder value: {source.ref}")
        self.q[name] = q
        return q.value

    def get(self, name: str) -> Any:
        return self.q[name].value

    def flag(self, severity: Severity, code: str, message: str, ref: str = "") -> None:
        self.flags.append(Flag(severity=severity, code=code, message=message, ref=ref))

    def unused_overrides(self) -> list[str]:
        return sorted(set(self._ov) - self._used)
