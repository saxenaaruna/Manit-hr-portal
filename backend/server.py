import os
import re
import json
import uuid
import base64
import asyncio
import logging
import secrets
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone, timedelta, date as date_cls
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText
from email.header import Header
from urllib.parse import urlencode, urlparse

import httpx
import bcrypt
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from seed import TEMPLATES, KB_SEED, JNF_URL
import jev

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
ADMIN_EMAILS = {e.strip().lower() for e in os.environ["ADMIN_EMAILS"].split(",") if e.strip()}
OFFICIAL_EMAIL = os.environ["OFFICIAL_GOOGLE_EMAIL"].lower()
LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"].strip().lower()
ADMIN_EMAILS.add(ADMIN_EMAIL)
USER_PROJ = {"_id": 0, "password_hash": 0}
AI_MODELS = {"claude": ("anthropic", "claude-sonnet-5-5", "Claude Sonnet 5.5"),
             "gpt": ("openai", "gpt-5.6-terra", "ChatGPT (GPT-5.6 Terra)"),
             "gemini": ("gemini", "gemini-3.1-pro-preview", "Gemini 3.1 Pro")}
STORAGE_URL = ((os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com").rstrip("/") + "/objstore/api/v1/storage"
APP_NAME = "manit-tp"
ALLOWED_FILES = {"pdf": "application/pdf", "doc": "application/msword",
                 "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
MAX_FILE = 15 * 1024 * 1024

app = FastAPI()
api = APIRouter(prefix="/api")
logger = logging.getLogger("manit")
logging.basicConfig(level=logging.INFO)

IST = ZoneInfo("Asia/Kolkata")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
HM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
LEAD_STATUSES = ["Hot", "Warm", "Cold"]
VISIT_PURPOSES = ["Campus Placement Drive", "Internship Recruitment", "Pre-Placement Talk",
                  "Recruitment Assessment / Interview", "Company Presentation", "Other"]
CALL_MODES = ["Phone", "Google Meet", "Other"]
DURATIONS = [15, 30, 45, 60]
ACTIVE = ["Approved", "Rescheduled"]
GOOGLE_SCOPES = ["openid", "email", "https://www.googleapis.com/auth/gmail.send",
                 "https://www.googleapis.com/auth/calendar.freebusy",
                 "https://www.googleapis.com/auth/calendar.events"]
APPROVAL_LOCK = asyncio.Lock()
NO_ID = {"_id": 0}


def now():
    return datetime.now(timezone.utc).isoformat()


def nid():
    return uuid.uuid4().hex


def today_ist():
    return datetime.now(IST).date().isoformat()


def to_dt(d, hm):
    return datetime.strptime(f"{d} {hm}", "%Y-%m-%d %H:%M").replace(tzinfo=IST)


def add_minutes(hm, minutes):
    return (datetime.strptime(hm, "%H:%M") + timedelta(minutes=int(minutes))).strftime("%H:%M")


def pretty_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d %B %Y")
    except Exception:
        return d or ""


def validate_slot(d, start, end):
    try:
        date_cls.fromisoformat(d)
    except Exception:
        raise HTTPException(400, "Invalid date (use YYYY-MM-DD)")
    if not HM_RE.match(start or "") or not HM_RE.match(end or ""):
        raise HTTPException(400, "Invalid time (use HH:MM)")
    if start >= end:
        raise HTTPException(400, "End time must be after start time")


# ---------------- Activity ----------------
async def log_activity(admin_id, entity_type, entity_id, action, prev=None, new=None):
    await db.activity_logs.insert_one({
        "id": nid(), "admin_id": admin_id, "entity_type": entity_type, "entity_id": entity_id,
        "action": action, "previous_value": None if prev is None else str(prev),
        "new_value": None if new is None else str(new), "timestamp": now()})


# ---------------- Auth ----------------
async def get_admin(request: Request):
    token = request.cookies.get("session_token")
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    s = await db.user_sessions.find_one({"session_token": token}, NO_ID)
    if not s:
        raise HTTPException(401, "Invalid session")
    exp = s["expires_at"]
    if isinstance(exp, str):
        exp = datetime.fromisoformat(exp)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        raise HTTPException(401, "Session expired")
    user = await db.users.find_one({"user_id": s["user_id"]}, USER_PROJ)
    if not user or user["email"].lower() not in ADMIN_EMAILS:
        raise HTTPException(403, "Not authorised for Admin access")
    return user


@api.post("/auth/session")
async def auth_session(body: dict, response: Response):
    sid = body.get("session_id")
    if not sid:
        raise HTTPException(400, "session_id required")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                        headers={"X-Session-ID": sid})
    if r.status_code != 200:
        raise HTTPException(401, "Authentication failed")
    d = r.json()
    email = d["email"].lower()
    if email not in ADMIN_EMAILS:
        raise HTTPException(403, f"{email} is not authorised for Admin access.")
    user = await db.users.find_one({"email": email}, NO_ID)
    if user:
        await db.users.update_one({"email": email}, {"$set": {"name": d.get("name"), "picture": d.get("picture")}})
        user_id = user["user_id"]
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({"user_id": user_id, "email": email, "name": d.get("name"),
                                   "picture": d.get("picture"), "created_at": now()})
    await db.user_sessions.insert_one({"user_id": user_id, "session_token": d["session_token"],
                                       "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
                                       "created_at": now()})
    response.set_cookie("session_token", d["session_token"], httponly=True, secure=True,
                        samesite="none", path="/", max_age=7 * 24 * 3600)
    await log_activity(user_id, "auth", user_id, "login")
    return await db.users.find_one({"user_id": user_id}, USER_PROJ)


@api.get("/auth/me")
async def auth_me(admin=Depends(get_admin)):
    return admin


@api.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", secure=True, samesite="none")
    return {"ok": True}


def hash_pw(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def check_pw(p, h):
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


class LoginIn(BaseModel):
    email: str
    password: str


@api.post("/auth/login")
async def password_login(body: LoginIn, request: Request, response: Response):
    email = body.email.strip().lower()
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0].strip()
    ident = f"{ip}:{email}"
    att = await db.login_attempts.find_one({"identifier": ident}) or {}
    if att.get("locked_until") and att["locked_until"] > now():
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email}, NO_ID)
    if not user or email not in ADMIN_EMAILS or not user.get("password_hash") or not check_pw(body.password, user["password_hash"]):
        count = att.get("count", 0) + 1
        upd = {"count": count, "updated_at": now()}
        if count >= 5:
            upd = {"count": 0, "locked_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}
        await db.login_attempts.update_one({"identifier": ident}, {"$set": upd}, upsert=True)
        raise HTTPException(401, "Invalid email or password")
    await db.login_attempts.delete_one({"identifier": ident})
    token = secrets.token_urlsafe(32)
    await db.user_sessions.insert_one({"user_id": user["user_id"], "session_token": token,
                                       "expires_at": datetime.now(timezone.utc) + timedelta(days=7), "created_at": now()})
    response.set_cookie("session_token", token, httponly=True, secure=True, samesite="none", path="/", max_age=7 * 24 * 3600)
    await log_activity(user["user_id"], "auth", user["user_id"], "password_login")
    return await db.users.find_one({"user_id": user["user_id"]}, USER_PROJ)


@api.post("/auth/change-password")
async def change_password(body: dict, admin=Depends(get_admin)):
    new = body.get("new_password") or ""
    if len(new) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    user = await db.users.find_one({"user_id": admin["user_id"]})
    if user.get("password_hash") and not check_pw(body.get("current_password") or "", user["password_hash"]):
        raise HTTPException(400, "Current password is incorrect")
    await db.users.update_one({"user_id": admin["user_id"]}, {"$set": {"password_hash": hash_pw(new)}})
    await log_activity(admin["user_id"], "auth", admin["user_id"], "password_changed")
    return {"ok": True}


# ---------------- File storage ----------------
storage_key = None


def init_storage(force=False):
    global storage_key
    if storage_key and not force:
        return storage_key
    r = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": LLM_KEY}, timeout=30)
    r.raise_for_status()
    storage_key = r.json()["storage_key"]
    return storage_key


def put_object(path, data, ctype):
    r = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(), "Content-Type": ctype}, data=data, timeout=120)
    if r.status_code == 404:
        r = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(True), "Content-Type": ctype}, data=data, timeout=120)
    r.raise_for_status()
    return r.json()


def get_object(path):
    r = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage()}, timeout=60)
    r.raise_for_status()
    return r.content


@api.post("/admin/kb/{kid}/file")
async def upload_kb_file(kid: str, file: UploadFile = File(...), admin=Depends(get_admin)):
    entry = await db.knowledge_base.find_one({"id": kid}, NO_ID)
    if not entry:
        raise HTTPException(404, "Entry not found")
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if ext not in ALLOWED_FILES:
        raise HTTPException(400, "Allowed file types: PDF, DOC, DOCX, PNG, JPG, WEBP")
    data = await file.read()
    if len(data) > MAX_FILE:
        raise HTTPException(400, "File too large (max 15 MB)")
    try:
        res = await asyncio.to_thread(put_object, f"{APP_NAME}/kb/{kid}/{uuid.uuid4()}.{ext}", data, ALLOWED_FILES[ext])
    except Exception as e:
        raise HTTPException(502, f"File storage error: {e}")
    if entry.get("file_id"):
        await db.files.update_one({"id": entry["file_id"]}, {"$set": {"is_deleted": True}})
    fid = nid()
    await db.files.insert_one({"id": fid, "storage_path": res["path"], "original_filename": file.filename, "content_type": ALLOWED_FILES[ext],
                               "size": res.get("size", len(data)), "kb_id": kid, "is_deleted": False, "created_at": now()})
    await db.knowledge_base.update_one({"id": kid}, {"$set": {"file_id": fid, "file_name": file.filename, "updated_at": now()}})
    await log_activity(admin["user_id"], "knowledge_base", kid, "file_uploaded", entry.get("file_name"), file.filename)
    return await db.knowledge_base.find_one({"id": kid}, NO_ID)


