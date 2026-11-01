import { useState } from "react";
import { useLocation, Link, useNavigate } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import { ShieldCheck, ArrowLeft } from "lucide-react";

export default function AdminLogin() {
  const location = useLocation();
  const navigate = useNavigate();
  const [error, setError] = useState(location.state?.error);
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError(null);
    try { const r = await api.post("/auth/login", { email, password }); navigate("/admin", { replace: true, state: { user: r.data } }); }
    catch (err) { setError(errMsg(err)); } finally { setBusy(false); }
  };
  const login = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/admin";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };
  return (
    <div className="grid min-h-screen md:grid-cols-2">
      <div className="relative hidden md:block">
        <img src="/img/building.jpg" alt="MANIT Bhopal main building" className="h-full w-full object-cover" />
        <div className="absolute inset-0 bg-[#0B2545]/70" />
        <div className="absolute bottom-10 left-10 right-10 text-white">
          <img src="/img/logo.png" alt="MANIT logo" className="mb-6 h-14 w-auto" />
          <p className="font-serif-d text-3xl">Training & Placement Cell</p>
          <p className="mt-2 text-sm text-blue-100">Administration console for company engagement and campus recruitment.</p>
        </div>
      </div>
      <div className="flex items-center justify-center bg-[#EFF6FF] p-8">
        <div className="card w-full max-w-sm p-8 fade-up" data-testid="admin-login-card">
          <ShieldCheck className="mb-4 h-10 w-10 text-[#1D4ED8]" />
          <h1 className="font-serif-d text-2xl text-[#0B2545]">Admin Login</h1>
          <p className="mt-2 text-sm text-[#64748B]">Access is restricted to authorised MANIT T&P administrators. No public sign-up.</p>
          {error && <p className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700" data-testid="login-error">{error}</p>}
          <form onSubmit={submit} className="mt-6 space-y-3" data-testid="password-login-form">
            <input type="email" required placeholder="Email" className="field" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email" />
            <input type="password" required placeholder="Password" className="field" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password" />
            <button className="btn-primary w-full justify-center py-3" disabled={busy} data-testid="login-submit-btn">{busy ? "Signing in…" : "Sign in"}</button>
          </form>
          <div className="my-4 flex items-center gap-3 text-xs text-[#64748B]"><span className="h-px flex-1 bg-[#D6E4F7]" />or<span className="h-px flex-1 bg-[#D6E4F7]" /></div>
          <button onClick={login} className="btn-outline w-full justify-center py-3" data-testid="google-login-btn">Continue with Google</button>
          <Link to="/" className="mt-6 inline-flex items-center gap-1 text-sm text-[#1D4ED8] hover:underline" data-testid="back-to-portal-link"><ArrowLeft className="h-4 w-4" />Back to portal</Link>
        </div>
      </div>
    </div>
  );
}
