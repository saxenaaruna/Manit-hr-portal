# MANIT Bhopal — T&P HR Portal, Company CRM & Recruitment Scheduling

## Original problem
Full spec supplied by user (consolidated master build prompt): public HR portal, MANIT Connect AI chatbot, editable Company Leads Spreadsheet (Hot/Warm/Cold), automatic invitation+JNF email on Hot, campus visit & call approval workflows, recruitment calendar, Gmail + Google Calendar OAuth for tpwnitb@gmail.com, knowledge base, templates, activity log, blue institutional theme, supplied photos, LinkedIn links.

## Choices
- Admin login: Emergent-managed Google Sign-In, allowlist env ADMIN_EMAILS (saxena.aroona@gmail.com)
- LLM: Claude Sonnet 5.5 (claude-sonnet-5-5) via Emergent LLM key
- DB: MongoDB (platform default)

## Architecture
- backend/server.py (FastAPI, all /api routes), backend/seed.py (templates + KB seed)
- Gmail/Calendar: direct REST via httpx, server-side OAuth (/api/admin/google/connect -> /api/oauth/google/callback), tokens in `integrations` collection, account must equal OFFICIAL_GOOGLE_EMAIL
- Chat: SSE stream; LLM emits <action>{json}</action>; backend runs predefined functions only (register_interest, visit_request, call_request, check_availability, check_status)
- Idempotent invitation: atomic find_one_and_update guard on invitation_success_at + Queued lock
- Conflict check: asyncio lock + internal approved visits/calls + Google freebusy (if connected)

## Implemented (2026-06)
- Public portal, forms, status lookup, chatbot, LinkedIn, resources
- Admin: dashboard stats, leads spreadsheet (inline edit/search/filter/sort/delete/detail/resend/schedule call), emails (retry/manual), JNF tracking (+URL edit, reminder), visits & calls (approve/reject/propose/reschedule/cancel/complete/notes), calendar (month grid, manual events), KB & resources, templates, activity, Google settings
- Tested: backend 8/8, frontend pass (chat crash fixed)
- Iteration 2: email+password admin login (bcrypt, lockout, change password) alongside Google; chatbot model switch Claude/GPT-5.6 Terra/Gemini 3.1 Pro; KB/resource file uploads (Emergent object storage); Jev: chat interest gating (fail-closed), AI Hot/Warm/Cold suggestion, junk flag + urgency on requests. Tested 12/12 backend + frontend.
- Not built (conflict with spec / defaults): Stripe, Resend/SendGrid (all mail must come from tpwnitb@gmail.com; managed Resend can't send outreach with manit.ac.in links), Twilio SMS, ElevenLabs/TTS/STT, Perplexity, image/video generation

## Pending configuration
- Iteration 3: placement brochure PDF attached (downloaded from manit.ac.in); JNF Google Doc is private (401) so not attached — admin must upload; junk auto-hide (Junk review tab, Genuine/Junk actions); dashboard critical-urgency banner with dismiss; GOOGLE_REDIRECT_URI updated to manit-hr-portal--93wuv0i1 preview domain
- GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET (redirect URI env already set for preview; update GOOGLE_REDIRECT_URI for production domain)
- Internship KB entry is unpublished pending verification

## Backlog
- P1: verify brochure content & import into KB manually
- P2: chat history viewer for admin, follow-up reminders on next_followup_at
