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
  RENDERER_DATA_DIR  where quotes are stored (default renderer/data)
  CHROMIUM_PATH      default: auto-detect the playwright chromium
  TWENTY_URL / TWENTY_EMAIL / TWENTY_PASSWORD   only needed for /crm

Security: this service exposes every quote and MCE's internal sizing and pricing
data. It must not be published straight to the internet — in production it binds
to localhost and is reached only through Caddy, which enforces basic auth.
"""
import hmac
import os
import pathlib

from flask import (Flask, abort, redirect, render_template, request,
                   send_from_directory, session, url_for)

import calculators
from builder import bp as builder_bp
from crm import bp as crm_bp

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
    "rotary-cooler": ("Rotary Cooler Sizing", "rotary-cooler-sizing-calculator.html",
                      "Direct air-swept drum — psychrometrics, drum selection, "
                      "drive and fan, with a summer sweep."),
}

app = Flask(__name__, static_folder="assets", static_url_path="/assets")
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)
app.register_blueprint(builder_bp)
app.register_blueprint(crm_bp)

RENDERER_PASSWORD = os.environ.get("RENDERER_PASSWORD") or ""


@app.before_request
def _gate():
    """Optional app-level password gate — see RENDERER_PASSWORD above."""
    if not RENDERER_PASSWORD or session.get("ok"):
        return None
    if request.endpoint in ("login", "static"):
        return None
    return redirect(url_for("login", next=request.full_path))


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
