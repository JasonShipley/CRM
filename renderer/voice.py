#!/usr/bin/env python3
"""The voice assistant's half of the server.

The talking happens between the browser and ElevenLabs (assets/voice.js). This
module does the two things that must stay on the server:

  * POST /api/voice/session   asks ElevenLabs for a short-lived conversation
    token for MCE's agent, with ELEVENLABS_API_KEY — which never reaches the
    browser — and tells the agent who it is talking to (staff or dealer).

  * the assistant's tools. While it talks, the agent calls tools that run in the
    browser, and the browser calls these with the person's own session. So a
    dealer's assistant is a dealer: same allowlist (app.py), same filter
    (dealer_view.py), no webhook open to the internet.

      GET  /api/voice/equipment        what can be sized
      GET  /api/voice/fields/<key>     a calculator's inputs
      POST /api/voice/size/<key>       size and price one thing
      POST /api/voice/draft            a draft quote from a job, for the form

Each tool answers twice over: `summary` is a few short lines for the voice model
to read out (short is fast), and `result` / `quote` is the full answer for the
screen. Every number in either comes from MCE's calculators — the agent is told
to say nothing numeric it did not get from a tool.
"""
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError

import builder
import calculators
import dealer_view
import interpret
import quote_from_job

bp = Blueprint("voice", __name__)

API = os.environ.get("ELEVENLABS_API_URL", "https://api.elevenlabs.io").rstrip("/")
SESSIONS_PER_HOUR = int(os.environ.get("VOICE_SESSIONS_PER_HOUR", "30"))

_recent = {}
_lock = threading.Lock()


def _allow(email):
    """A few dozen conversations an hour per person — each one bills minutes."""
    now = time.time()
    with _lock:
        stamps = [t for t in _recent.get(email, []) if now - t < 3600]
        if len(stamps) >= SESSIONS_PER_HOUR:
            _recent[email] = stamps
            return False
        stamps.append(now)
        _recent[email] = stamps
        return True


def _elevenlabs(path, params):
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"xi-api-key": key})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode() or "{}")


@bp.route("/api/voice/session", methods=["POST"])
def session():
    """A conversation token for the agent, and who the agent is talking to."""
    agent = os.environ.get("ELEVENLABS_AGENT_ID", "")
    user = g.user
    if not (os.environ.get("ELEVENLABS_API_KEY") and agent):
        detail = (" (set ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID in deploy/.env)"
                  if user["role"] == "staff" else "")
        return jsonify({"error": "The voice assistant is not switched on yet" + detail
                                 + "."}), 503
    if not _allow(user["email"]):
        return jsonify({"error": "That is a lot of conversations this hour — "
                                 "try again in a little while."}), 429
    try:
        # WebRTC first: lower latency and the browser's own echo cancelling
        token = _elevenlabs("/v1/convai/conversation/token", {"agent_id": agent}).get("token")
        reply = {"conversationToken": token, "connectionType": "webrtc"}
        if not token:
            url = _elevenlabs("/v1/convai/conversation/get-signed-url",
                              {"agent_id": agent}).get("signed_url")
            reply = {"signedUrl": url, "connectionType": "websocket"}
    except (urllib.error.URLError, OSError, ValueError) as e:
        return jsonify({"error": f"Could not reach the voice service: {e}"}), 502
    if not (reply.get("conversationToken") or reply.get("signedUrl")):
        return jsonify({"error": "The voice service gave no session."}), 502
    reply["dynamicVariables"] = {
        "user_name": user.get("name") or user["email"].split("@")[0],
        "user_role": user["role"],
        "dealership": user.get("dealership") or "",
    }
    return jsonify(reply)


# ---------------------------------------------------------------- tools ---

def _money(v):
    try:
        return "${:,.0f}".format(float(v))
    except (TypeError, ValueError):
        return ""


def _line_summary(lines):
    out = []
    for l in lines or []:
        price = ("price on request" if l.get("needsPrice") or not l.get("unitPrice")
                 else _money(l.get("unitPrice")))
        qty = l.get("quantity") or 1
        out.append(f"{l.get('name')}{f' x{qty}' if str(qty) not in ('1', '1.0') else ''}"
                   f": {price}")
    return out