@api.delete("/admin/kb/{kid}/file")
async def remove_kb_file(kid: str, admin=Depends(get_admin)):
    entry = await db.knowledge_base.find_one({"id": kid}, NO_ID)
    if not entry or not entry.get("file_id"):
        raise HTTPException(404, "No file attached")
    await db.files.update_one({"id": entry["file_id"]}, {"$set": {"is_deleted": True}})
    await db.knowledge_base.update_one({"id": kid}, {"$set": {"file_id": None, "file_name": None, "updated_at": now()}})
    await log_activity(admin["user_id"], "knowledge_base", kid, "file_removed", entry.get("file_name"))
    return {"ok": True}


@api.get("/files/{fid}")
async def download_file(fid: str, request: Request):
    rec = await db.files.find_one({"id": fid, "is_deleted": False}, NO_ID)
    if not rec:
        raise HTTPException(404, "File not found")
    kb = await db.knowledge_base.find_one({"id": rec.get("kb_id"), "file_id": fid}, NO_ID)
    if not kb or not kb.get("published"):
        await get_admin(request)
    data = await asyncio.to_thread(get_object, rec["storage_path"])
    safe = re.sub(r'[^A-Za-z0-9._ -]', "_", rec["original_filename"])
    return Response(content=data, media_type=rec["content_type"], headers={"Content-Disposition": f'inline; filename="{safe}"'})


# ---------------- Settings & templates ----------------
async def get_settings():
    return await db.settings.find_one({"key": "app"}, NO_ID) or {}


async def get_template(key):
    return await db.email_templates.find_one({"key": key}, NO_ID)


def render(text, vals):
    for k, v in vals.items():
        text = text.replace(f"[{k}]", str(v if v not in (None, "") else "—"))
    return text


# ---------------- Google OAuth / Gmail / Calendar ----------------
class GoogleNotReady(Exception):
    pass


def google_conf():
    cid, sec, red = (os.environ.get("GOOGLE_CLIENT_ID"), os.environ.get("GOOGLE_CLIENT_SECRET"),
                     os.environ.get("GOOGLE_REDIRECT_URI"))
    return (cid, sec, red) if cid and sec and red else None


async def google_token(scope):
    conf = google_conf()
    if not conf:
        raise GoogleNotReady("Google OAuth credentials are not configured on the server")
    doc = await db.integrations.find_one({"key": "google"})
    if not doc or not doc.get("refresh_token"):
        raise GoogleNotReady("Google account (tpwnitb@gmail.com) is not connected")
    if (doc.get("email") or "").lower() != OFFICIAL_EMAIL:
        raise GoogleNotReady("Connected Google account is not the official account")
    if scope not in (doc.get("scopes") or []):
        raise GoogleNotReady(f"Missing Google permission: {scope}")
    exp = datetime.fromisoformat(doc["expires_at"]) if doc.get("expires_at") else None
    if doc.get("access_token") and exp and exp - timedelta(seconds=60) > datetime.now(timezone.utc):
        return doc["access_token"]
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post("https://oauth2.googleapis.com/token", data={
            "client_id": conf[0], "client_secret": conf[1], "refresh_token": doc["refresh_token"],
            "grant_type": "refresh_token"})
    if r.status_code != 200:
        await db.integrations.update_one({"key": "google"}, {"$set": {"last_error": f"Token refresh failed: {r.text[:200]}"}})
        raise GoogleNotReady("Google token refresh failed — please reconnect")
    t = r.json()
    await db.integrations.update_one({"key": "google"}, {"$set": {
        "access_token": t["access_token"], "last_check_at": now(), "last_error": None,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=t.get("expires_in", 3600))).isoformat()}})
    return t["access_token"]


async def gmail_send(to, subject, body):
    token = await google_token("https://www.googleapis.com/auth/gmail.send")
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["From"] = f"Training & Placement Cell, MANIT Bhopal <{OFFICIAL_EMAIL}>"
    msg["Subject"] = Header(subject, "utf-8")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                         headers={"Authorization": f"Bearer {token}"}, json={"raw": raw})
    if r.status_code != 200:
        raise RuntimeError(f"Gmail API error {r.status_code}: {r.text[:300]}")
    return r.json()["id"]


async def dispatch_email(to, subject, body, email_type, lead=None, visit_id=None, call_id=None,
                         request_id=None, company_name=None, hr_name=None, notify_key=None):
    log = {"id": nid(), "company_lead_id": (lead or {}).get("id"), "visit_request_id": visit_id,
           "call_request_id": call_id, "related_request_id": request_id, "recipient_email": to,
           "company_name": company_name or (lead or {}).get("company_name"),
           "hr_name": hr_name or (lead or {}).get("hr_name"), "email_type": email_type,
           "subject": subject, "body": body, "delivery_status": "Queued", "provider_message_id": None,
           "error": None, "sent_at": None, "notify_key": notify_key, "created_at": now()}
    await db.email_logs.insert_one(dict(log))
    try:
        mid = await gmail_send(to, subject, body)
        upd = {"delivery_status": "Sent", "provider_message_id": mid, "sent_at": now()}
    except Exception as e:
        upd = {"delivery_status": "Failed", "error": str(e)}
    await db.email_logs.update_one({"id": log["id"]}, {"$set": upd})
    log.update(upd)
    log.pop("_id", None)
    if upd["delivery_status"] == "Sent" and log["company_lead_id"]:
        await db.company_leads.update_one({"id": log["company_lead_id"]}, {"$set": {"last_contact_at": now()}})
    return log


async def gcal(method, path, body=None):
    token = await google_token("https://www.googleapis.com/auth/calendar.events")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.request(method, f"https://www.googleapis.com/calendar/v3/calendars/primary/events{path}",
                            headers={"Authorization": f"Bearer {token}"}, json=body)
    if r.status_code not in (200, 204, 410):
        raise RuntimeError(f"Calendar API error {r.status_code}: {r.text[:200]}")
    return r.json() if r.status_code == 200 else {}


async def google_busy(d):
    token = await google_token("https://www.googleapis.com/auth/calendar.freebusy")
    start = datetime.fromisoformat(f"{d}T00:00:00").replace(tzinfo=IST)
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post("https://www.googleapis.com/calendar/v3/freeBusy",
                         headers={"Authorization": f"Bearer {token}"},
                         json={"timeMin": start.isoformat(), "timeMax": (start + timedelta(days=1)).isoformat(),
                               "timeZone": "Asia/Kolkata", "items": [{"id": "primary"}]})
    if r.status_code != 200:
        raise RuntimeError(f"FreeBusy error {r.status_code}")
    busy = r.json().get("calendars", {}).get("primary", {}).get("busy", [])
    return [(datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
             datetime.fromisoformat(b["end"].replace("Z", "+00:00"))) for b in busy]


@api.get("/admin/google/status")
async def google_status(admin=Depends(get_admin)):
    doc = await db.integrations.find_one({"key": "google"}, NO_ID) or {}
    scopes = doc.get("scopes") or []
    ok = bool(doc.get("refresh_token")) and (doc.get("email") or "").lower() == OFFICIAL_EMAIL
    return {"configured": bool(google_conf()), "connected": ok, "account": doc.get("email"),
            "gmail": ok and GOOGLE_SCOPES[2] in scopes,
            "calendar": ok and GOOGLE_SCOPES[3] in scopes and GOOGLE_SCOPES[4] in scopes,
            "last_check_at": doc.get("last_check_at"), "connected_at": doc.get("connected_at"),
            "last_error": doc.get("last_error"), "official_email": OFFICIAL_EMAIL,
            "redirect_uri": os.environ.get("GOOGLE_REDIRECT_URI"), "scopes": GOOGLE_SCOPES,
            "env_vars": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"]}


@api.get("/admin/google/connect")
async def google_connect(admin=Depends(get_admin)):
    conf = google_conf()
    if not conf:
        raise HTTPException(400, "Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI first")
    state = secrets.token_urlsafe(32)
    await db.oauth_states.insert_one({"state": state, "admin_id": admin["user_id"], "created_at": now()})
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": conf[0], "redirect_uri": conf[2], "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES), "access_type": "offline", "prompt": "consent",
        "include_granted_scopes": "true", "login_hint": OFFICIAL_EMAIL, "state": state})
    return {"url": url}


