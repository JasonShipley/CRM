#!/usr/bin/env python3
"""API tokens, issued by the people who need them.

A salesperson or an agent that wants to build quotes through the API should not
have to wait for someone to mint a credential by hand. So the rule is simple:
prove you hold a work mailbox, and the service issues you a token.

    POST /api/tokens/request   {"email": "jb@usemce.com", "label": "JB's laptop"}
        -> emails a six-digit code to that address, if the domain is allowed
    POST /api/tokens/confirm   {"email": ..., "code": "123456"}
        -> {"token": "mceq_..."} shown ONCE and never again

The token is stored only as a SHA-256 hash, the way a password would be, so a
copy of the data directory does not hand anyone the keys. Every call records a
last-used stamp, and any token can be revoked without touching the others.

Domains are set by ALLOWED_EMAIL_DOMAINS (default usemce.com). Nothing outside
them can get a token, so this is self-service within the company and closed to
everyone else.
"""
import datetime
import hashlib
import hmac
import json
import os
import pathlib
import re
import secrets
import time

DATA_DIR = pathlib.Path(os.environ.get("RENDERER_DATA_DIR")
                        or (pathlib.Path(__file__).resolve().parent / "data"))
TOKEN_FILE = DATA_DIR / "api_tokens.json"
PENDING_FILE = DATA_DIR / "api_token_codes.json"

ALLOWED_DOMAINS = [d.strip().lower() for d in
                   (os.environ.get("ALLOWED_EMAIL_DOMAINS") or "usemce.com").split(",")
                   if d.strip()]
CODE_TTL_S = 15 * 60
MAX_ATTEMPTS = 5
PREFIX = "mceq_"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _read(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def _write(path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True))
    tmp.replace(path)
    try:
        path.chmod(0o600)          # tokens are hashes, but the list is still private
    except OSError:
        pass


def domain_allowed(email):
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        return False
    return email.rsplit("@", 1)[-1] in ALLOWED_DOMAINS


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def request_code(email):
    """Issue a one-time code for a work address. (code, error)."""
    email = (email or "").strip().lower()
    if not domain_allowed(email):
        return None, ("That address is not on a work domain. Tokens are issued to "
                      + " or ".join("@" + d for d in ALLOWED_DOMAINS) + " addresses.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    pending = _read(PENDING_FILE)
    pending[email] = {"code_hash": _hash(code), "expires": time.time() + CODE_TTL_S,
                      "attempts": 0}
    _write(PENDING_FILE, pending)
    return code, None


def confirm_code(email, code, label=""):
    """Exchange a valid code for a token. (token, error) — token shown once."""
    email = (email or "").strip().lower()
    pending = _read(PENDING_FILE)
    entry = pending.get(email)
    if not entry:
        return None, "Ask for a code first."
    if time.time() > entry["expires"]:
        pending.pop(email, None)
        _write(PENDING_FILE, pending)
        return None, "That code has expired. Ask for another."
    if entry["attempts"] >= MAX_ATTEMPTS:
        pending.pop(email, None)
        _write(PENDING_FILE, pending)
        return None, "Too many attempts. Ask for another code."
    if not hmac.compare_digest(entry["code_hash"], _hash((code or "").strip())):
        entry["attempts"] += 1
        _write(PENDING_FILE, pending)
        return None, "That code doesn't match."

    pending.pop(email, None)
    _write(PENDING_FILE, pending)
    token = PREFIX + secrets.token_urlsafe(32)
    tokens = _read(TOKEN_FILE)
    tokens[_hash(token)] = {
        "email": email, "label": label or "",
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "last_used": None, "revoked": False,
    }
    _write(TOKEN_FILE, tokens)
    return token, None


def identify(token):
    """The owner of a token, or None. Records the call."""
    if not token or not token.startswith(PREFIX):
        return None
    tokens = _read(TOKEN_FILE)
    entry = tokens.get(_hash(token))
    if not entry or entry.get("revoked"):
        return None
    entry["last_used"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat(timespec="seconds")
    _write(TOKEN_FILE, tokens)
    return {"email": entry["email"], "label": entry.get("label", "")}


def listing(email=None):
    """Tokens, without anything that could be used as one."""
    out = []
    for h, e in sorted(_read(TOKEN_FILE).items(), key=lambda kv: kv[1]["created"]):
        if email and e["email"] != email:
            continue
        out.append({"id": h[:12], "email": e["email"], "label": e.get("label", ""),
                    "created": e["created"], "last_used": e.get("last_used"),
                    "revoked": bool(e.get("revoked"))})
    return out


def revoke(token_id, email=None):
    """Revoke by the short id from listing(). Scoped to an owner when given."""
    tokens = _read(TOKEN_FILE)
    for h, e in tokens.items():
        if h.startswith(token_id) and (email is None or e["email"] == email):
            e["revoked"] = True
            _write(TOKEN_FILE, tokens)
            return True
    return False
