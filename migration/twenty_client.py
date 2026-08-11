#!/usr/bin/env python3
"""Minimal Twenty CRM API client for the MCE migration.

Auth: reads email/password from deploy/credentials.local (never committed).
Exposes gql() for the workspace API (/graphql) and metadata API (/metadata).
"""
import json
import pathlib
import sys
import urllib.request

BASE = "http://localhost:3000"
REPO = pathlib.Path(__file__).resolve().parent.parent
CREDS = REPO / "deploy" / "credentials.local"


class TwentyError(RuntimeError):
    pass


def _post(endpoint, payload, token=None):
    req = urllib.request.Request(
        BASE + endpoint,
        data=json.dumps(payload).encode(),
        headers={
            "content-type": "application/json",
            **({"authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def gql(query, variables=None, token=None, endpoint="/graphql", allow_errors=False):
    out = _post(endpoint, {"query": query, "variables": variables or {}}, token)
    if out.get("errors") and not allow_errors:
        raise TwentyError(json.dumps(out["errors"])[:2000])
    return out


def login():
    """Full auth flow -> workspace access token."""
    creds = {}
    for line in CREDS.read_text().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            creds[k.strip().lower()] = v.strip()
    email, password = creds["email"], creds["password"]

    d = gql(
        f'mutation {{ getLoginTokenFromCredentials(email: "{email}", '
        f'password: "{password}", origin: "{BASE}") '
        "{ loginToken { token } } }",
        endpoint="/metadata",
    )["data"]
    login_token = d["getLoginTokenFromCredentials"]["loginToken"]["token"]
    d = gql(
        f'mutation {{ getAuthTokensFromLoginToken(loginToken: "{login_token}", '
        f'origin: "{BASE}") {{ tokens {{ accessOrWorkspaceAgnosticToken {{ token }} }} }} }}',
        endpoint="/metadata",
    )["data"]
    return d["getAuthTokensFromLoginToken"]["tokens"]["accessOrWorkspaceAgnosticToken"]["token"]


if __name__ == "__main__":
    tok = login()
    print(tok if "--print-token" in sys.argv else "login OK")
