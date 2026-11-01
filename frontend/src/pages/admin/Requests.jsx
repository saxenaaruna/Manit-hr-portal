import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errMsg, fmt } from "../../lib/api";
import { PageHead } from "../../components/admin/AdminLayout";
import Modal, { Field } from "../../components/Modal";
import ScheduleCallDialog, { reportSchedule } from "./ScheduleCallDialog";

const CFG = {
  visits: { title: "Visit Requests", statuses: ["Pending Approval", "Approved", "Rejected", "Alternative Proposed", "Rescheduled", "Cancelled", "Completed"] },
  calls: { title: "Call Scheduling", statuses: ["Pending", "Approved", "Rejected", "Rescheduled", "Cancelled", "Completed"] },
};
const PENDING = ["Pending Approval", "Pending", "Alternative Proposed"];
const ACTIVE = ["Approved", "Rescheduled"];

const slot = (r, v) => v
  ? (r.approved_date ? `${r.approved_date} ${r.approved_start_time}–${r.approved_end_time}` : null)
  : (r.approved_date ? `${r.approved_date} ${r.approved_time} (${r.approved_duration}m)` : null);
const requested = (r, v) => v ? `${r.requested_date} ${r.requested_start_time}–${r.requested_end_time}` : `${r.preferred_date} ${r.preferred_time} (${r.duration}m)`;

export default function Requests({ kind }) {
  const v = kind === "visits";
  const [rows, setRows] = useState([]); const [status, setStatus] = useState("");
  const [act, setAct] = useState(null); const [manual, setManual] = useState(false);
  const load = useCallback(() => api.get(`/admin/req/${kind}`, { params: { status } }).then((r) => setRows(r.data)), [kind, status]);
  useEffect(() => { load(); }, [load]);
  const quick = async (r, action, extra = {}) => {
    try { const d = (await api.post(`/admin/req/${kind}/${r.id}/action`, { action, ...extra })).data; d.item ? reportResult(d) : null; load(); }
    catch (e) { toast.error(errMsg(e), { duration: 8000 }); }
  };
  const reportResult = (d) => { toast.success(`${d.item.id}: ${d.item.status}`); if (d.calendar) toast.info(`Google Calendar: ${d.calendar}`); if (d.email) (d.email.ok ? toast.success : toast.error)(d.email.message, { duration: 8000 }); };

  return (
    <div>
      <PageHead title={CFG[kind].title} desc={v ? "Approve, reject, propose alternatives, reschedule or cancel campus visits. Confirmation emails are sent only after approval." : "Review call requests with the Head of T&P. Approval creates a calendar event and sends a confirmation."}>
        <button className="btn-primary" onClick={() => setManual(true)} data-testid="manual-create-btn">{v ? "Create visit" : "Schedule call manually"}</button>
      </PageHead>
      <div className="mb-4 flex flex-wrap gap-1">
        {["", ...CFG[kind].statuses].map((s) => <button key={s} onClick={() => setStatus(s)} className={`rounded px-3 py-1.5 text-xs ${status === s ? "bg-[#2563EB] text-white" : "border border-[#C9D8F0] bg-white text-[#123B70]"}`} data-testid={`status-filter-${s || "all"}`}>{s || "All"}</button>)}
      </div>
      <div className="overflow-x-auto rounded-lg border border-[#D6E4F7] bg-white">
        <table className="w-full min-w-[1100px] text-sm" data-testid={`${kind}-table`}>
          <thead className="bg-[#DBEAFE] text-left text-xs uppercase text-[#123B70]"><tr>{["ID", "Company / HR", v ? "Purpose" : "Purpose / Mode", "Requested", "Approved schedule", "Status", "Calendar / Email", "Actions"].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.id} className="border-t border-[#EEF3FB] align-top" data-testid={`${kind}-row-${i}`}>
                <td className="px-3 py-2 font-mono text-xs">{r.id}<div className="font-sans text-[10px] text-[#64748B]">{fmt(r.created_at)}</div></td>
                <td className="px-3 py-2"><p className="font-medium">{r.company_name}</p><p className="text-xs text-[#64748B]">{r.hr_name} · {r.work_email}{r.contact_number ? ` · ${r.contact_number}` : ""}</p>{r.admin_notes && <p className="mt-1 text-xs italic text-[#123B70]">Note: {r.admin_notes}</p>}</td>
                <td className="px-3 py-2 text-xs">{v ? r.visit_purpose : `${r.discussion_purpose || "—"} · ${r.call_mode}`}{r.meeting_link && <a href={r.meeting_link} target="_blank" rel="noreferrer" className="block text-[#1D4ED8]">Meeting link</a>}{r.remarks && <p className="text-[#64748B]">“{r.remarks}”</p>}</td>
                <td className="px-3 py-2 text-xs">{requested(r, v)}{r.proposed_date && <p className="text-amber-700">Proposed: {r.proposed_date} {r.proposed_start_time}–{r.proposed_end_time}</p>}</td>
                <td className="px-3 py-2 text-xs font-medium">{slot(r, v) || "—"}</td>
                <td className="px-3 py-2"><span className={`rounded px-2 py-0.5 text-xs font-semibold ${ACTIVE.includes(r.status) ? "bg-[#DBEAFE] text-[#1D4ED8]" : PENDING.includes(r.status) ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"}`} data-testid={`${kind}-status-${i}`}>{r.status}</span>{r.rejection_reason && <p className="mt-1 text-xs text-[#64748B]">{r.rejection_reason}</p>}</td>
                <td className="px-3 py-2 text-[11px] text-[#64748B]"><p>{r.calendar_sync_status}</p><p>{r.last_email_status || ""}</p></td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1">
                    {PENDING.includes(r.status) && <button className="btn-outline px-2 py-1 text-xs" onClick={() => setAct({ r, action: "approve" })} data-testid={`${kind}-approve-${i}`}>Approve</button>}
                    {PENDING.includes(r.status) && <button className="btn-outline px-2 py-1 text-xs" onClick={() => setAct({ r, action: "reject" })} data-testid={`${kind}-reject-${i}`}>Reject</button>}
                    {v && PENDING.includes(r.status) && <button className="btn-outline px-2 py-1 text-xs" onClick={() => setAct({ r, action: "propose_alternative" })} data-testid={`${kind}-propose-${i}`}>Propose alt.</button>}
                    {ACTIVE.includes(r.status) && <button className="btn-outline px-2 py-1 text-xs" onClick={() => setAct({ r, action: "reschedule" })} data-testid={`${kind}-reschedule-${i}`}>Reschedule</button>}
                    {ACTIVE.includes(r.status) && <button className="btn-outline px-2 py-1 text-xs" onClick={() => quick(r, "send_confirmation")} data-testid={`${kind}-confirm-${i}`}>Send/retry email</button>}
                    {ACTIVE.includes(r.status) && !String(r.calendar_sync_status).startsWith("Synced") && <button className="btn-outline px-2 py-1 text-xs" onClick={() => quick(r, "sync_calendar")}>Retry sync</button>}
                    {ACTIVE.includes(r.status) && <button className="btn-outline px-2 py-1 text-xs" onClick={() => quick(r, "complete")}>Complete</button>}
                    {!["Cancelled", "Completed", "Rejected"].includes(r.status) && <button className="btn-outline px-2 py-1 text-xs text-red-600" onClick={() => window.confirm(`Cancel ${r.id}?`) && quick(r, "cancel")} data-testid={`${kind}-cancel-${i}`}>Cancel</button>}
                    <button className="btn-outline px-2 py-1 text-xs" onClick={() => setAct({ r, action: "notes" })} data-testid={`${kind}-notes-${i}`}>Notes</button>
                  </div>
                </td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={8} className="p-8 text-center text-[#64748B]">No requests.</td></tr>}
          </tbody>
        </table>
      </div>
      {act && <ActionDialog kind={kind} {...act} onClose={() => setAct(null)} onDone={(d) => { reportResult(d); setAct(null); load(); }} />}
      {manual && <ScheduleCallDialog kind={kind} onClose={() => setManual(false)} onDone={load} />}
    </div>
  );
}

