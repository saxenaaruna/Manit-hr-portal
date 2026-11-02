# Iteration 4: Email preview endpoint tests
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
H = {"Authorization": "Bearer test_session_admin"}
FROM = "Training & Placement Cell, MANIT Bhopal <tpwnitb@gmail.com>"


@pytest.fixture(scope="module")
def s():
    x = requests.Session(); x.headers.update(H); return x


@pytest.fixture(scope="module")
def lead(s):
    r = s.get(f"{BASE_URL}/api/admin/leads")
    assert r.status_code == 200
    d = r.json()
    items = d.get("items", d) if isinstance(d, dict) else d
    assert items, "no leads"
    return items[0]


def email_count(s):
    r = s.get(f"{BASE_URL}/api/admin/emails")
    assert r.status_code == 200
    d = r.json()
    if isinstance(d, dict):
        return d.get("total", len(d.get("items", [])))
    return len(d)


def test_preview_requires_auth():
    r = requests.post(f"{BASE_URL}/api/admin/templates/invitation/preview", json={})
    assert r.status_code == 401


def test_preview_sample(s):
    r = s.post(f"{BASE_URL}/api/admin/templates/invitation/preview", json={})
    assert r.status_code == 200
    d = r.json()
    assert d["from"] == FROM
    assert d["to"] == "hr@sample-company.com"
    assert "[JNF_URL]" not in d["body"] and "https://" in d["body"]
    assert "[COMPANY_NAME]" not in d["body"] + d["subject"]


def test_preview_lead(s, lead):
    before = email_count(s)
    r = s.post(f"{BASE_URL}/api/admin/templates/invitation/preview", json={"lead_id": lead["id"]})
    assert r.status_code == 200
    d = r.json()
    assert d["to"] == lead["work_email"]
    assert d["subject"] == "Invitation for Campus Recruitment Program 2026–27 — MANIT Bhopal"
    assert "[JNF_URL]" not in d["body"] and "[" not in d["body"].split("http")[0][-3:]
    assert email_count(s) == before


def test_preview_draft_override(s):
    r = s.post(f"{BASE_URL}/api/admin/templates/visit_confirmation/preview",
               json={"subject": "TEST_ Visit [COMPANY_NAME] [APPROVED_DATE]", "body": "Hi [HR_NAME] [MEETING_LINK]"})
    assert r.status_code == 200
    d = r.json()
    assert d["subject"] == "TEST_ Visit Sample Company Pvt. Ltd. 15 December 2026"
    assert d["body"] == "Hi Sample HR To be shared"
    # not persisted
    t = [x for x in s.get(f"{BASE_URL}/api/admin/templates").json() if x["key"] == "visit_confirmation"][0]
    assert not t["subject"].startswith("TEST_")


def test_preview_unknown_template(s):
    assert s.post(f"{BASE_URL}/api/admin/templates/nope/preview", json={}).status_code == 404


def test_preview_unknown_lead(s):
    assert s.post(f"{BASE_URL}/api/admin/templates/invitation/preview", json={"lead_id": "nope"}).status_code == 404
