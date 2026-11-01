import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { CheckCircle2, XCircle } from "lucide-react";
import { api, errMsg, fmt } from "../../lib/api";
import { PageHead } from "../../components/admin/AdminLayout";

const MSG = { connected: "Google account connected", wrong_account: "Rejected: only tpwnitb@gmail.com can be connected", denied: "Authorisation was cancelled", invalid_state: "OAuth state invalid or expired — try again", token_error: "Google token exchange failed" };

const Row = ({ ok, label }) => <p className="flex items-center gap-2 text-sm">{ok ? <CheckCircle2 className="h-4 w-4 text-green-600" /> : <XCircle className="h-4 w-4 text-red-500" />}{label}</p>;

export default function Settings() {
  const [s, setS] = useState(null);
  const [params, setParams] = useSearchParams();
  const load = () => api.get("/admin/google/status").then((r) => setS(r.data));
  useEffect(() => {
    load();
    const g = params.get("google");
    if (g) { (g === "connected" ? toast.success : toast.error)(MSG[g] || g); setParams({}); }
  }, []); // eslint-disable-line
  const connect = async () => { try { window.location.href = (await api.get("/admin/google/connect")).data.url; } catch (e) { toast.error(errMsg(e)); } };
  const disconnect = async () => { if (!window.confirm("Disconnect Google? Emails and calendar sync will stop.")) return; await api.post("/admin/google/disconnect"); toast.success("Disconnected"); load(); };
  const check = async () => { try { await api.post("/admin/google/check"); toast.success("Connection OK"); } catch (e) { toast.error(errMsg(e)); } load(); };
  if (!s) return null;
  return (
    <div>
      <PageHead title="Settings" desc="Gmail & Google Calendar integration for the official account." />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card space-y-3 p-6" data-testid="google-integration-card">
          <p className="font-serif-d text-xl text-[#0B2545]">Google Integration</p>
          <Row ok={s.configured} label={`OAuth client credentials ${s.configured ? "configured" : "missing on server"}`} />
          <Row ok={s.connected} label={s.connected ? `Connected account: ${s.account}` : "Google account not connected"} />
          <Row ok={s.gmail} label="Gmail send permission" />
          <Row ok={s.calendar} label="Calendar free/busy & events permission" />
          <p className="text-xs text-[#64748B]">Connected: {fmt(s.connected_at)} · Last check: {fmt(s.last_check_at)}</p>
          {s.last_error && <p className="rounded-md bg-red-50 p-2 text-xs text-red-700" data-testid="google-error">{s.last_error}</p>}
          <div className="flex flex-wrap gap-2 pt-2">
            <button className="btn-primary" onClick={connect} disabled={!s.configured} data-testid="google-connect-btn">{s.connected ? "Reconnect" : "Connect Google Account"}</button>
            {s.connected && <button className="btn-outline" onClick={check} data-testid="google-check-btn">Check connection</button>}
            {s.connected && <button className="btn-outline text-red-600" onClick={disconnect} data-testid="google-disconnect-btn">Disconnect</button>}
          </div>
          <p className="text-xs text-[#64748B]">Sign in as <b>{s.official_email}</b>. Any other account is rejected and never used.</p>
        </div>
        <div className="card space-y-3 p-6 text-sm" data-testid="google-setup-card">
          <p className="font-serif-d text-xl text-[#0B2545]">Google Cloud setup</p>
          <ol className="list-decimal space-y-1.5 pl-5">
            <li>In Google Cloud Console create a project and enable <b>Gmail API</b> and <b>Google Calendar API</b>.</li>
            <li>OAuth consent screen: External, app name "MANIT T&P Portal", support email tpwnitb@gmail.com, add the scopes below, and add tpwnitb@gmail.com as a test user (or publish the app).</li>
            <li>Credentials → Create OAuth client ID → Web application. Add the redirect URI below exactly.</li>
            <li>Provide the client ID and secret as server secrets, then click Connect Google Account.</li>
          </ol>
          <p className="lbl mt-3">Authorized redirect URI</p>
          <code className="block break-all rounded bg-[#EFF6FF] p-2 text-xs" data-testid="redirect-uri">{s.redirect_uri || "GOOGLE_REDIRECT_URI not set"}</code>
          <p className="lbl">Server environment variables</p>
          <code className="block rounded bg-[#EFF6FF] p-2 text-xs">{s.env_vars.join(", ")}</code>
          <p className="lbl">Scopes</p>
          <code className="block whitespace-pre-wrap break-all rounded bg-[#EFF6FF] p-2 text-xs">{s.scopes.join("\n")}</code>
        </div>
      </div>
    </div>
  );
}