@api.get("/oauth/google/callback")
async def google_callback(state: str = "", code: str = "", error: str = ""):
    conf = google_conf()
    if not conf:
        raise HTTPException(400, "Google OAuth not configured")
    p = urlparse(conf[2])
    back = f"{p.scheme}://{p.netloc}/admin/settings"
    st = await db.oauth_states.find_one_and_delete({"state": state})
    if not st or datetime.fromisoformat(st["created_at"]) < datetime.now(timezone.utc) - timedelta(minutes=10):
        return RedirectResponse(f"{back}?google=invalid_state")
    if error or not code:
        return RedirectResponse(f"{back}?google=denied")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post("https://oauth2.googleapis.com/token", data={
            "code": code, "client_id": conf[0], "client_secret": conf[1], "redirect_uri": conf[2],
            "grant_type": "authorization_code"})
        if r.status_code != 200:
            await db.integrations.update_one({"key": "google"}, {"$set": {"last_error": "Token exchange failed"}}, upsert=True)
            return RedirectResponse(f"{back}?google=token_error")
        t = r.json()
        u = await c.get("https://openidconnect.googleapis.com/v1/userinfo",
                        headers={"Authorization": f"Bearer {t['access_token']}"})
    email = (u.json().get("email") or "").lower() if u.status_code == 200 else ""
    if email != OFFICIAL_EMAIL:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post("https://oauth2.googleapis.com/revoke", params={"token": t["access_token"]})
        await db.integrations.update_one({"key": "google"}, {"$set": {
            "last_error": f"Rejected account {email or 'unknown'} — only {OFFICIAL_EMAIL} may be connected"}}, upsert=True)
        return RedirectResponse(f"{back}?google=wrong_account")
    prev = await db.integrations.find_one({"key": "google"}) or {}
    await db.integrations.update_one({"key": "google"}, {"$set": {
        "email": email, "access_token": t["access_token"],
        "refresh_token": t.get("refresh_token") or prev.get("refresh_token"),
        "scopes": t.get("scope", "").split(), "connected_at": now(), "last_check_at": now(), "last_error": None,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=t.get("expires_in", 3600))).isoformat()}}, upsert=True)
    await log_activity(st["admin_id"], "integration", "google", "connected", None, email)
    return RedirectResponse(f"{back}?google=connected")


@api.post("/admin/google/disconnect")
async def google_disconnect(admin=Depends(get_admin)):
    doc = await db.integrations.find_one({"key": "google"}) or {}
    if doc.get("refresh_token"):
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post("https://oauth2.googleapis.com/revoke", params={"token": doc["refresh_token"]})
    await db.integrations.delete_one({"key": "google"})
    await log_activity(admin["user_id"], "integration", "google", "disconnected")
    return {"ok": True}


@api.post("/admin/google/check")
async def google_check(admin=Depends(get_admin)):
    try:
        await db.integrations.update_one({"key": "google"}, {"$set": {"expires_at": None}})
        await google_token("https://www.googleapis.com/auth/gmail.send")
        return {"ok": True}
    except GoogleNotReady as e:
        raise HTTPException(400, str(e))


# ---------------- Company leads ----------------
LEAD_FIELDS = ["company_name", "hr_name", "designation", "work_email", "contact_number", "interest_status",
               "remarks", "recruitment_request", "jnf_status", "jnf_remarks", "next_followup_at", "last_contact_at"]


def new_lead(data):
    t = now()
    lead = {"id": nid(), "company_name": "", "hr_name": "", "designation": "", "work_email": "",
            "contact_number": "", "interest_status": "Warm", "remarks": "", "recruitment_request": "",
            "invitation_status": "Not Sent", "invitation_sent_at": None, "invitation_success_at": None,
            "invitation_message_id": None, "invitation_error": None, "jnf_status": "Awaited", "jnf_remarks": "",
            "last_contact_at": None, "next_followup_at": None, "status_history": [], "created_at": t, "updated_at": t}
    lead.update({k: v for k, v in data.items() if k in LEAD_FIELDS and v is not None})
    lead["work_email"] = (lead["work_email"] or "").strip().lower()
    lead["status_history"] = [{"status": lead["interest_status"], "at": t}]
    return lead


def check_lead(upd):
    if "interest_status" in upd and upd["interest_status"] not in LEAD_STATUSES:
        raise HTTPException(400, "Status must be Hot, Warm or Cold")
    if "jnf_status" in upd and upd["jnf_status"] not in ["Awaited", "Received"]:
        raise HTTPException(400, "JNF status must be Awaited or Received")
    if "company_name" in upd and not str(upd["company_name"]).strip():
        raise HTTPException(400, "Company name is required")
    if upd.get("work_email") and not EMAIL_RE.match(upd["work_email"].strip()):
        raise HTTPException(400, "Invalid HR email address")


async def send_invitation(lead_id, manual=False):
    lead = await db.company_leads.find_one({"id": lead_id}, NO_ID)
    if not lead:
        return {"ok": False, "message": "Company not found"}
    if not lead["company_name"].strip() or not EMAIL_RE.match(lead.get("work_email") or ""):
        return {"ok": False, "message": "Invitation not sent: a valid company name and HR email are required."}
    q = {"id": lead_id, "invitation_status": {"$ne": "Queued"}}
    if not manual:
        q["invitation_success_at"] = None
    locked = await db.company_leads.find_one_and_update(q, {"$set": {"invitation_status": "Queued"}})
    if not locked:
        return {"ok": False, "skipped": True, "message": "Invitation already sent earlier — no duplicate sent."}
    tpl = await get_template("invitation")
    vals = {"COMPANY_NAME": lead["company_name"], "HR_NAME": lead["hr_name"], "JNF_URL": (await get_settings()).get("jnf_url", JNF_URL)}
    log = await dispatch_email(lead["work_email"], render(tpl["subject"], vals), render(tpl["body"], vals),
                               "Recruitment Invitation", lead=lead)
    if log["delivery_status"] == "Sent":
        await db.company_leads.update_one({"id": lead_id}, {"$set": {
            "invitation_status": "Sent", "invitation_sent_at": log["sent_at"], "invitation_message_id": log["provider_message_id"],
            "invitation_success_at": locked.get("invitation_success_at") or log["sent_at"], "invitation_error": None}})
        return {"ok": True, "message": f"Invitation submitted to Gmail for {lead['work_email']} (message ID {log['provider_message_id']})."}
    status = "Sent" if locked.get("invitation_success_at") else "Failed"
    await db.company_leads.update_one({"id": lead_id}, {"$set": {"invitation_status": status, "invitation_error": log["error"]}})
    return {"ok": False, "message": f"Invitation email failed: {log['error']}"}


async def find_or_create_lead(data, status=None):
    email = (data.get("work_email") or "").strip().lower()
    lead = None
    if email:
        lead = await db.company_leads.find_one({"work_email": email}, NO_ID)
    if not lead and data.get("company_name"):
        lead = await db.company_leads.find_one(
            {"company_name": {"$regex": f"^{re.escape(data['company_name'].strip())}$", "$options": "i"}}, NO_ID)
    if not lead:
        lead = new_lead({**data, "interest_status": status or "Warm"})
        await db.company_leads.insert_one(dict(lead))
        await log_activity("system", "company_lead", lead["id"], "created", None, lead["company_name"])
        return lead, None
    fill = {k: data[k] for k in ["hr_name", "designation", "work_email", "contact_number"] if data.get(k) and not lead.get(k)}
    if fill:
        await db.company_leads.update_one({"id": lead["id"]}, {"$set": {**fill, "updated_at": now()}})
    return await db.company_leads.find_one({"id": lead["id"]}, NO_ID), lead["interest_status"]


async def set_status(lead, new_status, actor):
    prev = lead["interest_status"]
    if prev == new_status:
        return
    await db.company_leads.update_one({"id": lead["id"]}, {
        "$set": {"interest_status": new_status, "updated_at": now()},
        "$push": {"status_history": {"status": new_status, "from": prev, "at": now(), "by": actor}}})
    await log_activity(actor, "company_lead", lead["id"], "status_change", prev, new_status)


@api.get("/admin/leads")
async def list_leads(q: str = "", status: str = "", sort: str = "updated_at", order: str = "desc", admin=Depends(get_admin)):
    f = {}
    if status in LEAD_STATUSES:
        f["interest_status"] = status
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        f["$or"] = [{"company_name": rx}, {"hr_name": rx}]
    key = sort if sort in ["company_name", "interest_status", "last_contact_at", "updated_at"] else "updated_at"
    return await db.company_leads.find(f, NO_ID).sort(key, -1 if order == "desc" else 1).to_list(2000)


@api.post("/admin/leads")
async def create_lead(body: dict, admin=Depends(get_admin)):
    check_lead({**body, "company_name": body.get("company_name", "")})
    lead = new_lead(body)
    await db.company_leads.insert_one(dict(lead))
    await log_activity(admin["user_id"], "company_lead", lead["id"], "created", None, lead["company_name"])
    inv = await send_invitation(lead["id"]) if lead["interest_status"] == "Hot" else None
    return {"lead": await db.company_leads.find_one({"id": lead["id"]}, NO_ID), "invitation": inv}


@api.get("/admin/leads/{lead_id}")
async def lead_detail(lead_id: str, admin=Depends(get_admin)):
    lead = await db.company_leads.find_one({"id": lead_id}, NO_ID)
    if not lead:
        raise HTTPException(404, "Company not found")
    return {"lead": lead,
            "emails": await db.email_logs.find({"company_lead_id": lead_id}, {"_id": 0, "body": 0}).sort("created_at", -1).to_list(200),
            "visits": await db.visit_requests.find({"company_lead_id": lead_id}, NO_ID).sort("created_at", -1).to_list(100),
            "calls": await db.call_requests.find({"company_lead_id": lead_id}, NO_ID).sort("created_at", -1).to_list(100)}


