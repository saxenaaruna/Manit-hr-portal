import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { PageHead } from "../../components/admin/AdminLayout";
import Modal from "../../components/Modal";
import { ActionDialog } from "./Requests";
import ScheduleCallDialog from "./ScheduleCallDialog";
import LeadDetail from "./LeadDetail";

const pad = (n) => String(n).padStart(2, "0");

export default function CalendarView() {
  const now = new Date();
  const [ym, setYm] = useState([now.getFullYear(), now.getMonth()]);
  const [items, setItems] = useState([]);
  const [sel, setSel] = useState(null); const [act, setAct] = useState(null); const [manual, setManual] = useState(null); const [lead, setLead] = useState(null);
  const month = `${ym[0]}-${pad(ym[1] + 1)}`;
  const load = useCallback(() => api.get("/admin/calendar", { params: { month } }).then((r) => setItems(r.data)), [month]);
  useEffect(() => { load(); }, [load]);
  const shift = (d) => setYm(([y, m]) => { const t = new Date(y, m + d, 1); return [t.getFullYear(), t.getMonth()]; });
  const first = new Date(ym[0], ym[1], 1).getDay();
  const days = new Date(ym[0], ym[1] + 1, 0).getDate();
  const cells = [...Array(first).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)];

  const openAction = async (it, action) => {
    const kind = it.kind === "visit" ? "visits" : "calls";
    const r = (await api.get(`/admin/req/${kind}`)).data.find((x) => x.id === it.id);
    if (action === "cancel") {
      if (!window.confirm(`Cancel ${it.id}?`)) return;
      try { await api.post(`/admin/req/${kind}/${it.id}/action`, { action: "cancel" }); toast.success("Cancelled"); setSel(null); load(); } catch (e) { toast.error(errMsg(e)); }
      return;
    }
    setAct({ kind, r, action }); setSel(null);
  };

  return (
    <div>
      <PageHead title="Recruitment Calendar" desc="Internal calendar (IST). Solid = confirmed, dashed = pending request (not confirmed). Google sync status is shown per event.">
        <button className="btn-outline" onClick={() => setManual("visits")} data-testid="cal-new-visit-btn">New campus visit</button>
        <button className="btn-primary" onClick={() => setManual("calls")} data-testid="cal-new-call-btn">New call</button>
      </PageHead>
      <div className="mb-3 flex items-center gap-3">
        <button className="btn-outline px-2" onClick={() => shift(-1)} data-testid="cal-prev"><ChevronLeft className="h-4 w-4" /></button>
        <p className="font-serif-d w-48 text-center text-xl text-[#0B2545]" data-testid="cal-month">{new Date(ym[0], ym[1]).toLocaleString("en-IN", { month: "long", year: "numeric" })}</p>
        <button className="btn-outline px-2" onClick={() => shift(1)} data-testid="cal-next"><ChevronRight className="h-4 w-4" /></button>
        <div className="ml-auto flex gap-4 text-xs"><span className="flex items-center gap-1"><i className="h-3 w-3 rounded-sm bg-[#1D4ED8]" />Campus visit</span><span className="flex items-center gap-1"><i className="h-3 w-3 rounded-sm bg-[#0EA5E9]" />Call</span><span className="flex items-center gap-1"><i className="h-3 w-3 rounded-sm border border-dashed border-[#64748B]" />Pending</span></div>
      </div>
      <div className="grid grid-cols-7 overflow-hidden rounded-lg border border-[#D6E4F7] bg-white" data-testid="calendar-grid">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => <div key={d} className="bg-[#DBEAFE] p-2 text-xs font-semibold text-[#123B70]">{d}</div>)}
        {cells.map((d, i) => {
          const date = d && `${month}-${pad(d)}`;
          const list = d ? items.filter((x) => x.date === date).sort((a, b) => a.start.localeCompare(b.start)) : [];
          return (
            <div key={i} className="min-h-[110px] border-t border-l border-[#EEF3FB] p-1.5">
              {d && <p className="mb-1 text-xs text-[#64748B]">{d}</p>}
              {list.map((it) => {
                const base = it.kind === "visit" ? "#1D4ED8" : "#0EA5E9";
                const cancelled = it.status === "Cancelled";
                return (
                  <button key={it.id} onClick={() => setSel(it)} data-testid={`cal-event-${it.id}`}
                    className={`mb-1 block w-full truncate rounded px-1.5 py-0.5 text-left text-[11px] ${cancelled ? "line-through opacity-50" : ""}`}
                    style={it.confirmed ? { background: base, color: "#fff" } : { border: `1px dashed ${base}`, color: base, background: "#fff" }}>
                    {it.start} {it.company}{!it.confirmed && !cancelled ? " (pending)" : ""}
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>
      {sel && (
        <Modal open onClose={() => setSel(null)} title={`${sel.kind === "visit" ? "Campus visit" : "Call"} — ${sel.id}`} testid="cal-event-modal">
          <div className="space-y-1 text-sm">
            <p><b>{sel.company}</b> · {sel.title}</p>
            <p>{sel.date} · {sel.start}–{sel.end} IST</p>
            <p>Status: <b>{sel.status}</b> {sel.confirmed ? "(confirmed)" : "(not confirmed)"}</p>
            <p className="text-xs text-[#64748B]">Internal record · Google Calendar: {sel.sync || "Not Synced"}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {["Approved", "Rescheduled"].includes(sel.status) && <button className="btn-primary" onClick={() => openAction(sel, "reschedule")} data-testid="cal-reschedule-btn">Change date / time</button>}
            {["Pending Approval", "Pending", "Alternative Proposed"].includes(sel.status) && <button className="btn-primary" onClick={() => openAction(sel, "approve")} data-testid="cal-approve-btn">Review & approve</button>}
            {!["Cancelled", "Completed", "Rejected"].includes(sel.status) && <button className="btn-outline text-red-600" onClick={() => openAction(sel, "cancel")} data-testid="cal-cancel-btn">Cancel</button>}
            {sel.lead_id && <button className="btn-outline" onClick={() => { setLead(sel.lead_id); setSel(null); }} data-testid="cal-company-btn">Company details</button>}
          </div>
        </Modal>
      )}
      {act && <ActionDialog {...act} onClose={() => setAct(null)} onDone={(d) => { toast.success(`${d.item.id}: ${d.item.status}`); if (d.calendar) toast.info(`Google Calendar: ${d.calendar}`); if (d.email) (d.email.ok ? toast.success : toast.error)(d.email.message); setAct(null); load(); }} />}
      {manual && <ScheduleCallDialog kind={manual} onClose={() => setManual(null)} onDone={load} />}
      {lead && <LeadDetail id={lead} onClose={() => setLead(null)} onChanged={load} />}
    </div>
  );
}
