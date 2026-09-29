#!/usr/bin/env python3
"""MCE Quoting — quote form builder, sizing calculators and branded quote PDFs.

The builder stands alone: quotes live in local JSON (quotes_store.py), sizing
runs against Python ports of MCE's own calculators (calculators/), and the PDF is
MCE's Equipment Proposal layout (templates/quote.html). Twenty CRM is optional —
when it is reachable, /crm lists and renders quotes held in the CRM with the same
template, which is the path the builder will write to once the CRM tie-in lands.

Routes:
  GET  /                      quotes built here
  GET  /quotes/new            the quote form builder          (builder.py)
  GET  /quotes/<id>[/pdf]     branded web view / PDF          (builder.py)
  GET  /tools                 MCE's own calculators, hosted
  GET  /tools/<slug>          one calculator, served whole
  GET  /crm                   quotes in Twenty CRM            (crm.py)

Config (env):
  RENDERER_PASSWORD  optional app-level password gate. Leave unset in production,
                     where Caddy already enforces basic auth (deploy/Caddyfile).
  SECRET_KEY         Flask session key. Required if RENDERER_PASSWORD is set,
                     otherwise logins do not survive a restart.
  RENDERER_DATA_DIR  where quotes and API tokens are stored (default renderer/data)
  ALLOWED_EMAIL_DOMAINS  who may issue themselves an API token (default usemce.com)
  SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM
                     mail for the one-time codes. Without SMTP_HOST the code is
                     written to the service log instead, which is fine for a first
                     token but not for self-service.
  CHROMIUM_PATH      default: auto-detect the playwright chromium
  TWENTY_URL / TWENTY_EMAIL / TWENTY_PASSWORD   only needed for /crm

Security: this service exposes every quote and MCE's internal sizing and pricing
data. It must not be published straight to the internet — in production it binds
to localhost and is reached only through Caddy. Caddy enforces basic auth on
everything a person uses; /api/ is passed through because it carries its own
bearer tokens, and an invalid one is refused here (see _gate).
"""
import hmac
import os
import pathlib

from flask import (Flask, abort, g, jsonify, redirect, render_template, request,
                   send_from_directory, session, url_for)

import calculators
from builder import bp as builder_bp
from crm import bp as crm_bp
import tokens

ROOT = pathlib.Path(__file__).resolve().parent
TOOLS_DIR = ROOT / "tools"

# slug -> the calculator file MCE maintains, served byte for byte
TOOLS = {
    "hammermill": ("Hammermill Sizing", "hammermill-sizing-calculator.html",
                   "Full mill sizing workbench — index chart, model reference "
                   "table, feeder and screw tables, and package pricing."),
    "cooler": ("Counterflow Cooler Sizing", "counterflow-cooler-sizing-calculator.html",
               "Cooler model, air system and option pricing, for pellets and meal."),
    "baghouse": ("Baghouse Filter", "baghouse-filter-calculator.html",
                 "Cloth area, MCE model and the Kice PneuJet equivalent."),
    "cyclone": ("Cyclone CFM", "cyclone-cfm-calculator.html",
                "Rated CFM to an MCE HE/H or budget cyclone, with the full "
                "dimension and weight charts."),
    "hammer-pattern": ("Hammer Pattern", "hammer-pattern-calculator.html",
                       "Hammer count, balanced row split and pin stack, against "
                       "the 38/44-40 reference pattern."),
    "duct": ("Duct Sizing", "duct-sizing-calculator.html",
             "Airflow to duct diameter at the conveying velocity, and back."),
    "fan": ("Fan Sizing", "fan-sizing-calculator.html",
            "Duty to fan selection — density factor, brake HP, motor, wheel and "
            "line size, with the RFQ block MCE sends to AirPro or IAP."),
    "xf-fan": ("XF Fan Duty & Curve", "xf-fan-sizing-calculator.html",
               "MCE's own XF / LS series: duct system resistance, the capacity "
               "tables from Bulletin 251, RPM and BHP interpolated at the duty, "
               "max safe speed, and the fan curve against the system curve."),
    "rotary-cooler": ("Rotary Cooler Sizing", "rotary-cooler-sizing-calculator.html",
                      "Direct air-swept drum — psychrometrics, drum selection, "
                      "drive and fan, with a summer sweep."),
}

app = Flask(__name__, static_folder="assets", static_url_path="/assets")
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)
app.register_blueprint(builder_bp)
app.register_blueprint(crm_bp)

RENDERER_PASSWORD = os.environ.get("RENDERER_PASSWORD") or ""

# Endpoints an API token may reach. A token is for building quotes and reading the
# basis, not for the browser session's full run of the app.
TOKEN_ENDPOINTS = {"builder.api_interpret", "builder.api_calc", "builder.api_pricing",
                   "builder.api_create", "builder.api_update", "builder.quote_pdf",
                   "builder.quote_view",
                   # a holder manages their own tokens without asking anyone
                   "api_token_list", "api_token_revoke"}
# Endpoints anyone may reach — the token self-service flow has to work before you
# hold a token. Both still gate on the work-email domain (tokens.py), and confirm
# needs a code that was mailed to that address.
OPEN_ENDPOINTS = {"login", "static", "api_token_request", "api_token_confirm"}

# Everything under this prefix is passed through Caddy without basic auth so
# bearer headers survive, so this app is the only guard in front of it.
API_PREFIX = "/api/"


