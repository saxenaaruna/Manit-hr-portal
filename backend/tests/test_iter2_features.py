# Iteration 2: password login, change-password, AI model selection, KB file upload, Jev lead suggestion / interest gating / request screening
import os
import json
import time
import uuid
import pytest
import requests
from datetime import date, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
TOKEN = "test_session_admin"
EMAIL = "saxena.aroona@gmail.com"
PW = "Manit@47deznLcnf4"
U = uuid.uuid4().hex[:6]
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@pytest.fixture(scope="module")
def s():
    x = requests.Session()
    x.headers["Authorization"] = f"Bearer {TOKEN}"
    return x


def chat(sid, m):
    out, note = "", None
    with requests.post(f"{BASE_URL}/api/chat", json={"session_id": sid, "message": m}, stream=True, timeout=180) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if line.startswith(b"data: "):
                d = json.loads(line[6:])
                assert "error" not in d, d
                out += d.get("delta", "")
                note = d.get("note") or note
    return out, note


# Password login
def test_password_login_success_sets_httponly_cookie():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PW})
    assert r.status_code == 200, r.text
    assert r.json()["email"] == EMAIL and "password_hash" not in r.json()
    sc = r.headers.get("set-cookie", "")
    assert "session_token=" in sc and "HttpOnly" in sc and "Secure" in sc
    tok = r.cookies.get("session_token")
    me = requests.get(f"{BASE_URL}/api/auth/me", cookies={"session_token": tok})
    assert me.status_code == 200 and me.json()["email"] == EMAIL


def test_password_login_wrong_and_lockout():
    em = f"test_lock_{U}@example.com"  # non-admin email so the real admin is never locked
    codes = [requests.post(f"{BASE_URL}/api/auth/login", json={"email": em, "password": "bad"}).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429, codes
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": "wrongpass"})
    assert r.status_code == 401 and r.json()["detail"] == "Invalid email or password"


def test_change_password_and_revert(s):
    bad = s.post(f"{BASE_URL}/api/auth/change-password", json={"current_password": "nope", "new_password": "TEST_newpass123"})
    assert bad.status_code == 400
    short = s.post(f"{BASE_URL}/api/auth/change-password", json={"current_password": PW, "new_password": "short"})
    assert short.status_code == 400
    r = s.post(f"{BASE_URL}/api/auth/change-password", json={"current_password": PW, "new_password": "TEST_newpass123"})
    assert r.status_code == 200
    try:
        assert requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": "TEST_newpass123"}).status_code == 200
    finally:
        rv = s.post(f"{BASE_URL}/api/auth/change-password", json={"current_password": "TEST_newpass123", "new_password": PW})
        assert rv.status_code == 200
    assert requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PW}).status_code == 200


# AI model selection + chat per model
def test_ai_models_list(s):
    r = s.get(f"{BASE_URL}/api/admin/ai-models")
    assert r.status_code == 200
    assert {m["key"] for m in r.json()["models"]} == {"claude", "gpt", "gemini"}
    assert s.put(f"{BASE_URL}/api/admin/settings", json={"chat_model": "bogus"}).status_code == 400


@pytest.mark.parametrize("model", ["gpt", "gemini", "claude"])
def test_chat_with_each_model(s, model):
    r = s.put(f"{BASE_URL}/api/admin/settings", json={"chat_model": model})
    assert r.status_code == 200 and r.json()["chat_model"] == model
    out, _ = chat(f"TEST_{model}_{U}", "Who is the Head of Training & Placement at MANIT?")
    print(model, "->", out[:200])
    assert len(out) > 10


