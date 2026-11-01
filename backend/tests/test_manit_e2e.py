# MANIT T&P portal - lightweight end-to-end API regression (auth, leads, invitations, visits, calls, calendar, stats, chat)
import os
import json
import uuid
import pytest
import requests
from datetime import date, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
TOKEN = "test_session_admin"
U = uuid.uuid4().hex[:6]


@pytest.fixture(scope="module")
def s():
    x = requests.Session()
    x.cookies.set("session_token", TOKEN)
    return x


@pytest.fixture(scope="module")
def created():
    return {}


def future(days):
    return (date.today() + timedelta(days=days)).isoformat()


# Auth
def test_unauth_401():
    for p in ["/api/admin/leads", "/api/admin/stats", "/api/admin/req/visits", "/api/auth/me"]:
        assert requests.get(BASE_URL + p).status_code == 401, p


def test_auth_me_cookie_and_bearer(s):
    r = s.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200 and r.json()["email"] == "saxena.aroona@gmail.com"
    r2 = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r2.status_code == 200


# Leads + invitations
def test_lead_flow(s, created):
    r = s.post(f"{BASE_URL}/api/admin/leads", json={"company_name": f"TEST Lead {U}", "hr_name": "TEST HR",
                                                   "work_email": f"test_{U}@example.com", "interest_status": "Warm"})
    assert r.status_code == 200, r.text
    lead = r.json()["lead"]; lid = lead["id"]; created["lead"] = lid
    assert lead["invitation_status"] == "Not Sent"
    n0 = len(s.get(f"{BASE_URL}/api/admin/leads/{lid}").json()["emails"])
    # remarks edit -> no email
    r = s.patch(f"{BASE_URL}/api/admin/leads/{lid}", json={"remarks": "TEST remark"})
    assert r.json()["lead"]["remarks"] == "TEST remark" and r.json()["invitation"] is None
    assert len(s.get(f"{BASE_URL}/api/admin/leads/{lid}").json()["emails"]) == n0
    # Warm -> Hot -> Failed
    r = s.patch(f"{BASE_URL}/api/admin/leads/{lid}", json={"interest_status": "Hot"}).json()
    print("HOT:", r["invitation"])
    assert r["lead"]["invitation_status"] == "Failed"
    assert "Google OAuth credentials are not configured" in (r["lead"]["invitation_error"] or "")
    det = s.get(f"{BASE_URL}/api/admin/leads/{lid}").json()
    assert len(det["emails"]) == n0 + 1 and det["emails"][0]["delivery_status"] == "Failed"
    # Hot->Warm->Hot (not yet sent, so retry attempt expected)
    s.patch(f"{BASE_URL}/api/admin/leads/{lid}", json={"interest_status": "Warm"})
    s.patch(f"{BASE_URL}/api/admin/leads/{lid}", json={"interest_status": "Hot"})
    n2 = len(s.get(f"{BASE_URL}/api/admin/leads/{lid}").json()["emails"])
    print("emails after Hot->Warm->Hot:", n2)
    # Manual resend creates new log
    r = s.post(f"{BASE_URL}/api/admin/leads/{lid}/invite").json()
    assert r["ok"] is False and "not configured" in r["message"]
    assert len(s.get(f"{BASE_URL}/api/admin/leads/{lid}").json()["emails"]) == n2 + 1
    # never Sent
    assert s.get(f"{BASE_URL}/api/admin/leads/{lid}").json()["lead"]["invitation_status"] != "Sent"


def test_invalid_lead(s):
    assert s.post(f"{BASE_URL}/api/admin/leads", json={"company_name": ""}).status_code == 400
    assert s.post(f"{BASE_URL}/api/admin/leads", json={"company_name": "TEST x", "work_email": "bad"}).status_code == 400
    assert s.patch(f"{BASE_URL}/api/admin/leads/nonexist", json={"remarks": "a"}).status_code == 404


