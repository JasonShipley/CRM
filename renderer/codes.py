#!/usr/bin/env python3
"""One-time email codes — the one way anybody proves who they are here.

Two things use it: signing in to the app (people, dealers included) and issuing
an API token (agents, work addresses only). Both mail a six-digit code to an
address and accept it once, so the mechanics live here once:

    code = codes.issue(email, "login")       # then codes.send(...) mails it
    ok, error = codes.verify(email, "login", "123456")

A code is stored only as a hash, lasts 15 minutes, survives five wrong guesses,
and a new one cannot be asked for within 30 seconds of the last. Codes for
different purposes never stand in for each other — a token code does not sign
anybody in.
"""
import hashlib
import hmac
import json
import logging
import os
import pathlib
import secrets
import smtplib
import time
from email.message import EmailMessage

DATA_DIR = pathlib.Path(os.environ.get("RENDERER_DATA_DIR")
                        or (pathlib.Path(__file__).resolve().parent / "data"))
CODE_FILE = DATA_DIR / "one_time_codes.json"

CODE_TTL_S = 15 * 60
MAX_ATTEMPTS = 5
RESEND_AFTER_S = 30

log = logging.getLogger("mce.codes")


def _read():
    try:
        return json.loads(CODE_FILE.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def _write(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CODE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True))
    tmp.replace(CODE_FILE)
    try:
        CODE_FILE.chmod(0o600)
    except OSError:
        pass


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _key(email, purpose):
    return f"{purpose}|{(email or '').strip().lower()}"


def issue(email, purpose, throttle=False):
    """A fresh code for this address and purpose. (code, error).

    `throttle` is for requests that come in over the web, so nobody can flood
    an inbox; code that issues directly (tests, an admin) skips it."""
    pending = _read()
    key = _key(email, purpose)
    now = time.time()
    last = pending.get(key)
    if throttle and last and now - last.get("issued", 0) < RESEND_AFTER_S:
        return None, "A code was just sent — give it a moment, then check your inbox."
    code = f"{secrets.randbelow(1_000_000):06d}"
    pending[key] = {"code_hash": _hash(code), "issued": now,
                    "expires": now + CODE_TTL_S, "attempts": 0}
    # drop anything long expired while we are here
    pending = {k: v for k, v in pending.items() if v.get("expires", 0) > now - 3600}
    _write(pending)
    return code, None


def verify(email, purpose, code):
    """Accept a code once. (True, None) or (False, a reason a person can act on)."""
    pending = _read()
    key = _key(email, purpose)
    entry = pending.get(key)
    if not entry:
        return False, "Ask for a code first."
    if time.time() > entry["expires"]:
        pending.pop(key, None)
        _write(pending)
        return False, "That code has expired. Ask for another."
    if entry["attempts"] >= MAX_ATTEMPTS:
        pending.pop(key, None)
        _write(pending)
        return False, "Too many attempts. Ask for another code."
    if not hmac.compare_digest(entry["code_hash"], _hash((code or "").strip())):
        entry["attempts"] += 1
        _write(pending)
        return False, "That code doesn't match."
    pending.pop(key, None)
    _write(pending)
    return True, None


def send(email, code, subject="Your MCE quote builder code", default_from=None):
    """Mail a code. Without SMTP_HOST it goes to the service log and returns False."""
    host = os.environ.get("SMTP_HOST")
    body = (f"Your code is {code}\n\nIt is good for 15 minutes. If you did not ask "
            "for it, ignore this message and nothing happens.")
    if not host:
        log.warning("No SMTP_HOST set — code for %s is %s", email, code)
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("SMTP_FROM") or default_from or "quotes@usemce.com"
    msg["To"] = email
    msg.set_content(body)
    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls()
        user = os.environ.get("SMTP_USER")
        if user:
            smtp.login(user, os.environ.get("SMTP_PASSWORD", ""))
        smtp.send_message(msg)
    return True