export function ActionDialog({ kind, r, action, onClose, onDone }) {
  const v = kind === "visits";
  const [f, setF] = useState({
    date: r.approved_date || r.proposed_date || (v ? r.requested_date : r.preferred_date),
    start_time: (v ? r.approved_start_time || r.proposed_start_time || r.requested_start_time : r.approved_time || r.preferred_time),
    end_time: v ? r.approved_end_time || r.proposed_end_time || r.requested_end_time : "",
    duration: r.approved_duration || r.duration, meeting_link: r.meeting_link || "", reason: "", notes: r.admin_notes || "",
  });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const timeFields = ["approve", "reschedule", "propose_alternative"].includes(action);
  const submit = async () => {
    setBusy(true);
    try { onDone((await api.post(`/admin/req/${kind}/${r.id}/action`, { action, ...f, duration: Number(f.duration) || null })).data); }
    catch (e) { toast.error(errMsg(e), { duration: 8000 }); } finally { setBusy(false); }
  };
  const titles = { approve: "Approve request", reject: "Reject request", reschedule: "Reschedule", propose_alternative: "Propose alternative slot", notes: "Private admin notes" };
  return (
    <Modal open onClose={onClose} title={`${titles[action]} — ${r.id}`} testid="action-dialog">
      <p className="text-sm text-[#64748B]">{r.company_name} · {r.hr_name}</p>
      {timeFields && (
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Date"><input type="date" className="field" value={f.date} onChange={set("date")} data-testid="action-date" /></Field>
          <Field label={v ? "Start" : "Time"}><input type="time" className="field" value={f.start_time} onChange={set("start_time")} data-testid="action-start" /></Field>
          {v ? <Field label="End"><input type="time" className="field" value={f.end_time} onChange={set("end_time")} data-testid="action-end" /></Field>
            : <Field label="Duration"><select className="field" value={f.duration} onChange={set("duration")} data-testid="action-duration">{[15, 30, 45, 60].map((d) => <option key={d} value={d}>{d} min</option>)}</select></Field>}
          {!v && <div className="sm:col-span-3"><Field label="Meeting link"><input className="field" value={f.meeting_link} onChange={set("meeting_link")} data-testid="action-meeting-link" /></Field></div>}
        </div>
      )}
      {action === "reject" && <Field label="Reason"><textarea className="field" rows={2} value={f.reason} onChange={set("reason")} data-testid="action-reason" /></Field>}
      {(action === "notes" || action === "approve") && <Field label="Private admin notes"><textarea className="field" rows={2} value={f.notes} onChange={set("notes")} data-testid="action-notes" /></Field>}
      {timeFields && action !== "propose_alternative" && <p className="text-xs text-[#64748B]">The system checks for conflicts with approved visits, calls and Google Calendar (if connected) before saving, then sends the official email from tpwnitb@gmail.com.</p>}
      <button className="btn-primary" disabled={busy} onClick={submit} data-testid="action-submit-btn">{busy ? "Working…" : "Confirm"}</button>
    </Modal>
  );
}
