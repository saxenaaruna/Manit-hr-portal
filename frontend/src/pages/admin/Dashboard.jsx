import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import { api } from "../../lib/api";
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
  useEffect(() => {
    api.get("/admin/stats").then((r) => setS(r.data));
    api.get("/admin/google/status").then((r) => setG(r.data));
  }, []);
  return (
    <div>
      <PageHead title="Dashboard" desc={`Welcome, ${user?.name || user?.email}`} />
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