def calc_summary(result):
    """What the voice model needs to answer — and nothing it could misread."""
    if result.get("error"):
        return {"error": result["error"]}
    outs = [f"{o.get('label')}: {o.get('value')}{(' ' + o['unit']) if o.get('unit') else ''}"
            for o in (result.get("outputs") or [])[:10]]
    summary = {"equipment": result.get("calculator"), "results": outs,
               "priced_lines": _line_summary(result.get("lines")),
               "warnings": (result.get("warnings") or [])[:3]}
    if result.get("total"):
        summary["total"] = _money(result["total"])
    return summary


def _role_result(result):
    return dealer_view.calc(result) if builder.is_dealer() else result


@bp.route("/api/voice/equipment")
def equipment():
    calcs = builder._form_calculators()
    rows = [{"key": k, "name": c["label"], "what": c.get("blurb", ""),
             "prices": bool(c.get("prices"))}
            for k, c in calcs.items()]
    return jsonify({"equipment": rows})


@bp.route("/api/voice/fields/<key>")
def fields(key):
    calc = calculators.CALCULATORS.get(key)
    if not calc:
        return jsonify({"error": f"No calculator called {key}.",
                        "known": sorted(calculators.CALCULATORS)}), 404
    flds = (dealer_view.form_fields(calc["fields"], key) if builder.is_dealer()
            else calc["fields"])
    return jsonify({"equipment": calc["label"], "inputs": [
        {k: f.get(k) for k in ("key", "label", "unit", "default", "options", "help")
         if f.get(k) not in (None, "")}
        for f in flds if not f.get("advanced")]})


@bp.route("/api/voice/size/<key>", methods=["POST"])
def size(key):
    if key not in calculators.CALCULATORS:
        return jsonify({"error": f"No calculator called {key}.",
                        "known": sorted(calculators.CALCULATORS)}), 404
    form = (request.get_json(silent=True) or {}).get("inputs") or {}
    if builder.is_dealer():
        form = dealer_view.lock_inputs(key, form)
    result = _role_result(calculators.run_with_defaults(key, form))
    return jsonify({"summary": calc_summary(result), "result": result}), (
        400 if result.get("error") else 200)


@bp.route("/api/voice/draft", methods=["POST"])
def draft():
    """A draft quote from a job the assistant pieced together from the
    conversation. The same quote_from_job.build the typed description uses —
    nothing is saved; the person reviews it on the form and saves it."""
    data = (request.get_json(silent=True) or {}).get("job") or {}
    if not isinstance(data, dict):
        return jsonify({"error": "The job must be an object of fields."}), 400
    unknown = sorted(set(data) - set(interpret.JobRequest.model_fields))
    feeder = data.get("feeder") if isinstance(data.get("feeder"), dict) else {}
    unknown += sorted(f"feeder.{k}" for k in set(feeder) - set(interpret.FeederSpec.model_fields))
    if unknown:
        # a misspelt field would otherwise quote without it, silently
        return jsonify({"error": f"Unknown job field(s): {', '.join(unknown)}.",
                        "allowed": sorted(interpret.JobRequest.model_fields)}), 400
    try:
        job = interpret.JobRequest(**data)
    except (ValidationError, TypeError) as e:
        return jsonify({"error": "The job does not fit the form: "
                                 + "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}"
                                             for x in getattr(e, "errors", lambda: [])())
                                 or str(e)}), 400
    quote = builder.for_viewer(quote_from_job.build(job))
    quote["sourceRequest"] = (request.get_json(silent=True) or {}).get("said", "")[:2000]
    needs = [f"{r.get('parameter')}: {r.get('value')}" for r in quote.get("designBasis") or []
             if r.get("needsInput")]
    summary = {"quote": quote.get("name"), "lines": _line_summary(quote.get("lines")),
               "needs_input": needs[:6], "open_questions": list(job.ambiguities)[:6]}
    return jsonify({"summary": summary, "quote": quote})