@api.patch("/admin/leads/{lead_id}")
async def update_lead(lead_id: str, body: dict, admin=Depends(get_admin)):
    lead = await db.company_leads.find_one({"id": lead_id}, NO_ID)
    if not lead:
        raise HTTPException(404, "Company not found")
    upd = {k: v for k, v in body.items() if k in LEAD_FIELDS and k != "interest_status"}
    check_lead(body)
    if "work_email" in upd:
        upd["work_email"] = (upd["work_email"] or "").strip().lower()
    changed = {k: v for k, v in upd.items() if lead.get(k) != v}
    if changed:
        await db.company_leads.update_one({"id": lead_id}, {"$set": {**changed, "updated_at": now()}})
        for k, v in changed.items():
            await log_activity(admin["user_id"], "company_lead", lead_id, f"update:{k}", lead.get(k), v)
        if {"remarks", "recruitment_request"} & changed.keys():
            asyncio.create_task(store_status_suggestion(lead_id))
    inv = None
    new_status = body.get("interest_status")
    if new_status and new_status != lead["interest_status"]:
        await set_status(lead, new_status, admin["user_id"])
        if new_status == "Hot":
            inv = await send_invitation(lead_id)
    return {"lead": await db.company_leads.find_one({"id": lead_id}, NO_ID), "invitation": inv}


@api.post("/admin/leads/{lead_id}/suggest-status")
async def suggest_lead_status(lead_id: str, admin=Depends(get_admin)):
    lead = await db.company_leads.find_one({"id": lead_id}, NO_ID)
    if not lead:
        raise HTTPException(404, "Company not found")
    if not (lead.get("remarks") or lead.get("recruitment_request")):
        raise HTTPException(400, "Add remarks or a recruitment request first")
    sug = await jev.suggest_status(lead)
    await db.company_leads.update_one({"id": lead_id}, {"$set": {"ai_status_suggestion": sug}})
    return sug


@api.delete("/admin/leads/{lead_id}")
async def delete_lead(lead_id: str, admin=Depends(get_admin)):
    lead = await db.company_leads.find_one_and_delete({"id": lead_id})
    if not lead:
        raise HTTPException(404, "Company not found")
    await log_activity(admin["user_id"], "company_lead", lead_id, "deleted", lead["company_name"])
    return {"ok": True}


@api.post("/admin/leads/{lead_id}/invite")
async def invite_lead(lead_id: str, admin=Depends(get_admin)):
    res = await send_invitation(lead_id, manual=True)
    await log_activity(admin["user_id"], "company_lead", lead_id, "manual_invitation", None, res["message"])
    return res


@api.post("/admin/leads/{lead_id}/jnf-reminder")
async def jnf_reminder(lead_id: str, admin=Depends(get_admin)):
    lead = await db.company_leads.find_one({"id": lead_id}, NO_ID)
    if not lead or not EMAIL_RE.match(lead.get("work_email") or ""):
        raise HTTPException(400, "Valid HR email required")
    tpl = await get_template("jnf_reminder")
    vals = {"COMPANY_NAME": lead["company_name"], "HR_NAME": lead["hr_name"], "JNF_URL": (await get_settings()).get("jnf_url", JNF_URL)}
    log = await dispatch_email(lead["work_email"], render(tpl["subject"], vals), render(tpl["body"], vals), "JNF Reminder", lead=lead)
    await log_activity(admin["user_id"], "company_lead", lead_id, "jnf_reminder", None, log["delivery_status"])
    return {"ok": log["delivery_status"] == "Sent", "message": "JNF reminder submitted to Gmail" if log["delivery_status"] == "Sent" else f"Failed: {log['error']}"}


@api.get("/admin/stats")
async def stats(admin=Depends(get_admin)):
    cl, t = db.company_leads, today_ist()
    return {
        "total": await cl.count_documents({}),
        "hot": await cl.count_documents({"interest_status": "Hot"}),
        "warm": await cl.count_documents({"interest_status": "Warm"}),
        "cold": await cl.count_documents({"interest_status": "Cold"}),
        "invitations_sent": await cl.count_documents({"invitation_success_at": {"$ne": None}}),
        "jnf_awaited": await cl.count_documents({"jnf_status": "Awaited"}),
        "jnf_received": await cl.count_documents({"jnf_status": "Received"}),
        "pending_visits": await db.visit_requests.count_documents({"status": {"$in": ["Pending Approval", "Alternative Proposed"]}}),
        "upcoming_visits": await db.visit_requests.count_documents({"status": {"$in": ACTIVE}, "approved_date": {"$gte": t}}),
        "pending_calls": await db.call_requests.count_documents({"status": "Pending"}),
        "scheduled_calls": await db.call_requests.count_documents({"status": {"$in": ACTIVE}, "approved_date": {"$gte": t}}),
    }


# ---------------- Visit & call requests ----------------
def coll_of(kind):
    return "visit_requests" if kind == "visits" else "call_requests"


def slot_of(ent, is_visit):
    if is_visit:
        return ent.get("approved_start_time"), ent.get("approved_end_time")
    if not ent.get("approved_time"):
        return None, None
    return ent["approved_time"], add_minutes(ent["approved_time"], ent.get("approved_duration") or 30)


async def busy_internal(d, exclude_id=None):
    out = []
    async for v in db.visit_requests.find({"status": {"$in": ACTIVE}, "approved_date": d}, NO_ID):
        if v["id"] != exclude_id:
            out.append((v["approved_start_time"], v["approved_end_time"], f"approved campus visit {v['id']}"))
    async for c in db.call_requests.find({"status": {"$in": ACTIVE}, "approved_date": d}, NO_ID):
        if c["id"] != exclude_id:
            s, e = slot_of(c, False)
            out.append((s, e, f"approved call {c['id']}"))
    return out


async def find_conflict(d, start, end, exclude_id=None, own_slot=None):
    for s, e, label in await busy_internal(d, exclude_id):
        if start < e and s < end:
            return f"Conflicts with {label} ({s}–{e})"
    try:
        s_dt, e_dt = to_dt(d, start), to_dt(d, end)
        for bs, be in await google_busy(d):
            if own_slot and bs == own_slot[0] and be == own_slot[1]:
                continue
            if s_dt < be and bs < e_dt:
                return f"Conflicts with a busy slot on Google Calendar ({bs.astimezone(IST):%H:%M}–{be.astimezone(IST):%H:%M})"
    except GoogleNotReady:
        pass
    except Exception as ex:
        logger.warning("freebusy failed: %s", ex)
    return None


def validate_request(kind, b):
    for k in ["company_name", "hr_name", "work_email"]:
        if not str(b.get(k) or "").strip():
            raise HTTPException(400, f"{k.replace('_', ' ').title()} is required")
    if not EMAIL_RE.match(b["work_email"].strip()):
        raise HTTPException(400, "Invalid work email")
    if kind == "visits":
        validate_slot(b.get("requested_date"), b.get("requested_start_time"), b.get("requested_end_time"))
        d = b["requested_date"]
        if b.get("visit_purpose") not in VISIT_PURPOSES:
            raise HTTPException(400, "Invalid visit purpose")
    else:
        d = b.get("preferred_date")
        validate_slot(d, b.get("preferred_time"), "23:59")
        if int(b.get("duration") or 0) not in DURATIONS:
            raise HTTPException(400, "Duration must be 15, 30, 45 or 60 minutes")
        if b.get("call_mode") not in CALL_MODES:
            raise HTTPException(400, "Invalid call mode")
    if d < today_ist():
        raise HTTPException(400, "Date cannot be in the past")


async def screen_and_store(kind, doc):
    d = doc.get("requested_date") or doc.get("preferred_date")
    days = (date_cls.fromisoformat(d) - datetime.now(IST).date()).days
    res = await jev.screen_request(doc, kind, days)
    res["junk_flag"] = res.get("junk_probability", 0) >= 0.8
    await db[coll_of(kind)].update_one({"id": doc["id"]}, {"$set": {"ai_screen": res}})


async def store_status_suggestion(lead_id):
    lead = await db.company_leads.find_one({"id": lead_id}, NO_ID)
    if lead and (lead.get("remarks") or lead.get("recruitment_request")):
        await db.company_leads.update_one({"id": lead_id}, {"$set": {"ai_status_suggestion": await jev.suggest_status(lead)}})


async def create_request(kind, b):
    validate_request(kind, b)
    lead, _ = await find_or_create_lead(b)
    t = now()
    base = {"company_lead_id": lead["id"], "company_name": b["company_name"].strip(), "hr_name": b["hr_name"].strip(),
            "designation": b.get("designation", ""), "work_email": b["work_email"].strip().lower(),
            "contact_number": b.get("contact_number", ""), "remarks": b.get("remarks", ""), "admin_notes": "",
            "calendar_event_id": None, "calendar_sync_status": "Not Synced", "sent_notifications": [],
            "history": [], "created_at": t, "updated_at": t}
    if kind == "visits":
        doc = {**base, "id": f"VR-{secrets.token_hex(3).upper()}", "visit_purpose": b["visit_purpose"],
               "requested_date": b["requested_date"], "requested_start_time": b["requested_start_time"],
               "requested_end_time": b["requested_end_time"], "approved_date": None, "approved_start_time": None,
               "approved_end_time": None, "status": "Pending Approval", "rejection_reason": None, "approved_at": None}
    else:
        doc = {**base, "id": f"CR-{secrets.token_hex(3).upper()}", "discussion_purpose": b.get("discussion_purpose", ""),
               "preferred_date": b["preferred_date"], "preferred_time": b["preferred_time"], "duration": int(b["duration"]),
               "approved_date": None, "approved_time": None, "approved_duration": None, "call_mode": b["call_mode"],
               "meeting_link": b.get("meeting_link", ""), "status": "Pending"}
    await db[coll_of(kind)].insert_one(dict(doc))
    await log_activity("public", coll_of(kind), doc["id"], "created", None, doc["status"])
    asyncio.create_task(screen_and_store(kind, doc))
    return doc


