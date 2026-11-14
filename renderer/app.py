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

  GET  /login                 email -> one-time code sign-in        (accounts.py)
  GET  /admin/users           dealers and staff, staff only

Config (env):
  SECRET_KEY         Flask session key. Set it — without one every restart signs
                     everybody out.
  SESSION_COOKIE_SECURE  1 (default) sends the session cookie over HTTPS only.
  RENDERER_DATA_DIR  where quotes and API tokens are stored (default renderer/data)
  ALLOWED_EMAIL_DOMAINS  who may issue themselves an API token (default usemce.com)
  SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM
                     mail for the one-time codes. Without SMTP_HOST the code is
                     written to the service log instead, which is fine for a first
                     token but not for self-service.
  CHROMIUM_PATH      default: auto-detect the playwright chromium
  TWENTY_URL / TWENTY_EMAIL / TWENTY_PASSWORD   only needed for /crm

Security: this service holds every quote and MCE's internal sizing and pricing
data, and since dealers came on it is the only gate in front of them — Caddy
passes everything through (deploy/Caddyfile). Every page and API needs a signed-in
person or an API token (see _gate). Staff see everything; a dealer reaches only
DEALER_ENDPOINTS, sees only their own dealership's quotes, and gets every answer
through dealer_view.py. It still binds to localhost and is reached through Caddy.
"""
import datetime
import os
import pathlib

from flask import (Flask, abort, g, jsonify, redirect, render_template, request,
                   send_from_directory, session, url_for)

import accounts
import calculators
import codes
from builder import bp as builder_bp
from crm import bp as crm_bp
import tokens
from voice import bp as voice_bp

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
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "1") != "0",
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=30),
)
app.register_blueprint(builder_bp)
app.register_blueprint(crm_bp)
app.register_blueprint(voice_bp)

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

# Everything a dealer may reach. An allowlist on purpose: a page added later is
# staff-only until someone decides a dealer should see it. Not here, and so
# staff-only: /crm, /tools (MCE's own calculator pages carry the pricing
# multipliers and vendor costs), /api/pricing, /api/tokens, /admin.
DEALER_ENDPOINTS = {"logout", "static",
                    "builder.index", "builder.new_quote", "builder.edit_quote",
                    "builder.quote_view", "builder.quote_pdf",
                    "builder.api_interpret", "builder.api_calc", "builder.api_create",
                    "builder.api_update", "builder.api_delete",
                    "voice.session", "voice.equipment", "voice.fields",
                    "voice.size", "voice.draft"}

# Everything under this prefix is passed through Caddy without basic auth so
# bearer headers survive, so this app is the only guard in front of it.
API_PREFIX = "/api/"


def _is_api(path):
    return path.startswith(API_PREFIX) or path == API_PREFIX.rstrip("/")


@app.before_request
def _gate():
    """A signed-in person, or an agent with a bearer token. Nobody else.

    People sign in at /login with an emailed code (accounts.py). Staff reach
    everything; a dealer reaches DEALER_ENDPOINTS only. An agent presents
    `Authorization: Bearer mceq_...`, issued to a work address (tokens.py), which
    reaches the quote and calculator APIs only.

    Caddy passes every request straight through, so this function is the ONLY
    thing in front of MCE's quotes and pricing. An account switched off in
    /admin/users is refused on its very next request, not when its session ends.
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
        g.user = {"email": who["email"], "role": "staff",
                  "dealership": accounts.STAFF_DEALERSHIP, "name": ""}
        return None

    signed_in = session.get("user")
    user = accounts.get(signed_in["email"]) if signed_in else None
    if not user:
        session.pop("user", None)
        if _is_api(request.path):
            return jsonify({
                "error": "Sign in first, or use an API token.",
                "how": "People sign in at /login. Agents: POST /api/tokens/request "
                       "with a work email, then /api/tokens/confirm with the code.",
                "use": "Authorization: Bearer <token>",
            }), 401
        return redirect(url_for("login", next=request.full_path))

    g.user = accounts.session_user(user)
    if g.user["role"] == "dealer" and request.endpoint not in DEALER_ENDPOINTS:
        if _is_api(request.path):
            return jsonify({"error": "That is not available on a dealer account."}), 403
        return render_template("error.html", nav="", title="Not available",
                               message="That page is for MCE staff only."), 403
    return None


@app.context_processor
def _who():
    user = getattr(g, "user", None)
    return {"me": user, "is_staff": bool(user and user.get("role") == "staff")}


def _send_code(email, code):
    """Email a one-time code. Falls back to the log when no SMTP is configured."""
    try:
        return codes.send(email, code,
                          default_from=f"quotes@{tokens.ALLOWED_DOMAINS[0]}")
    except Exception as e:                     # noqa: BLE001 — say so, don't 500
        app.logger.error("Could not send the code to %s: %s", email, e)
        return False


@app.route("/api/tokens/request", methods=["POST"])
def api_token_request():
    """Ask for a one-time code. Work addresses only."""
    payload = request.get_json(silent=True) or request.form.to_dict()
    email = (payload.get("email") or "").strip()
    code, error = tokens.request_code(email, throttle=True)
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


def _safe_next(nxt):
    """Only ever bounce back to a path on this host."""
    nxt = nxt or ""
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("builder.index")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Email in, code out, signed in. No passwords anywhere.

    The reply to an address is the same whether or not it may sign in, so the
    page cannot be used to find out who MCE's dealers are."""
    nxt = request.values.get("next") or ""
    if request.method == "GET":
        if session.get("user") and accounts.get(session["user"]["email"]):
            return redirect(_safe_next(nxt))
        return render_template("login.html", step="email", next=nxt)

    email = accounts.normalise(request.form.get("email"))
    if request.form.get("step") == "code":
        ok, error = codes.verify(email, "login", request.form.get("code"))
        user = accounts.get(email) if ok else None
        if not user:
            return render_template("login.html", step="code", email=email, next=nxt,
                                   error=error or "That code doesn't match."), 401
        accounts.touch_login(email)
        session.clear()
        session["user"] = accounts.session_user(user)
        session.permanent = True
        return redirect(_safe_next(nxt))

    if not accounts.EMAIL_RE.match(email):
        return render_template("login.html", step="email", next=nxt,
                               error="Enter your email address."), 400
    note = None
    if not os.environ.get("SMTP_HOST"):
        # said for every address alike, so it gives away nothing about who has access
        note = ("Mail is not set up on this server yet, so codes go to the service "
                "log. Ask MCE for yours.")
    if accounts.get(email):
        code, error = codes.issue(email, "login", throttle=True)
        if code:
            _send_code(email, code)
        elif error:
            note = error
    return render_template("login.html", step="code", email=email, next=nxt, note=note)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    """Add, edit and switch off dealers. Staff only (not in DEALER_ENDPOINTS)."""
    message = error = None
    if request.method == "POST":
        by = g.user["email"]
        action = request.form.get("action")
        email = request.form.get("email")
        if action == "save":
            user, error = accounts.save_dealer(
                email, request.form.get("name"), request.form.get("dealership"),
                active=request.form.get("active", "1") == "1", by=by)
            if user:
                message = f"Saved {user['email']} ({user['dealership']})."
        elif action in ("disable", "enable"):
            if accounts.set_active(email, action == "enable", by=by):
                message = f"{accounts.normalise(email)} " + (
                    "can sign in again." if action == "enable" else
                    "is switched off — signed out on their next click.")
            else:
                error = "No such account."
    return render_template("admin_users.html", nav="admin",
                           users=accounts.listing(), message=message, error=error), (
                               400 if error else 200)


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
