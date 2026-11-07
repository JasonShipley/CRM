"""Quote app calculator routes (Flask test client, vendored engine, temporary sizing-record store).

    cd renderer && python -m pytest tests -q        (needs: flask pydantic openpyxl reportlab pillow pytest)
"""
import io
import json
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MCE_AUDIT_ROOT", str(tmp_path / "audit"))
    import app as quote_app
    quote_app.app.config["TESTING"] = True
    return quote_app.app.test_client()


def test_engine_is_the_vendored_copy():
    import calc  # noqa: F401
    import mce_engineering
    assert str(HERE / "vendor") in mce_engineering.__file__


def test_calculator_pages(client):
    assert client.get("/calc").status_code == 200
    assert client.get("/calc/dryer").status_code == 301
    r = client.get("/calc/dryer/")
    assert r.status_code == 200 and b"ROTARY DRYER CALCULATOR" in r.data and b"/calc/dryer/records" in r.data
    assert b"No sizing records yet" in client.get("/calc/dryer/records").data


def test_save_record_then_list_and_download(client):
    rec = {"entries": {"j_Job": "Q-123", "j_Customer": "Test customer", "p_Throughput": 1.5, "p_TUnit": "TPH"},
           "results": {"d_mf": 324.7573032, "d_BtuLb": 1728.1148}}
    r = client.post("/calc/dryer/api/dryer/workbook", json=rec).get_json()
    assert r["status"] == "ok" and r["record"]["index"] == "RD-000001", r
    assert r["crosscheck"]["summary"].startswith("matches the engine")
    page = client.get("/calc/dryer/records").data.decode()
    assert "RD-000001" in page and "Q-123" in page and "4 ft dia x 30 ft long" in page
    pdf = client.get("/calc/dryer/records/RD-000001.pdf")
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF"
    x = client.get("/calc/dryer/records/RD-000001.xlsx")
    assert x.status_code == 200 and x.data[:2] == b"PK"
    js = client.get("/calc/dryer/records/RD-000001.json")
    assert json.loads(js.data)["index"] == "RD-000001"
    assert client.get("/calc/dryer/records/..%2Fapp.py").status_code == 404


def test_excel_download(client):
    import openpyxl
    r = client.post("/calc/dryer/api/dryer/workbook/xlsx", json={"entries": {"j_Job": "Q-9", "f_Fuel": "Natural gas"}})
    assert r.status_code == 200 and 'MCE_rotary_dryer_Q-9.xlsx' in r.headers["Content-Disposition"]
    wb = openpyxl.load_workbook(io.BytesIO(r.data))
    assert wb.sheetnames[0] == "Mass-Energy Balance"
    assert {"Equipment", "Emissions", "Open Items", "Products"} <= set(wb.sheetnames)


def test_engine_json_api(client):
    r = client.post("/calc/dryer/api/dryer", json={"save_record": False}).get_json()
    assert r["status"] == "ok" and r["outputs"]["drum"]["recommended"]["size"] == "4 ft dia x 30 ft long"
    r = client.post("/calc/dryer/api/dryer", json={"save_record": False, "process": {"material": "carrots"},
                                                   "fuel": {"fuel": "natural_gas"}}).get_json()
    assert r["status"] == "ok" and r["outputs"]["emissions"]["pollutants"]["NOx"]["lb_hr"]["value"] > 0