def _is_api(path):
    return path.startswith(API_PREFIX) or path == API_PREFIX.rstrip("/")


@app.before_request
def _gate():
    """Session password for people, bearer token for agents.

    A salesperson signs in at /login. An agent presents `Authorization: Bearer
    mceq_...`, which it issued itself against its work email — see tokens.py. The
    token reaches the quote and calculator APIs only.

    /api/ is the part to be careful with. Caddy routes it straight through with no
    basic auth, because a basic-auth challenge would reject the bearer header
    before this app ever saw it (deploy/Caddyfile). That makes this function the
    ONLY thing standing in front of the API — so an /api/ request must carry a
    valid token or a signed-in browser session, and RENDERER_PASSWORD being unset
    does NOT open it. Unset is the normal production setup, where Caddy holds the
    password for the pages a person uses.
    """
    if request.endpoint in OPEN_ENDPOINTS:
        return None

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        who = tokens.identify(auth[7:].strip())
        if not who:
            return jsonify({"error": "That token is not valid or has been revoked."}), 401
        if request.endpoint not in TOKEN_ENDPOINTS:
            return jsonify({"error": "This token reaches the quote and calculator "
                                     "APIs only.",
                            "allowed": sorted(TOKEN_ENDPOINTS)}), 403
        g.api_user = who
        return None

    if _is_api(request.path):
        if session.get("ok"):
            return None                       # signed in at /login in this browser
        return jsonify({
            "error": "This endpoint needs an API token.",
            "how": "POST /api/tokens/request with your work email, then "
                   "/api/tokens/confirm with the code you are sent.",
            "use": "Authorization: Bearer <token>",
        }), 401

    if not RENDERER_PASSWORD or session.get("ok"):
        return None
    return redirect(url_for("login", next=request.full_path))


def _send_code(email, code):
    """Email a one-time code. Falls back to the log when no SMTP is configured."""
    host = os.environ.get("SMTP_HOST")
    subject = "Your MCE quote builder code"
    body = (f"Your code is {code}\n\nIt is good for 15 minutes. If you did not ask "
            "for it, ignore this message and nothing happens.")
    if not host:
        app.logger.warning("No SMTP_HOST set — code for %s is %s", email, code)
        return False
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("SMTP_FROM", f"quotes@{tokens.ALLOWED_DOMAINS[0]}")
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


@app.route("/api/tokens/request", methods=["POST"])
def api_token_request():
    """Ask for a one-time code. Work addresses only."""
    payload = request.get_json(silent=True) or request.form.to_dict()
    email = (payload.get("email") or "").strip()
    code, error = tokens.request_code(email)
    if error:
        return jsonify({"error": error}), 400
    sent = _send_code(email, code)
    return jsonify({
        "sent": sent, "email": email.lower(),
        "message": ("A six-digit code is on its way — it is good for 15 minutes."
                    if sent else
                    "Mail is not configured on this server, so the code was written "
                    "to the service log instead. Ask whoever runs the box for it, or "
                    "set SMTP_HOST."),
    })


@app.route("/api/tokens/confirm", methods=["POST"])
def api_token_confirm():
    """Exchange the code for a token. Shown once — it is not recoverable."""
    payload = request.get_json(silent=True) or request.form.to_dict()
    token, error = tokens.confirm_code(payload.get("email"), payload.get("code"),
                                       label=payload.get("label", ""))
    if error:
        return jsonify({"error": error}), 400
    return jsonify({
        "token": token,
        "note": "Copy it now — it is stored only as a hash and cannot be shown again.",
        "use": "Authorization: Bearer <token>",
    })


@app.route("/api/tokens")
def api_token_list():
    """Your own tokens, or everyone's from a browser session."""
    who = getattr(g, "api_user", None)
    return jsonify({"tokens": tokens.listing(who["email"] if who else None)})


@app.route("/api/tokens/<token_id>/revoke", methods=["POST"])
def api_token_revoke(token_id):
    who = getattr(g, "api_user", None)
    ok = tokens.revoke(token_id, who["email"] if who else None)
    return jsonify({"revoked": ok}), (200 if ok else 404)


@app.route("/login", methods=["GET", "POST"])
def login():
    if not RENDERER_PASSWORD:
        return redirect(url_for("builder.index"))
    error = None
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("password", ""), RENDERER_PASSWORD):
            session["ok"] = True
            session.permanent = True
            nxt = request.args.get("next") or ""
            # only ever bounce back to a path on this host
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//")
                            else url_for("builder.index"))
        error = "That password doesn't match."
    return render_template("login.html", error=error), (401 if error else 200)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login") if RENDERER_PASSWORD else url_for("builder.index"))


@app.route("/tools")
def tools_index():
    return render_template("tools.html", nav="tools", tools=TOOLS,
                           planned=calculators.PLANNED,
                           not_ported=calculators.NOT_PORTED)


@app.route("/tools/<slug>")
def tool(slug):
    """Serve one of MCE's calculators exactly as MCE maintains it.

    These are the engineering source of truth, hosted here so the team reaches
    them behind the same login instead of passing files around desktops. They are
    served unmodified — the quote builder uses the Python ports of the same math.
    """
    entry = TOOLS.get(slug)
    if not entry:
        abort(404)
    return send_from_directory(TOOLS_DIR, entry[1])


@app.errorhandler(404)
def _not_found(_e):
    return render_template("error.html", nav="", title="Not found",
                           message="That page doesn't exist."), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8090")))
