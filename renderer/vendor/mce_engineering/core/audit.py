"""Audit store: every sizing run is saved with an index number, date, inputs,
overrides, results and flags (standing MCE rule).

Records are append-only: an index number is never reused and a record file is
never overwritten. Each record carries a SHA-256 of its own content so later
edits are detectable.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

DEFAULT_ROOT = Path(os.environ.get("MCE_AUDIT_ROOT", Path(__file__).resolve().parents[2] / "outputs" / "audit"))


class AuditRecord(BaseModel):
    index: str
    family: str
    job_number: str
    timestamp: str
    calculator_version: str
    inputs: dict[str, Any]
    overrides: list[dict[str, Any]]
    results: dict[str, Any]
    flags: list[dict[str, Any]]
    files: list[str] = []
    sha256: str = ""


def _digest(rec: dict) -> str:
    body = {k: v for k, v in rec.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


class AuditStore:
    def __init__(self, root: Path | str = DEFAULT_ROOT):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_file = self.root / "index.jsonl"

    def _lock(self):
        lock = self.root / ".lock"
        for _ in range(200):
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return lock
            except FileExistsError:
                time.sleep(0.025)
        raise TimeoutError(f"audit store locked: {lock}")

    def _next_index(self, prefix: str) -> str:
        n = 0
        if self.index_file.exists():
            for line in self.index_file.read_text().splitlines():
                idx = json.loads(line)["index"]
                if idx.startswith(prefix + "-"):
                    n = max(n, int(idx.rsplit("-", 1)[1]))
        return f"{prefix}-{n + 1:06d}"

    def record(self, *, prefix: str, family: str, job_number: str, calculator_version: str,
               inputs: dict, overrides: list, results: dict, flags: list, files: list[str] | None = None) -> AuditRecord:
        lock = self._lock()
        try:
            index = self._next_index(prefix)
            rec = AuditRecord(
                index=index, family=family, job_number=job_number,
                timestamp=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                calculator_version=calculator_version, inputs=inputs, overrides=overrides,
                results=results, flags=flags, files=files or [],
            ).model_dump(mode="json")
            rec["sha256"] = _digest(rec)
            path = self.root / f"{index}.json"
            with open(path, "x") as fh:  # "x": never overwrite
                json.dump(rec, fh, indent=2, default=str)
            with open(self.index_file, "a") as fh:
                fh.write(json.dumps({"index": index, "job_number": job_number, "family": family,
                                     "timestamp": rec["timestamp"]}) + "\n")
            return AuditRecord.model_validate(rec)
        finally:
            lock.unlink(missing_ok=True)

    def attach_files(self, index: str, files: list[str]) -> None:
        """Files (report PDF, job_params.json) are listed in a sidecar, so the sealed record is untouched."""
        side = self.root / f"{index}.files.json"
        existing = json.loads(side.read_text()) if side.exists() else []
        side.write_text(json.dumps(existing + files, indent=2))

    def load(self, index: str) -> AuditRecord:
        return AuditRecord.model_validate(json.loads((self.root / f"{index}.json").read_text()))

    def verify(self, index: str) -> bool:
        rec = json.loads((self.root / f"{index}.json").read_text())
        return rec.get("sha256") == _digest(rec)
