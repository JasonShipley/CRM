#!/usr/bin/env python3
"""Who may sign in, and as what.

Two kinds of people use the quote builder:

  staff    anyone at a work domain (ALLOWED_EMAIL_DOMAINS, default usemce.com).
           They need no setup: the first sign-in creates the account. Staff see
           everything — every quote, the CRM list, MCE's own calculators and the
           pricing basis.
  dealer   a person at one of MCE's dealers. They exist only once someone at MCE
           adds them (/admin/users), and they see only their own dealership's
           quotes, at list price, with nothing internal: no costs, no vendor
           names, no pricing basis, no internal open items (dealer_view.py).

Sign-in is an emailed one-time code (codes.py); there are no passwords to leak or
reset. Accounts live in users.json in the data volume, beside the quotes.
"""
import datetime
import json
import os
import pathlib
import re

DATA_DIR = pathlib.Path(os.environ.get("RENDERER_DATA_DIR")
                        or (pathlib.Path(__file__).resolve().parent / "data"))
USERS_FILE = DATA_DIR / "users.json"

STAFF_DOMAINS = [d.strip().lower() for d in
                 (os.environ.get("ALLOWED_EMAIL_DOMAINS") or "usemce.com").split(",")
                 if d.strip()]
STAFF_DEALERSHIP = "MCE"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _read():
    try:
        return json.loads(USERS_FILE.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def _write(users):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(users, indent=1, sort_keys=True))
    tmp.replace(USERS_FILE)
    try:
        USERS_FILE.chmod(0o600)
    except OSError:
        pass


def normalise(email):
    return (email or "").strip().lower()


def is_staff_email(email):
    email = normalise(email)
    return bool(EMAIL_RE.match(email)) and email.rsplit("@", 1)[-1] in STAFF_DOMAINS


def get(email):
    """The account for an address, or None if it may not sign in.

    A staff address always has one (made on first use). A dealer has one only
    if MCE added it and has not switched it off."""
    email = normalise(email)
    if not EMAIL_RE.match(email):
        return None
    user = _read().get(email)
    if is_staff_email(email):
        base = {"email": email, "role": "staff", "dealership": STAFF_DEALERSHIP,
                "name": "", "active": True}
        if user:
            base.update({k: user[k] for k in ("name", "active", "lastLogin", "created")
                         if k in user})
            base["role"] = "staff"            # a work address is never demoted
            base["dealership"] = STAFF_DEALERSHIP
        return base if base.get("active", True) else None
    if not user or user.get("role") != "dealer" or not user.get("active", True):
        return None
    return dict(user)


def session_user(user):
    """What goes into the browser session — nothing that is not needed."""
    return {"email": user["email"], "role": user["role"],
            "dealership": user.get("dealership") or "",
            "name": user.get("name") or ""}


def touch_login(email):
    email = normalise(email)
    users = _read()
    user = users.get(email) or {"email": email, "created": _now()}
    if is_staff_email(email):
        user.update({"role": "staff", "dealership": STAFF_DEALERSHIP})
        user.setdefault("active", True)
    user["lastLogin"] = _now()
    users[email] = user
    _write(users)


def save_dealer(email, name, dealership, active=True, by=""):
    """Add or edit a dealer. (user, error)."""
    email = normalise(email)
    if not EMAIL_RE.match(email):
        return None, "That is not an email address."
    if is_staff_email(email):
        return None, ("That is an MCE address — it signs in as staff already and "
                      "cannot be made a dealer.")
    dealership = (dealership or "").strip()
    if not dealership:
        return None, "Name the dealership — it decides which quotes they see."
    if dealership.upper() == STAFF_DEALERSHIP:
        return None, "MCE is not a dealership name a dealer may have."
    users = _read()
    user = users.get(email) or {"email": email, "created": _now(), "createdBy": by}
    user.update({"role": "dealer", "name": (name or "").strip()[:120],
                 "dealership": dealership[:120], "active": bool(active),
                 "updated": _now(), "updatedBy": by})
    users[email] = user
    _write(users)
    return dict(user), None


def set_active(email, active, by=""):
    email = normalise(email)
    users = _read()
    if email not in users:
        return False
    users[email]["active"] = bool(active)
    users[email]["updated"] = _now()
    users[email]["updatedBy"] = by
    _write(users)
    return True


def listing():
    """Every account on file, dealers first, then staff."""
    rows = list(_read().values())
    for r in rows:
        if is_staff_email(r.get("email")):
            r["role"] = "staff"
            r["dealership"] = STAFF_DEALERSHIP
    rows.sort(key=lambda r: (r.get("role") != "dealer", (r.get("dealership") or "").lower(),
                             r.get("email") or ""))
    return rows
