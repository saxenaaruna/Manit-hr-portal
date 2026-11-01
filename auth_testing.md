# Auth testing (Emergent Google Auth)
Create test session:
mongosh --eval "use('test_database'); var u=db.users.findOne({email:'saxena.aroona@gmail.com'}); db.user_sessions.insertOne({user_id:u.user_id,session_token:'test_session_'+Date.now(),expires_at:new Date(Date.now()+7*864e5),created_at:new Date()})"
Backend: curl -H "Authorization: Bearer <token>" $API/api/auth/me
Browser: add cookie session_token=<token> (httpOnly, secure, sameSite None, path /) for the preview domain, then open /admin.