def placeholders(ent, is_visit):
    s, e = slot_of(ent, is_visit)
    return {"COMPANY_NAME": ent["company_name"], "HR_NAME": ent["hr_name"], "REQUEST_ID": ent["id"],
            "PURPOSE": ent.get("visit_purpose") if is_visit else ent.get("discussion_purpose"),
            "APPROVED_DATE": pretty_date(ent.get("approved_date")), "START_TIME": s, "END_TIME": e,
            "DURATION": ent.get("approved_duration"), "MODE": ent.get("call_mode"),
            "MEETING_LINK": ent.get("meeting_link") or "To be shared",
            "ITEM": "campus visit" if is_visit else "call with the Head of Training & Placement"}


async def notify(coll, ent, kind):
    is_visit = coll == "visit_requests"
    s, e = slot_of(ent, is_visit)
    key = f"{kind}|{ent.get('approved_date')}|{s}|{e}"
    if key in (ent.get("sent_notifications") or []):
        return {"ok": True, "skipped": True, "message": "Email already sent for this schedule"}
    tpl_key = {"confirmation": "visit_confirmation" if is_visit else "call_confirmation",
               "rescheduling": "rescheduling", "cancellation": "cancellation"}[kind]
    etype = {"confirmation": "Campus Visit Confirmation" if is_visit else "Call Confirmation",
             "rescheduling": "Rescheduling Update", "cancellation": "Cancellation Update"}[kind]
    tpl = await get_template(tpl_key)
    vals = placeholders(ent, is_visit)
    lead = await db.company_leads.find_one({"id": ent.get("company_lead_id")}, NO_ID)
    log = await dispatch_email(ent["work_email"], render(tpl["subject"], vals), render(tpl["body"], vals), etype,
                               lead=lead, visit_id=ent["id"] if is_visit else None, call_id=None if is_visit else ent["id"],
                               request_id=ent["id"], company_name=ent["company_name"], hr_name=ent["hr_name"], notify_key=key)
    upd = {"last_email_status": f"{etype}: {log['delivery_status']}"}
    if log["delivery_status"] == "Sent":
        await db[coll].update_one({"id": ent["id"]}, {"$set": upd, "$addToSet": {"sent_notifications": key}})
        return {"ok": True, "message": f"{etype} submitted to Gmail"}
    await db[coll].update_one({"id": ent["id"]}, {"$set": upd})
    return {"ok": False, "message": f"{etype} email failed: {log['error']}"}


async def sync_event(coll, ent, delete=False):
    is_visit = coll == "visit_requests"
    try:
        if delete:
            if ent.get("calendar_event_id"):
                await gcal("DELETE", f"/{ent['calendar_event_id']}")
                st = "Deleted"
            else:
                return "Not Synced"
            await db[coll].update_one({"id": ent["id"]}, {"$set": {"calendar_sync_status": st}})
            return st
        s, e = slot_of(ent, is_visit)
        if is_visit:
            summary = f"Campus Visit: {ent['company_name']} — {ent['visit_purpose']}"
            desc = f"Request ID: {ent['id']}\nPurpose: {ent['visit_purpose']}\nHR: {ent['hr_name']} ({ent['work_email']}, {ent.get('contact_number') or '-'})"
        else:
            summary = f"Call: {ent['company_name']} — {ent['hr_name']}"
            desc = (f"Call Request ID: {ent['id']}\nPurpose: {ent.get('discussion_purpose') or '-'}\nDuration: {ent['approved_duration']} min\n"
                    f"Mode: {ent['call_mode']}\nMeeting link: {ent.get('meeting_link') or '-'}\nHR: {ent['hr_name']} ({ent['work_email']})")
        body = {"summary": summary, "description": desc,
                "start": {"dateTime": f"{ent['approved_date']}T{s}:00", "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": f"{ent['approved_date']}T{e}:00", "timeZone": "Asia/Kolkata"}}
        if ent.get("calendar_event_id"):
            ev = await gcal("PATCH", f"/{ent['calendar_event_id']}", body)
        else:
            ev = await gcal("POST", "", body)
        await db[coll].update_one({"id": ent["id"]}, {"$set": {"calendar_event_id": ev["id"], "calendar_sync_status": "Synced"}})
        return "Synced"
    except GoogleNotReady as ex:
        st = f"Not Synced — {ex}"
    except Exception as ex:
        st = f"Sync Failed — {ex}"
    await db[coll].update_one({"id": ent["id"]}, {"$set": {"calendar_sync_status": st}})
    return st


class ActionIn(BaseModel):
    action: str
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: Optional[int] = None
    meeting_link: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


PENDING = ["Pending Approval", "Pending", "Alternative Proposed"]


async def schedule(coll, ent, a: ActionIn, admin_id):
    is_visit = coll == "visit_requests"
    approve = a.action == "approve"
    if approve and ent["status"] not in PENDING:
        raise HTTPException(400, f"Cannot approve a request with status {ent['status']}")
    if not approve and ent["status"] not in ACTIVE:
        raise HTTPException(400, "Only approved items can be rescheduled")
    if is_visit:
        d = a.date or ent.get("proposed_date") or ent["requested_date"]
        s = a.start_time or ent.get("proposed_start_time") or ent["requested_start_time"]
        e = a.end_time or ent.get("proposed_end_time") or ent["requested_end_time"]
        dur = None
    else:
        d = a.date or ent["preferred_date"]
        s = a.start_time or ent["preferred_time"]
        dur = int(a.duration or ent.get("approved_duration") or ent["duration"])
        if dur not in DURATIONS:
            raise HTTPException(400, "Invalid duration")
        e = add_minutes(s, dur)
    validate_slot(d, s, e)
    if d < today_ist():
        raise HTTPException(400, "Date cannot be in the past")
    os_, oe = slot_of(ent, is_visit)
    own = (to_dt(ent["approved_date"], os_), to_dt(ent["approved_date"], oe)) if ent.get("calendar_event_id") and os_ else None
    async with APPROVAL_LOCK:
        conflict = await find_conflict(d, s, e, ent["id"], own)
        if conflict:
            raise HTTPException(409, conflict)
        upd = {"approved_date": d, "status": "Approved" if approve else "Rescheduled", "updated_at": now()}
        if is_visit:
            upd.update({"approved_start_time": s, "approved_end_time": e})
            if approve:
                upd["approved_at"] = now()
        else:
            upd.update({"approved_time": s, "approved_duration": dur})
            if a.meeting_link is not None:
                upd["meeting_link"] = a.meeting_link
        if a.notes:
            upd["admin_notes"] = a.notes
        hist = {"at": now(), "action": a.action, "by": admin_id, "from": f"{ent.get('approved_date')} {os_}-{oe}" if os_ else None,
                "to": f"{d} {s}-{e}"}
        await db[coll].update_one({"id": ent["id"]}, {"$set": upd, "$push": {"history": hist}})
    await log_activity(admin_id, coll, ent["id"], a.action, hist["from"], hist["to"])
    ent = await db[coll].find_one({"id": ent["id"]}, NO_ID)
    cal = await sync_event(coll, ent)
    mail = await notify(coll, ent, "confirmation" if approve else "rescheduling")
    return {"item": await db[coll].find_one({"id": ent["id"]}, NO_ID), "calendar": cal, "email": mail}


async def do_action(kind, rid, a: ActionIn, admin_id):
    coll = coll_of(kind)
    ent = await db[coll].find_one({"id": rid}, NO_ID)
    if not ent:
        raise HTTPException(404, "Request not found")
    if a.action in ("approve", "reschedule"):
        return await schedule(coll, ent, a, admin_id)
    upd, res = {"updated_at": now()}, {}
    if a.action == "reject":
        if ent["status"] not in PENDING:
            raise HTTPException(400, "Only pending requests can be rejected")
        upd.update({"status": "Rejected", "rejection_reason": a.reason or ""})
    elif a.action == "propose_alternative":
        if kind != "visits" or ent["status"] not in PENDING:
            raise HTTPException(400, "Alternative can only be proposed for pending visit requests")
        validate_slot(a.date, a.start_time, a.end_time)
        upd.update({"status": "Alternative Proposed", "proposed_date": a.date, "proposed_start_time": a.start_time,
                    "proposed_end_time": a.end_time})
    elif a.action == "cancel":
        if ent["status"] in ("Cancelled", "Completed", "Rejected"):
            raise HTTPException(400, f"Request is already {ent['status']}")
        upd["status"] = "Cancelled"
        if ent["status"] in ACTIVE:
            res["calendar"] = await sync_event(coll, ent, delete=True)
            res["email"] = await notify(coll, ent, "cancellation")
    elif a.action == "complete":
        if ent["status"] not in ACTIVE:
            raise HTTPException(400, "Only approved items can be completed")
        upd["status"] = "Completed"
    elif a.action in ("mark_genuine", "mark_junk"):
        upd["junk_reviewed"] = True
        if a.action == "mark_junk":
            if ent["status"] not in PENDING:
                raise HTTPException(400, "Only pending requests can be marked as junk")
            upd.update({"status": "Rejected", "rejection_reason": "Marked as junk by admin"})
    elif a.action == "ack_urgent":
        upd["urgent_ack"] = True
    elif a.action == "notes":
        upd["admin_notes"] = a.notes or ""
    elif a.action == "send_confirmation":
        if ent["status"] not in ACTIVE:
            raise HTTPException(400, "Confirmation can only be sent for approved items")
        return {"item": ent, "email": await notify(coll, ent, "confirmation" if ent["status"] == "Approved" else "rescheduling")}
    elif a.action == "sync_calendar":
        if ent["status"] not in ACTIVE:
            raise HTTPException(400, "Only approved items are synced")
        return {"item": ent, "calendar": await sync_event(coll, ent)}
    else:
        raise HTTPException(400, "Unknown action")
    await db[coll].update_one({"id": rid}, {"$set": upd, "$push": {"history": {"at": now(), "action": a.action, "by": admin_id}}})
    await log_activity(admin_id, coll, rid, a.action, ent["status"], upd.get("status") or a.notes)
    return {"item": await db[coll].find_one({"id": rid}, NO_ID), **res}


