import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { api } from "../../lib/api";
import { AlertTriangle } from "lucide-react";
import { PageHead } from "../../components/admin/AdminLayout";

const CARDS = [
  ["total", "Total Companies", "/admin/leads"], ["hot", "Hot Leads", "/admin/leads", "text-red-600"], ["warm", "Warm Leads", "/admin/leads", "text-amber-600"],
  ["cold", "Cold Leads", "/admin/leads", "text-slate-500"], ["invitations_sent", "Invitations Sent", "/admin/emails"], ["jnf_awaited", "JNFs Awaited", "/admin/jnf"],
  ["jnf_received", "JNFs Received", "/admin/jnf"], ["pending_visits", "Pending Visit Requests", "/admin/visits"], ["upcoming_visits", "Approved Upcoming Visits", "/admin/visits"],
  ["pending_calls", "Pending Call Requests", "/admin/calls"], ["scheduled_calls", "Scheduled Calls", "/admin/calls"],
];

export default function Dashboard() {
  const { user } = useOutletContext();
  const [s, setS] = useState(null);
  const [g, setG] = useState(null);
  const [urgent, setUrgent] = useState(null);
  const loadUrgent = () => api.get("/admin/urgent").then((r) => setUrgent(r.data));
  const ack = async (u) => { await api.post(`/admin/req/${u.kind}/${u.id}/action`, { action: "ack_urgent" }); loadUrgent(); };
  useEffect(() => {
    loadUrgent();
    const t = setInterval(loadUrgent, 60000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    api.get("/admin/stats").then((r) => setS(r.data));
    api.get("/admin/google/status").then((r) => setG(r.data));
  }, []);
  return (
    <div>
      <PageHead title="Dashboard" desc={`Welcome, ${user?.name || user?.email}`} />
      {urgent?.urgent.length > 0 && (
        <div className="mb-6 rounded-lg border border-red-300 bg-red-50 p-4" data-testid="urgent-banner">
          <p className="flex items-center gap-2 font-semibold text-red-800"><AlertTriangle className="h-5 w-5" />{urgent.urgent.length} critical request{urgent.urgent.length > 1 ? "s need" : " needs"} attention</p>
          <div className="mt-3 space-y-2">
            {urgent.urgent.map((u) => (
              <div key={u.id} className="flex flex-wrap items-center gap-3 rounded-md bg-white p-2 text-sm" data-testid={`urgent-item-${u.id}`}>
                <span className="font-mono text-xs">{u.id}</span><span className="font-medium">{u.company_name}</span>
                <span className="text-xs text-[#64748B]">{u.kind === "visits" ? "Campus visit" : "Call"} · {u.purpose || "—"} · requested for {u.date}</span>
                <Link to={`/admin/${u.kind}`} className="ml-auto text-xs font-semibold text-[#1D4ED8] hover:underline" data-testid={`urgent-open-${u.id}`}>Review</Link>
                <button onClick={() => ack(u)} className="text-xs text-[#64748B] hover:text-[#0B2545]" data-testid={`urgent-dismiss-${u.id}`}>Dismiss</button>
              </div>
            ))}
          </div>
        </div>
      )}
      {urgent?.junk_pending > 0 && <p className="mb-6 text-sm text-[#64748B]" data-testid="junk-pending-note">{urgent.junk_pending} possible junk request(s) are hidden from the queues — open Visit Requests or Call Scheduling → Junk review.</p>}
      <div className="mb-8 grid gap-4 lg:grid-cols-3">
        <div className="card flex items-center gap-4 p-5 lg:col-span-2">
          <img src="/img/aruna.png" alt="Dr. Aruna Saxena" className="h-20 w-20 rounded-full border-2 border-[#DBEAFE] object-cover object-top" />
          <div><p className="font-serif-d text-xl text-[#0B2545]">Dr. Aruna Saxena</p><p className="text-sm text-[#64748B]">Professor & Head · Training & Placement Cell · MANIT Bhopal</p></div>
        </div>
        <Link to="/admin/settings" className={`card p-5 ${g?.connected ? "" : "border-amber-300 bg-amber-50"}`} data-testid="google-status-card">
          <p className="lbl">Google (Gmail & Calendar)</p>
          <p className="mt-1 font-semibold text-[#0B2545]">{g ? (g.connected ? `Connected: ${g.account}` : "Not connected — emails cannot be sent") : "…"}</p>
          <p className="mt-1 text-xs text-[#64748B]">Gmail: {g?.gmail ? "ready" : "not authorised"} · Calendar: {g?.calendar ? "ready" : "not authorised"}</p>
        </Link>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
        {CARDS.map(([k, label, to, color]) => (
          <Link key={k} to={to} className="card p-5 transition-colors hover:border-[#2563EB]" data-testid={`stat-${k}`}>
            <p className="text-xs font-semibold uppercase tracking-wide text-[#64748B]">{label}</p>
            <p className={`font-serif-d mt-2 text-4xl ${color || "text-[#123B70]"}`}>{s ? s[k] : "–"}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
