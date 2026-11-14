#!/usr/bin/env python3
"""The voice assistant's server half: sessions and tools.

ElevenLabs itself is not called — `voice._elevenlabs` is replaced — so this runs
anywhere. What it holds:

  * no key, no voice — a clear 503, never a crash
  * a session carries the token and who the agent is talking to, and never the key
  * a person cannot open conversations without limit
  * the draft tool builds exactly what quote_from_job.build does from the same job
  * a job the schema would refuse is refused, not guessed at
  * the tool summaries carry the calculators' own numbers

    cd renderer && python3 tests/test_voice.py
"""
import logging
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ["RENDERER_DATA_DIR"] = tempfile.mkdtemp()
os.environ["SESSION_COOKIE_SECURE"] = "0"
os.environ.pop("SMTP_HOST", None)
os.environ.pop("ELEVENLABS_API_KEY", None)
os.environ.pop("ELEVENLABS_AGENT_ID", None)
logging.disable(logging.WARNING)

import accounts  # noqa: E402
import app as appmod  # noqa: E402
import calculators  # noqa: E402
import codes  # noqa: E402
import quote_from_job  # noqa: E402
import voice  # noqa: E402
from interpret import JobRequest  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(f"{name}: {str(detail)[:300]}")


def sign_in(email):
    c = appmod.app.test_client()
    code, _ = codes.issue(email, "login")
    c.post("/login", data={"email": email, "step": "code", "code": code})
    return c


def main():
    staff = sign_in("jason@usemce.com")
    accounts.save_dealer("dee@dealerco.com", "Dee Dealer", "DealerCo")
    dealer = sign_in("dee@dealerco.com")

    # 1. not configured --------------------------------------------------------
    r = staff.post("/api/voice/session")
    check("no key: a clear 503", r.status_code == 503
          and "ELEVENLABS" in r.get_json()["error"], r.get_json())

    # 2. configured, with ElevenLabs stood in for --------------------------------
    os.environ["ELEVENLABS_API_KEY"] = "sk_test_never_leaves_the_server"
    os.environ["ELEVENLABS_AGENT_ID"] = "agent_test"
    calls = []

    def fake(path, params):
        calls.append((path, params))
        return {"token": "tok_123"} if path.endswith("/token") else {}
    voice._elevenlabs = fake
    r = dealer.post("/api/voice/session")
    j = r.get_json()
    check("a session is issued", r.status_code == 200 and j.get("conversationToken") == "tok_123", j)
    check("over WebRTC", j.get("connectionType") == "webrtc", j)
    check("for MCE's agent", calls and calls[-1][1] == {"agent_id": "agent_test"}, calls)
    check("telling the agent it is a dealer",
          j.get("dynamicVariables", {}).get("user_role") == "dealer"
          and j["dynamicVariables"].get("dealership") == "DealerCo", j)
    check("and never handing out the key", "sk_test" not in r.get_data(as_text=True))
    sj = staff.post("/api/voice/session").get_json()
    check("staff are staff", sj.get("dynamicVariables", {}).get("user_role") == "staff", sj)

    def fake_url(path, params):
        return {} if path.endswith("/token") else {"signed_url": "wss://example/x"}
    voice._elevenlabs = fake_url
    j = staff.post("/api/voice/session").get_json()
    check("falls back to a signed URL", j.get("signedUrl") == "wss://example/x"
          and j.get("connectionType") == "websocket", j)

    voice._elevenlabs = fake
    voice.SESSIONS_PER_HOUR = 3
    voice._recent.clear()
    codes_seen = [staff.post("/api/voice/session").status_code for _ in range(4)]
    check("a person cannot open conversations without limit",
          codes_seen == [200, 200, 200, 429], codes_seen)

    # 3. the draft tool is quote_from_job, nothing more ---------------------------
    job = dict(customer_company="Acme Feed", mill_model="XM-4430", motor_hp=200,
               product_match="Corn / Milo", product_confidence="stated",
               capacity_tph=15, screen_64ths=6, include_plenum=True,
               include_air_system=True)
    d = staff.post("/api/voice/draft", json={"job": job, "said": "quote acme a 4430"}).get_json()
    want = quote_from_job.build(JobRequest(**job))
    check("staff draft equals quote_from_job.build",
          [(l["name"], l["unitPrice"]) for l in d["quote"]["lines"]]
          == [(l["name"], l["unitPrice"]) for l in want["lines"]],
          d["quote"]["lines"])
    check("what was said rides along", d["quote"].get("sourceRequest") == "quote acme a 4430")
    check("the summary reads the same prices",
          any("$65,306" in line for line in d["summary"]["lines"]), d["summary"])
    bad = staff.post("/api/voice/draft", json={"job": {"capacity_tph": "lots"}})
    check("a job the schema refuses is refused", bad.status_code == 400
          and "capacity_tph" in bad.get_json()["error"], bad.get_json())
    unknown = staff.post("/api/voice/draft", json={"job": {"millz": 1}})
    check("an unknown field is not silently dropped", unknown.status_code == 400
          and "millz" in unknown.get_json()["error"], unknown.get_json())

    # 4. sizing summaries are the calculator's own numbers --------------------------
    inputs = {"tph": 2, "tin": 250, "tout": 120, "tmax": 100, "humMode": "rh",
              "humVal": 40, "cp": 0.45, "rho": 38, "mcin": 7, "mcout": 6}
    r = staff.post("/api/voice/size/rotary_cooler", json={"inputs": inputs}).get_json()
    model = calculators.run_with_defaults("rotary_cooler", inputs)["model"]
    check("the summary names the calculator's model",
          any(model in line for line in r["summary"]["results"]), (model, r["summary"]))
    r = staff.post("/api/voice/size/no_such_thing", json={})
    check("an unknown calculator says which exist",
          r.status_code == 404 and "known" in r.get_json())
    f = staff.get("/api/voice/fields/hammer_pattern").get_json()
    check("inputs are listed", any(i["key"] == "motorHp" for i in f["inputs"]), f)

    if FAILS:
        print(f"voice: {len(FAILS)} problems")
        for x in FAILS:
            print("  " + x)
        return 1
    print("OK — voice sessions stay server-keyed and rate-limited; the tools answer "
          "with MCE's calculators.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
