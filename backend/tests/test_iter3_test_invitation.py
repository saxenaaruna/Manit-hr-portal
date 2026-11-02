# Iteration 3: Google connect URL + test invitation endpoint (Google not connected)
import os
import requests
import pytest
from urllib.parse import urlparse, parse_qs

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
H = {"Authorization": "Bearer test_session_admin"}
REDIRECT = "https://manit-hr-portal--93wuv0i1.preview.emergentagent.com/api/oauth/google/callback"


# Google status
def test_google_status():
    r = requests.get(f"{BASE_URL}/api/admin/google/status", headers=H)
    assert r.status_code == 200
    d = r.json()
    assert d["configured"] is True
    assert d["connected"] is False
    assert d["redirect_uri"] == REDIRECT


# Google connect URL
def test_google_connect_url():
    r = requests.get(f"{BASE_URL}/api/admin/google/connect", headers=H)
    assert r.status_code == 200
    url = r.json()["url"]
    p = urlparse(url)
    assert p.netloc == "accounts.google.com"
    q = parse_qs(p.query)
    assert q["redirect_uri"][0] == REDIRECT
    scope = q["scope"][0]
    for s in ["gmail.send", "calendar.freebusy", "calendar.events"]:
        assert s in scope
    assert q["access_type"][0] == "offline"
    assert q["login_hint"][0] == "tpwnitb@gmail.com"
    assert q["client_id"][0]


def test_test_invitation_unauth():
    r = requests.post(f"{BASE_URL}/api/admin/emails/test-invitation", json={"to": "a@b.com"})
    assert r.status_code == 401


def test_test_invitation_invalid_email():
    r = requests.post(f"{BASE_URL}/api/admin/emails/test-invitation", json={"to": "not-an-email"}, headers=H)
    assert r.status_code == 400


def _leads():
    r = requests.get(f"{BASE_URL}/api/admin/leads", headers=H)
    return r.json() if r.status_code == 200 else None


def test_test_invitation_not_connected_logged():
    before = _leads()
    to = "TEST_invite@example.com"
    r = requests.post(f"{BASE_URL}/api/admin/emails/test-invitation", json={"to": to}, headers=H)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is False
    assert "Google account (tpwnitb@gmail.com) is not connected" in d["message"]
    # log
    e = requests.get(f"{BASE_URL}/api/admin/emails", headers=H)
    assert e.status_code == 200
    data = e.json()
    items = data if isinstance(data, list) else data.get("items") or data.get("emails") or data.get("logs") or []
    match = [x for x in items if x.get("recipient_email") == to and x.get("email_type") == "Test Invitation"]
    assert match, "Test invitation log not found"
    m = match[0]
    assert m["delivery_status"] == "Failed"
    assert m["provider_message_id"] is None
    assert m.get("company_lead_id") is None
    assert m["subject"].startswith("[TEST]")
    after = _leads()
    if before is not None:
        assert len(str(before)) == len(str(after)) or before == after