# KB file upload
def test_kb_file_upload_and_access(s):
    e = s.post(f"{BASE_URL}/api/admin/kb", json={"category": "Resources", "title": f"TEST File {U}", "content": "TEST",
                                                  "published": False, "is_resource": True})
    assert e.status_code == 200, e.text
    kid = e.json()["id"]
    try:
        bad = s.post(f"{BASE_URL}/api/admin/kb/{kid}/file", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
        assert bad.status_code == 400
        up = s.post(f"{BASE_URL}/api/admin/kb/{kid}/file", files={"file": ("TEST_doc.pdf", PDF, "application/pdf")})
        assert up.status_code == 200, up.text
        fid = up.json()["file_id"]
        assert up.json()["file_name"] == "TEST_doc.pdf"
        assert requests.get(f"{BASE_URL}/api/files/{fid}").status_code == 401  # unpublished
        g = s.get(f"{BASE_URL}/api/files/{fid}")
        assert g.status_code == 200 and g.content.startswith(b"%PDF") and "pdf" in g.headers["content-type"]
        assert s.patch(f"{BASE_URL}/api/admin/kb/{kid}", json={"published": True}).status_code == 200
        assert requests.get(f"{BASE_URL}/api/files/{fid}").status_code == 200
        pub = requests.get(f"{BASE_URL}/api/public/kb").json()
        assert any(k["id"] == kid and k.get("file_id") == fid for k in pub)
        assert s.delete(f"{BASE_URL}/api/admin/kb/{kid}/file").status_code == 200
        assert requests.get(f"{BASE_URL}/api/files/{fid}").status_code == 404
    finally:
        s.delete(f"{BASE_URL}/api/admin/kb/{kid}")


# Jev: AI status suggestion on remarks edit
def test_lead_ai_suggestion(s):
    r = s.post(f"{BASE_URL}/api/admin/leads", json={"company_name": f"TEST AISug {U}", "hr_name": "TEST HR", "interest_status": "Cold"})
    lid = r.json()["lead"]["id"]
    try:
        p = s.patch(f"{BASE_URL}/api/admin/leads/{lid}", json={"remarks": "HR confirmed on call they want to conduct a campus drive for 40 B.Tech CSE students in Aug 2026."})
        assert p.status_code == 200
        sug = p.json()["lead"].get("ai_status_suggestion")
        print("suggestion:", sug)
        assert sug and sug["ai_classified"] is True and sug["status"] in ("Hot", "Warm", "Cold")
        assert 0 <= sug["confidence"] <= 1
        assert sug["status"] == "Hot"
        p2 = s.patch(f"{BASE_URL}/api/admin/leads/{lid}", json={"remarks": "HR said they are not hiring this year and declined."})
        sug2 = p2.json()["lead"]["ai_status_suggestion"]
        print("suggestion2:", sug2)
        assert sug2["status"] == "Cold"
    finally:
        s.delete(f"{BASE_URL}/api/admin/leads/{lid}")


# Jev: request screening urgency + junk
def test_request_screening(s):
    soon = (date.today() + timedelta(days=4)).isoformat()
    body = {"company_name": "Infosys Limited", "hr_name": "Anita Sharma", "designation": "HR Manager", "work_email": f"anita.sharma{U}@infosys.com",
            "contact_number": "9876543210", "visit_purpose": "Campus Placement Drive", "requested_date": soon,
            "requested_start_time": "10:00", "requested_end_time": "12:00", "remarks": "Final placement drive for 2026 batch"}
    v = requests.post(f"{BASE_URL}/api/public/visits", json=body)
    assert v.status_code == 200, v.text
    junk = requests.post(f"{BASE_URL}/api/public/calls", json={"company_name": "asdf qwer", "hr_name": "lol", "work_email": f"x{U}@mailinator.com",
                         "preferred_date": (date.today() + timedelta(days=60)).isoformat(), "preferred_time": "15:00", "duration": 15,
                         "call_mode": "Phone", "discussion_purpose": "hahaha test spam buy crypto", "remarks": "free money click link"})
    assert junk.status_code == 200, junk.text
    vid, cid = v.json()["id"], junk.json()["id"]
    vs = cs = None
    for _ in range(20):
        time.sleep(3)
        vs = next((i for i in s.get(f"{BASE_URL}/api/admin/req/visits").json() if i["id"] == vid), {}).get("ai_screen")
        cs = next((i for i in s.get(f"{BASE_URL}/api/admin/req/calls").json() if i["id"] == cid), {}).get("ai_screen")
        if vs and cs:
            break
    print("visit screen:", vs, "call screen:", cs)
    assert vs and vs["ai_classified"] is True
    assert vs["urgency_label"] in ("low", "medium", "high", "critical") and 0 <= vs["urgency_score"] <= 3
    assert 0 <= vs["junk_probability"] <= 1 and vs["junk_flag"] is False
    assert cs and cs["ai_classified"] is True and cs["junk_probability"] >= 0.5
    srt = s.get(f"{BASE_URL}/api/admin/req/visits", params={"sort": "urgency"}).json()
    scores = [i.get("ai_screen", {}).get("urgency_score") for i in srt if i.get("ai_screen", {}).get("urgency_score") is not None]
    assert scores == sorted(scores, reverse=True)


# Chat interest gating
def test_chat_general_question_not_hot(s):
    s.put(f"{BASE_URL}/api/admin/settings", json={"chat_model": "claude"})
    sid = f"TEST_gate_{U}"
    comp = f"TEST GateCo {U}"
    out, note = chat(sid, f"Hi, I'm TEST Rahul from {comp}, email gate_{U}@example.com. What is the average CTC and which branches does MANIT have?")
    print("gate:", out[:300], "NOTE:", note)
    leads = s.get(f"{BASE_URL}/api/admin/leads", params={"q": comp}).json()
    print("leads:", [(l["company_name"], l["interest_status"]) for l in leads])
    assert not any(l["interest_status"] == "Hot" for l in leads)


def test_chat_explicit_interest_hot(s):
    sid = f"TEST_hot_{U}"
    comp = f"TEST HotCo {U}"
    out, note = chat(sid, f"We want to recruit MANIT students for full-time roles in 2026-27 and need the recruitment invitation and JNF. "
                          f"Company: {comp}, HR name: TEST Priya, work email: hot_{U}@example.com.")
    print("hot:", out[:300], "NOTE:", note)
    if not note:
        out, note = chat(sid, "Yes, all details are correct, please register our interest.")
        print("hot2:", out[:300], "NOTE:", note)
    leads = s.get(f"{BASE_URL}/api/admin/leads", params={"q": comp}).json()
    print("leads:", [(l["company_name"], l["interest_status"]) for l in leads])
    assert any(l["interest_status"] == "Hot" for l in leads)
    for l in leads:
        s.delete(f"{BASE_URL}/api/admin/leads/{l['id']}")