# Visits
def test_visit_approve_and_conflict(s, created):
    d = future(200 + (int(U, 16) % 60))
    body = {"company_name": f"TEST Visit {U}", "hr_name": "TEST HR", "work_email": f"tv_{U}@example.com",
            "visit_purpose": "Pre-Placement Talk", "requested_date": d, "requested_start_time": "10:00", "requested_end_time": "11:00"}
    r1 = requests.post(f"{BASE_URL}/api/public/visits", json=body)
    assert r1.status_code == 200 and r1.json()["id"].startswith("VR-") and r1.json()["status"] == "Pending Approval"
    r2 = requests.post(f"{BASE_URL}/api/public/visits", json={**body, "requested_start_time": "10:30", "requested_end_time": "11:30"})
    v1, v2 = r1.json()["id"], r2.json()["id"]
    a = s.post(f"{BASE_URL}/api/admin/req/visits/{v1}/action", json={"action": "approve"})
    assert a.status_code == 200 and a.json()["item"]["status"] == "Approved"
    print("visit approve:", a.json()["calendar"], a.json()["email"])
    c = s.post(f"{BASE_URL}/api/admin/req/visits/{v2}/action", json={"action": "approve"})
    assert c.status_code == 409, c.text
    cal = s.get(f"{BASE_URL}/api/admin/calendar", params={"month": d[:7]}).json()
    assert any(i["id"] == v1 and i["confirmed"] for i in cal)
    assert requests.post(f"{BASE_URL}/api/public/visits", json={**body, "requested_date": "2020-01-01"}).status_code == 400


# Calls
def test_call_approve_reschedule(s):
    d = future(270 + (int(U, 16) % 30))
    r = requests.post(f"{BASE_URL}/api/public/calls", json={"company_name": f"TEST Call {U}", "hr_name": "TEST HR",
                      "work_email": f"tc_{U}@example.com", "preferred_date": d, "preferred_time": "15:00",
                      "duration": 30, "call_mode": "Phone"})
    assert r.status_code == 200 and r.json()["id"].startswith("CR-")
    cid = r.json()["id"]
    a = s.post(f"{BASE_URL}/api/admin/req/calls/{cid}/action", json={"action": "approve"})
    assert a.status_code == 200 and a.json()["item"]["status"] == "Approved"
    d2 = future(301)
    rs = s.post(f"{BASE_URL}/api/admin/req/calls/{cid}/action", json={"action": "reschedule", "date": d2, "start_time": "16:00"})
    assert rs.status_code == 200, rs.text
    it = rs.json()["item"]
    assert it["status"] == "Rescheduled" and it["approved_date"] == d2 and it["approved_time"] == "16:00"
    cal = s.get(f"{BASE_URL}/api/admin/calendar", params={"month": d2[:7]}).json()
    assert any(i["id"] == cid and i["date"] == d2 and i["start"] == "16:00" for i in cal)


# Stats from DB
def test_stats(s):
    st = s.get(f"{BASE_URL}/api/admin/stats").json()
    leads = s.get(f"{BASE_URL}/api/admin/leads").json()
    assert st["total"] == len(leads)
    assert st["hot"] == sum(1 for l in leads if l["interest_status"] == "Hot")


# Chatbot (LLM) register interest
def test_chat_register_interest(s):
    sid = f"TEST-{U}"
    comp = f"TEST Chat Corp {U}"

    def ask(m):
        out, note = "", None
        with requests.post(f"{BASE_URL}/api/chat", json={"session_id": sid, "message": m}, stream=True, timeout=120) as r:
            for line in r.iter_lines():
                if line.startswith(b"data: "):
                    d = json.loads(line[6:])
                    out += d.get("delta", "")
                    note = d.get("note") or note
                    assert "error" not in d, d
        return out, note

    a, _ = ask("What B.Tech programs does MANIT offer?")
    print("A1:", a[:200])
    assert a
    a, note = ask(f"We want to recruit MANIT students for 2026-27. Company: {comp}, HR name: TEST Priya, "
                  f"work email: chat_{U}@example.com. Please register our interest and send the invitation.")
    print("A2:", a[:200], "NOTE:", note)
    if not note:
        a, note = ask("Yes, all details are correct, please proceed.")
        print("A3:", a[:200], "NOTE:", note)
    assert note
    leads = s.get(f"{BASE_URL}/api/admin/leads", params={"q": comp}).json()
    assert leads and leads[0]["interest_status"] == "Hot"