JUNK_Q = {"ai_screen.junk_flag": True, "junk_reviewed": {"$ne": True}}


@api.get("/admin/urgent")
async def urgent_requests(admin=Depends(get_admin)):
    f = {"status": {"$in": PENDING}, "ai_screen.urgency_label": "critical", "urgent_ack": {"$ne": True}, "$nor": [JUNK_Q]}
    out = []
    for kind in ("visits", "calls"):
        async for r in db[coll_of(kind)].find(f, NO_ID).sort("created_at", -1):
            out.append({"kind": kind, "id": r["id"], "company_name": r["company_name"], "hr_name": r["hr_name"],
                        "purpose": r.get("visit_purpose") or r.get("discussion_purpose"), "created_at": r["created_at"],
                        "date": r.get("requested_date") or r.get("preferred_date")})
    junk = sum([await db[coll_of(k)].count_documents(JUNK_Q) for k in ("visits", "calls")])
    return {"urgent": out, "junk_pending": junk}


@api.get("/admin/req/{kind}")
async def list_requests(kind: str, status: str = "", sort: str = "", view: str = "main", admin=Depends(get_admin)):
    if kind not in ("visits", "calls"):
        raise HTTPException(404)
    f = {"status": status} if status else {}
    f.update(JUNK_Q if view == "junk" else {"$nor": [JUNK_Q]})
    if sort == "urgency":
        return await db[coll_of(kind)].find(f, NO_ID).sort([("ai_screen.urgency_score", -1), ("created_at", -1)]).to_list(1000)
    return await db[coll_of(kind)].find(f, NO_ID).sort("created_at", -1).to_list(1000)


@api.post("/admin/req/{kind}")
async def admin_create_request(kind: str, body: dict, admin=Depends(get_admin)):
    if kind not in ("visits", "calls"):
        raise HTTPException(404)
    doc = await create_request(kind, body)
    try:
        return await do_action(kind, doc["id"], ActionIn(action="approve", meeting_link=body.get("meeting_link")), admin["user_id"])
    except HTTPException as e:
        return {"item": doc, "error": f"Saved as pending — could not auto-approve: {e.detail}"}


@api.post("/admin/req/{kind}/{rid}/action")
async def request_action(kind: str, rid: str, a: ActionIn, admin=Depends(get_admin)):
    if kind not in ("visits", "calls"):
        raise HTTPException(404)
    return await do_action(kind, rid, a, admin["user_id"])


@api.get("/admin/calendar")
async def calendar(month: str, admin=Depends(get_admin)):
    items = []
    rx = {"$regex": f"^{re.escape(month)}"}
    async for v in db.visit_requests.find({"$or": [{"approved_date": rx}, {"requested_date": rx}]}, NO_ID):
        confirmed = v["status"] in ACTIVE + ["Completed"] or (v["status"] == "Cancelled" and v.get("approved_date"))
        d = v["approved_date"] if v.get("approved_date") else v["requested_date"]
        s, e = (v["approved_start_time"], v["approved_end_time"]) if v.get("approved_date") else (v["requested_start_time"], v["requested_end_time"])
        items.append({"kind": "visit", "id": v["id"], "date": d, "start": s, "end": e, "status": v["status"],
                      "confirmed": bool(confirmed) and v["status"] != "Cancelled", "company": v["company_name"],
                      "title": v["visit_purpose"], "sync": v.get("calendar_sync_status"), "lead_id": v.get("company_lead_id")})
    async for c in db.call_requests.find({"$or": [{"approved_date": rx}, {"preferred_date": rx}]}, NO_ID):
        if c.get("approved_date"):
            d, (s, e) = c["approved_date"], slot_of(c, False)
        else:
            d, s, e = c["preferred_date"], c["preferred_time"], add_minutes(c["preferred_time"], c["duration"])
        items.append({"kind": "call", "id": c["id"], "date": d, "start": s, "end": e, "status": c["status"],
                      "confirmed": c["status"] in ACTIVE + ["Completed"], "company": c["company_name"],
                      "title": f"Call with {c['hr_name']}", "sync": c.get("calendar_sync_status"), "lead_id": c.get("company_lead_id")})
    return [i for i in items if i["date"].startswith(month)]


# ---------------- Emails ----------------
@api.get("/admin/emails")
async def list_emails(type: str = "", admin=Depends(get_admin)):
    f = {"email_type": type} if type else {}
    return await db.email_logs.find(f, {"_id": 0, "body": 0}).sort("created_at", -1).to_list(1000)


@api.post("/admin/emails/{eid}/retry")
async def retry_email(eid: str, admin=Depends(get_admin)):
    log = await db.email_logs.find_one({"id": eid}, NO_ID)
    if not log:
        raise HTTPException(404)
    if log["delivery_status"] != "Failed":
        raise HTTPException(400, "Only failed emails can be retried")
    await db.email_logs.update_one({"id": eid}, {"$set": {"delivery_status": "Failed (retried)"}})
    if log["email_type"] == "Recruitment Invitation" and log.get("company_lead_id"):
        res = await send_invitation(log["company_lead_id"], manual=True)
    elif log.get("notify_key"):
        coll = "visit_requests" if log.get("visit_request_id") else "call_requests"
        ent = await db[coll].find_one({"id": log["related_request_id"]}, NO_ID)
        if log["notify_key"] in (ent or {}).get("sent_notifications", []):
            return {"ok": True, "message": "Already sent successfully — not resent"}
        lead = await db.company_leads.find_one({"id": log.get("company_lead_id")}, NO_ID)
        new = await dispatch_email(log["recipient_email"], log["subject"], log["body"], log["email_type"], lead=lead,
                                   visit_id=log.get("visit_request_id"), call_id=log.get("call_request_id"),
                                   request_id=log.get("related_request_id"), company_name=log.get("company_name"),
                                   hr_name=log.get("hr_name"), notify_key=log["notify_key"])
        if new["delivery_status"] == "Sent" and ent:
            await db[coll].update_one({"id": ent["id"]}, {"$addToSet": {"sent_notifications": log["notify_key"]}})
        res = {"ok": new["delivery_status"] == "Sent", "message": new["delivery_status"] if new["delivery_status"] == "Sent" else new["error"]}
    else:
        lead = await db.company_leads.find_one({"id": log.get("company_lead_id")}, NO_ID)
        new = await dispatch_email(log["recipient_email"], log["subject"], log["body"], log["email_type"], lead=lead,
                                   company_name=log.get("company_name"), hr_name=log.get("hr_name"))
        res = {"ok": new["delivery_status"] == "Sent", "message": new["delivery_status"] if new["delivery_status"] == "Sent" else new["error"]}
    await log_activity(admin["user_id"], "email", eid, "retry", None, res["message"])
    return res


@api.post("/admin/emails/test-invitation")
async def test_invitation(body: dict, admin=Depends(get_admin)):
    to = (body.get("to") or admin["email"]).strip()
    if not EMAIL_RE.match(to):
        raise HTTPException(400, "Invalid email address")
    tpl = await get_template("invitation")
    vals = {"COMPANY_NAME": "TEST Company", "HR_NAME": "Test", "JNF_URL": (await get_settings()).get("jnf_url", JNF_URL)}
    log = await dispatch_email(to, "[TEST] " + render(tpl["subject"], vals), render(tpl["body"], vals), "Test Invitation",
                               company_name="TEST (no company record)")
    await log_activity(admin["user_id"], "email", log["id"], "test_invitation", None, log["delivery_status"])
    if log["delivery_status"] == "Sent":
        return {"ok": True, "message": f"Test invitation submitted to Gmail for {to} (message ID {log['provider_message_id']}). Check that inbox."}
    return {"ok": False, "message": f"Test invitation failed: {log['error']}"}


