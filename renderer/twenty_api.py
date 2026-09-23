#!/usr/bin/env python3
"""Twenty CRM client shared by the quote renderer and the quote form builder.

Holds the login/token dance, the GraphQL transport, and the money/date helpers
that both sides format with. No Flask in here.
"""
import json
import os
import pathlib
import time
import urllib.error
import urllib.request
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
TWENTY_URL = os.environ.get("TWENTY_URL", "http://localhost:3000")
# Origin presented during login (must match Twenty's SERVER_URL); defaults to TWENTY_URL
TWENTY_ORIGIN = os.environ.get("TWENTY_ORIGIN", TWENTY_URL)

_token = {"value": None, "at": 0}


class TwentyError(RuntimeError):
    """A GraphQL or transport error talking to Twenty."""


def _creds():
    """CRM login, from the environment or deploy/credentials.local.

    Raises TwentyError rather than letting a missing file escape as an OSError:
    the builder does not need the CRM, so "not configured" has to read as a
    message on the CRM page, not a 500 across the app.
    """
    email = os.environ.get("TWENTY_EMAIL")
    password = os.environ.get("TWENTY_PASSWORD")
    if email and password:
        return email, password
    path = REPO / "deploy" / "credentials.local"
    try:
        text = path.read_text()
    except OSError as e:
        raise TwentyError(
            "No CRM credentials: set TWENTY_EMAIL and TWENTY_PASSWORD, or create "
            f"{path}.") from e
    creds = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            creds[k.strip().lower()] = v.strip()
    if not creds.get("email") or not creds.get("password"):
        raise TwentyError(f"{path} has no email/password line.")
    return creds["email"], creds["password"]


def gql(query, variables=None, endpoint="/graphql", token=None):
    req = urllib.request.Request(
        TWENTY_URL + endpoint,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"content-type": "application/json",
                 **({"authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.load(r)
    except urllib.error.URLError as e:
        raise TwentyError(f"Cannot reach Twenty at {TWENTY_URL}: {e}") from e
    if out.get("errors"):
        raise TwentyError(json.dumps(out["errors"])[:1000])
    return out["data"]


def auth_token():
    """A workspace token, cached for 30 minutes."""
    if _token["value"] and time.time() - _token["at"] < 1800:
        return _token["value"]
    email, password = _creds()
    d = gql('mutation L($e: String!, $p: String!, $o: String!) { '
            'getLoginTokenFromCredentials(email: $e, password: $p, origin: $o) '
            '{ loginToken { token } } }',
            {"e": email, "p": password, "o": TWENTY_ORIGIN}, endpoint="/metadata")
    lt = d["getLoginTokenFromCredentials"]["loginToken"]["token"]
    d = gql('mutation T($lt: String!, $o: String!) { '
            'getAuthTokensFromLoginToken(loginToken: $lt, origin: $o) '
            '{ tokens { accessOrWorkspaceAgnosticToken { token } } } }',
            {"lt": lt, "o": TWENTY_ORIGIN}, endpoint="/metadata")
    _token["value"] = d["getAuthTokensFromLoginToken"]["tokens"][
        "accessOrWorkspaceAgnosticToken"]["token"]
    _token["at"] = time.time()
    return _token["value"]


def query(gql_query, variables=None):
    """Run a data-API query with a fresh-enough token."""
    return gql(gql_query, variables, token=auth_token())


# ---------------------------------------------------------------- formatting --

def m2d(micros):
    """amountMicros -> dollars (float)."""
    return (micros or 0) / 1_000_000


def d2m(dollars):
    """dollars -> amountMicros (int), the shape Twenty's CURRENCY fields take."""
    return int(round(float(dollars or 0) * 1_000_000))


def fmt_money(v):
    return "${:,.2f}".format(v)


def fmt_date(iso):
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.strftime("%b %-d, %Y")
    except ValueError:
        return str(iso)[:10]