@api.post("/admin/emails/manual")
async def manual_email(body: dict, admin=Depends(get_admin)):
    to = (body.get("to") or "").strip()
    if not EMAIL_RE.match(to) or not body.get("subject") or not body.get("body"):
        raise HTTPException(400, "Recipient, subject and body are required")
    lead = await db.company_leads.find_one({"id": body.get("company_lead_id")}, NO_ID) if body.get("company_lead_id") else None
    log = await dispatch_email(to, body["subject"], body["body"], body.get("email_type") or "Manual Communication", lead=lead)
    await log_activity(admin["user_id"], "email", log["id"], "manual_send", None, log["delivery_status"])
    return {"ok": log["delivery_status"] == "Sent", "message": "Submitted to Gmail" if log["delivery_status"] == "Sent" else log["error"]}


@api.get("/admin/templates")
async def list_templates(admin=Depends(get_admin)):
    return await db.email_templates.find({}, NO_ID).to_list(50)


SAMPLE_VALS = {"COMPANY_NAME": "Sample Company Pvt. Ltd.", "HR_NAME": "Sample HR", "PURPOSE": "Campus Placement Drive",
               "APPROVED_DATE": "15 December 2026", "START_TIME": "10:00", "END_TIME": "13:00", "REQUEST_ID": "VR-SAMPLE",
               "DURATION": 30, "MODE": "Google Meet", "MEETING_LINK": "To be shared", "ITEM": "campus visit"}


@api.post("/admin/templates/{key}/preview")
async def preview_template(key: str, body: dict, admin=Depends(get_admin)):
    tpl = await get_template(key)
    if not tpl:
        raise HTTPException(404)
    vals = {**SAMPLE_VALS, "JNF_URL": (await get_settings()).get("jnf_url", JNF_URL)}
    to = "hr@sample-company.com"
    if body.get("lead_id"):
        lead = await db.company_leads.find_one({"id": body["lead_id"]}, NO_ID)
        if not lead:
            raise HTTPException(404, "Company not found")
        vals.update({"COMPANY_NAME": lead["company_name"], "HR_NAME": lead["hr_name"]})
        to = lead.get("work_email") or "(no HR email)"
    return {"from": f"Training & Placement Cell, MANIT Bhopal <{OFFICIAL_EMAIL}>", "to": to,
            "subject": render(body.get("subject") or tpl["subject"], vals), "body": render(body.get("body") or tpl["body"], vals)}


@api.put("/admin/templates/{key}")
async def update_template(key: str, body: dict, admin=Depends(get_admin)):
    old = await get_template(key)
    if not old:
        raise HTTPException(404)
    if not body.get("subject") or not body.get("body"):
        raise HTTPException(400, "Subject and body required")
    await db.email_templates.update_one({"key": key}, {"$set": {"subject": body["subject"], "body": body["body"], "updated_at": now()}})
    await log_activity(admin["user_id"], "email_template", key, "updated", old["subject"], body["subject"])
    return await get_template(key)


@api.get("/admin/settings")
async def read_settings(admin=Depends(get_admin)):
    return await get_settings()


@api.put("/admin/settings")
async def write_settings(body: dict, admin=Depends(get_admin)):
    old = await get_settings()
    upd = {}
    if "chat_model" in body:
        if body["chat_model"] not in AI_MODELS:
            raise HTTPException(400, "Unknown AI model")
        upd["chat_model"] = body["chat_model"]
    if "jnf_url" in body:
        if not str(body["jnf_url"]).startswith("https://"):
            raise HTTPException(400, "JNF URL must start with https://")
        upd["jnf_url"] = body["jnf_url"]
    await db.settings.update_one({"key": "app"}, {"$set": upd})
    await log_activity(admin["user_id"], "settings", "app", "updated", {k: old.get(k) for k in upd}, upd)
    return await get_settings()


@api.get("/admin/ai-models")
async def ai_models(admin=Depends(get_admin)):
    return {"current": (await get_settings()).get("chat_model", "claude"),
            "models": [{"key": k, "provider": v[0], "model": v[1], "label": v[2]} for k, v in AI_MODELS.items()]}


@api.get("/admin/activity")
async def activity(admin=Depends(get_admin)):
    return await db.activity_logs.find({}, NO_ID).sort("timestamp", -1).to_list(500)


# ---------------- Knowledge base ----------------
KB_FIELDS = ["title", "category", "content", "source_url", "academic_year", "validity_period", "last_verified_at",
             "published", "is_resource"]


@api.get("/admin/kb")
async def kb_list(admin=Depends(get_admin)):
    return await db.knowledge_base.find({}, NO_ID).sort("updated_at", -1).to_list(500)


@api.post("/admin/kb")
async def kb_create(body: dict, admin=Depends(get_admin)):
    if not body.get("title") or not body.get("category"):
        raise HTTPException(400, "Title and category required")
    doc = {k: body.get(k) for k in KB_FIELDS}
    doc.update({"id": nid(), "published": bool(body.get("published")), "is_resource": bool(body.get("is_resource")),
                "created_at": now(), "updated_at": now()})
    await db.knowledge_base.insert_one(dict(doc))
    await log_activity(admin["user_id"], "knowledge_base", doc["id"], "created", None, doc["title"])
    doc.pop("_id", None)
    return doc


@api.patch("/admin/kb/{kid}")
async def kb_update(kid: str, body: dict, admin=Depends(get_admin)):
    upd = {k: v for k, v in body.items() if k in KB_FIELDS}
    old = await db.knowledge_base.find_one_and_update({"id": kid}, {"$set": {**upd, "updated_at": now()}})
    if not old:
        raise HTTPException(404)
    await log_activity(admin["user_id"], "knowledge_base", kid, "updated", None, ",".join(upd.keys()))
    return await db.knowledge_base.find_one({"id": kid}, NO_ID)


@api.delete("/admin/kb/{kid}")
async def kb_delete(kid: str, admin=Depends(get_admin)):
    old = await db.knowledge_base.find_one_and_delete({"id": kid})
    if not old:
        raise HTTPException(404)
    await log_activity(admin["user_id"], "knowledge_base", kid, "deleted", old["title"])
    return {"ok": True}


# ---------------- Public ----------------
@api.get("/public/kb")
async def public_kb():
    return await db.knowledge_base.find({"published": True}, {"_id": 0, "id": 1, "title": 1, "category": 1, "content": 1,
                                                              "source_url": 1, "is_resource": 1, "last_verified_at": 1, "file_id": 1, "file_name": 1}).to_list(500)


@api.get("/public/config")
async def public_config():
    return {"jnf_url": (await get_settings()).get("jnf_url", JNF_URL), "visit_purposes": VISIT_PURPOSES,
            "call_modes": CALL_MODES, "durations": DURATIONS}


async def availability(d):
    validate_slot(d, "00:00", "00:01")
    busy = [{"start": s, "end": e} for s, e, _ in await busy_internal(d)]
    google = "not_connected"
    try:
        for bs, be in await google_busy(d):
            busy.append({"start": bs.astimezone(IST).strftime("%H:%M"), "end": be.astimezone(IST).strftime("%H:%M")})
        google = "checked"
    except GoogleNotReady:
        pass
    except Exception:
        google = "error"
    return {"date": d, "busy": sorted(busy, key=lambda x: x["start"]), "google_calendar": google}


@api.get("/public/availability")
async def public_availability(date: str):
    return await availability(date)


@api.post("/public/visits")
async def public_visit(body: dict):
    doc = await create_request("visits", body)
    return {"id": doc["id"], "status": doc["status"], "message": visit_msg(doc["id"])}


@api.post("/public/calls")
async def public_call(body: dict):
    doc = await create_request("calls", body)
    return {"id": doc["id"], "status": doc["status"],
            "message": f"Your call request has been submitted. Your request ID is {doc['id']}. It is pending review by the MANIT Training & Placement Cell; you will receive a confirmation once it is approved."}


def visit_msg(rid):
    return (f"Your campus visit request has been submitted successfully. Your request ID is {rid}. The request is currently "
            "pending review by the MANIT Training & Placement Cell. An official confirmation will be shared once the visit is approved.")


async def lookup_status(rid, email):
    rid, email = (rid or "").strip().upper(), (email or "").strip().lower()
    coll = "visit_requests" if rid.startswith("VR-") else "call_requests"
    ent = await db[coll].find_one({"id": rid, "work_email": email}, NO_ID)
    if not ent:
        return None
    is_visit = coll == "visit_requests"
    s, e = slot_of(ent, is_visit)
    return {"id": ent["id"], "type": "Campus Visit" if is_visit else "Call with Head of T&P", "company_name": ent["company_name"],
            "status": ent["status"], "approved_date": ent.get("approved_date"), "start": s, "end": e,
            "proposed_date": ent.get("proposed_date"), "proposed_start_time": ent.get("proposed_start_time"),
            "proposed_end_time": ent.get("proposed_end_time")}


@api.get("/public/status")
async def public_status(request_id: str, email: str):
    r = await lookup_status(request_id, email)
    if not r:
        raise HTTPException(404, "No request found for this ID and email")
    return r


# ---------------- MANIT Connect chatbot ----------------
FALLBACK = ("I don't have verified information about that at the moment. Please contact the MANIT Training & Placement "
            "Cell at tpwnitb@gmail.com for clarification.")


async def system_prompt():
    kb = await db.knowledge_base.find({"published": True}, NO_ID).to_list(200)
    kb_text = "\n\n".join(f"### {k['title']} [{k['category']}]\n{k.get('content') or ''}\nSource: {k.get('source_url') or '-'}" for k in kb)[:20000]
    cfg = await public_config()
    return f"""You are MANIT Connect, the official AI assistant of the Training & Placement Cell, Maulana Azad National Institute of Technology (MANIT) Bhopal. You talk to company HR representatives.
Today's date (IST): {today_ist()}. Timezone: Asia/Kolkata.

STYLE: Professional, friendly Indian English. 1–3 short sentences. Ask only one follow-up question at a time.

KNOWLEDGE: Answer institutional questions ONLY from the VERIFIED KNOWLEDGE below. If the answer is not there, reply exactly: "{FALLBACK}"
Never invent placement statistics, CTC figures, programs, eligibility or dates. Never promise outcomes or student availability. Never confirm a campus visit or call yourself — only the T&P Cell approves. Never reveal other companies' data, admin notes or student data. Never claim an email was sent or a calendar event was created — the system reports results itself after your message.
Key links: JNF {cfg['jnf_url']} ; Placement brochure https://www.manit.ac.in/sites/default/files/documents/Placement_Brochure_MANIT.pdf ; Head of T&P: Dr. Aruna Saxena, Professor & Head, tpwnitb@gmail.com, +91 78982 16935, office 0755-2670802.

RECRUITMENT INTEREST: General questions are NOT interest. Only when the HR explicitly says they want to hire/recruit/conduct a drive/participate in placements/internship recruitment or asks for the invitation & JNF, collect (one at a time): company name, HR name, official work email (designation and contact number optional). If interest is ambiguous ask: "Would your organization be interested in participating in the MANIT Bhopal campus recruitment process for the 2026–27 session?"

ACTIONS: When (and only when) all required details for an action are collected and confirmed, append ONE action block at the very end of your reply, exactly in this form:
<action>{{"type": "...", ...}}</action>
Types and required fields:
- register_interest: company_name, hr_name, work_email, (designation, contact_number optional)
- visit_request: company_name, hr_name, designation, work_email, contact_number, visit_purpose (one of {cfg['visit_purposes']}), requested_date (YYYY-MM-DD), requested_start_time (HH:MM 24h), requested_end_time (HH:MM), remarks
- call_request: company_name, hr_name, designation, work_email, contact_number, preferred_date (YYYY-MM-DD), preferred_time (HH:MM), duration (15/30/45/60), discussion_purpose, call_mode (Phone/Google Meet/Other), remarks
- check_availability: date (YYYY-MM-DD)
- check_status: request_id, work_email
Do not output an action block otherwise. Do not describe the action's result; say something like "Let me process that for you."

VERIFIED KNOWLEDGE:
{kb_text or '(none published)'}"""


async def run_action(act, sid):
    t = act.get("type")
    try:
        if t == "register_interest":
            if not act.get("company_name") or not act.get("hr_name") or not EMAIL_RE.match(act.get("work_email") or ""):
                return "I need your company name, your name and a valid official work email to proceed."
            msgs = [m["content"] for m in await db.chat_messages.find({"session_id": sid, "role": "user"}, NO_ID).sort("ts", 1).to_list(50)]
            label, conf = await jev.classify_interest(msgs)
            if not (label == "explicit_interest" and conf >= 0.6):
                lead, _ = await find_or_create_lead(act)
                if label is None:
                    return "Thank you, your details are recorded. Our Training & Placement Cell will review your interest and share the recruitment invitation shortly."
                return ("Thank you, your details are noted. Would your organization be interested in participating in the "
                        "MANIT Bhopal campus recruitment process for the 2026–27 session?")
            lead, prev = await find_or_create_lead(act, status="Hot")
            if prev and prev != "Hot":
                await set_status(lead, "Hot", "system:manit-connect")
            elif prev is None:
                await log_activity("system:manit-connect", "company_lead", lead["id"], "status_change", None, "Hot")
            inv = await send_invitation(lead["id"])
            if inv["ok"]:
                return f"Thank you! Your interest has been recorded and the official recruitment invitation with the JNF link has been sent to {lead['work_email']}."
            if inv.get("skipped"):
                return "Thank you! Your interest is recorded. Our records show the recruitment invitation was already sent to your organization earlier, so no duplicate was sent."
            return ("Thank you! Your interest has been recorded with the Training & Placement Cell. However, the invitation email "
                    "could not be sent automatically right now; our team will share it shortly. Meanwhile, you can access the JNF here: "
                    + (await get_settings()).get("jnf_url", JNF_URL))
        if t == "visit_request":
            doc = await create_request("visits", act)
            return visit_msg(doc["id"])
        if t == "call_request":
            act["duration"] = int(act.get("duration") or 30)
            doc = await create_request("calls", act)
            return f"Your call request has been submitted. Your request ID is {doc['id']}. It is pending review by the MANIT Training & Placement Cell; you will receive a confirmation once it is approved."
        if t == "check_availability":
            a = await availability(act.get("date"))
            busy = ", ".join(f"{b['start']}–{b['end']}" for b in a["busy"]) or "no confirmed bookings"
            note = "" if a["google_calendar"] == "checked" else " (Google Calendar is not connected, so only internal bookings were checked)"
            return f"On {pretty_date(a['date'])}, already-booked slots: {busy}{note}. Availability is indicative; all requests need approval."
        if t == "check_status":
            r = await lookup_status(act.get("request_id"), act.get("work_email"))
            if not r:
                return "I couldn't find a request matching that ID and email."
            when = f" — scheduled {pretty_date(r['approved_date'])}, {r['start']}–{r['end']} IST" if r.get("approved_date") and r["status"] in ACTIVE else ""
            return f"Request {r['id']} ({r['type']}) status: {r['status']}{when}."
    except HTTPException as e:
        return f"I couldn't submit that: {e.detail}. Could you please correct it?"
    return None


class ChatIn(BaseModel):
    session_id: str
    message: str


@api.post("/chat")
async def chat(body: ChatIn):
    from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
    sid, msg = body.session_id[:64], body.message.strip()[:2000]
    if not msg:
        raise HTTPException(400, "Message required")
    hist = await db.chat_messages.find({"session_id": sid}, NO_ID).sort("ts", 1).to_list(200)
    await db.chat_messages.insert_one({"session_id": sid, "role": "user", "content": msg, "ts": now()})
    transcript = "\n".join(f"{'HR' if h['role'] == 'user' else 'MANIT Connect'}: {h['content']}" for h in hist[-20:])
    prompt = f"Conversation so far:\n{transcript or '(start)'}\n\nHR: {msg}\n\nReply as MANIT Connect."
    llm = LlmChat(api_key=LLM_KEY, session_id=f"{sid}-{nid()}", system_message=await system_prompt()).with_model(*AI_MODELS.get((await get_settings()).get("chat_model"), AI_MODELS["claude"])[:2])

    async def gen():
        full = ""
        try:
            async for ev in llm.stream_message(UserMessage(text=prompt)):
                if isinstance(ev, TextDelta):
                    full += ev.content
                    yield f"data: {json.dumps({'delta': ev.content})}\n\n"
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.error("chat error: %s", e)
            yield f"data: {json.dumps({'error': 'MANIT Connect is temporarily unavailable. Please try again or email tpwnitb@gmail.com.'})}\n\n"
            return
        visible = full.split("<action")[0].strip()
        m = re.search(r"<action>(.*?)</action>", full, re.S)
        note = None
        if m:
            try:
                note = await run_action(json.loads(m.group(1)), sid)
            except json.JSONDecodeError:
                note = None
        await db.chat_messages.insert_one({"session_id": sid, "role": "assistant", "content": visible, "ts": now()})
        if note:
            await db.chat_messages.insert_one({"session_id": sid, "role": "assistant", "content": f"[System] {note}", "ts": now()})
            yield f"data: {json.dumps({'note': note})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@api.get("/")
async def root():
    return {"message": "MANIT T&P API"}


@app.on_event("startup")
async def startup():
    await db.company_leads.create_index("id", unique=True)
    await db.visit_requests.create_index("id", unique=True)
    await db.call_requests.create_index("id", unique=True)
    await db.settings.update_one({"key": "app"}, {"$setOnInsert": {"key": "app", "jnf_url": JNF_URL}}, upsert=True)
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    admin = await db.users.find_one({"email": ADMIN_EMAIL})
    if not admin:
        await db.users.insert_one({"user_id": f"user_{uuid.uuid4().hex[:12]}", "email": ADMIN_EMAIL, "name": "Admin",
                                   "password_hash": hash_pw(os.environ["ADMIN_PASSWORD"]), "created_at": now()})
    elif not admin.get("password_hash"):
        await db.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"password_hash": hash_pw(os.environ["ADMIN_PASSWORD"])}})
    try:
        await asyncio.to_thread(init_storage)
    except Exception as e:
        logger.error("Storage init failed: %s", e)
    for key, t in TEMPLATES.items():
        await db.email_templates.update_one({"key": key}, {"$setOnInsert": {"key": key, **t, "updated_at": now()}}, upsert=True)
    if await db.knowledge_base.count_documents({}) == 0:
        for k in KB_SEED:
            await db.knowledge_base.insert_one({"id": nid(), "category": k["category"], "title": k["title"], "content": k["content"],
                                                "source_url": k.get("source_url"), "academic_year": k.get("academic_year"),
                                                "validity_period": None, "last_verified_at": None, "published": k.get("published", True),
                                                "is_resource": k.get("is_resource", False), "created_at": now(), "updated_at": now()})


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True,
                   allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])


@app.on_event("shutdown")
async def shutdown():
    client.close()
