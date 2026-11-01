import { useState } from "react";
import { toast } from "sonner";
import Modal, { Field } from "../../components/Modal";
import { api, errMsg } from "../../lib/api";

const PURPOSES = ["Campus Placement Drive", "Internship Recruitment", "Pre-Placement Talk", "Recruitment Assessment / Interview", "Company Presentation", "Other"];

export const reportSchedule = (d) => {
  if (d.error) return toast.warning(d.error);
  toast.success(`Saved as ${d.item.status}`);
  if (d.calendar) toast.info(`Google Calendar: ${d.calendar}`);
  if (d.email) (d.email.ok ? toast.success : toast.error)(d.email.message, { duration: 8000 });
};

// Admin manual scheduling (creates and approves immediately with conflict check)
export default function ScheduleCallDialog({ lead, kind = "calls", onClose, onDone }) {
  const isVisit = kind === "visits";
  const [f, setF] = useState({
    company_name: lead?.company_name || "", hr_name: lead?.hr_name || "", work_email: lead?.work_email || "", contact_number: lead?.contact_number || "", designation: lead?.designation || "",
    preferred_date: "", preferred_time: "11:00", duration: 30, call_mode: "Google Meet", discussion_purpose: "", meeting_link: "",
    requested_date: "", requested_start_time: "10:00", requested_end_time: "13:00", visit_purpose: PURPOSES[0],
  });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const inp = (k, label, type = "text") => <Field label={label}><input type={type} className="field" value={f[k]} onChange={set(k)} data-testid={`sched-${k}`} /></Field>;
  const submit = async () => {
    setBusy(true);
    try { const r = await api.post(`/admin/req/${kind}`, { ...f, duration: Number(f.duration) }); reportSchedule(r.data); onDone?.(); onClose(); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <Modal open onClose={onClose} title={isVisit ? "Create campus visit (manual)" : "Schedule call with HR (manual)"} testid="schedule-dialog">
      <div className="grid gap-3 sm:grid-cols-2">
        {inp("company_name", "Company")}{inp("hr_name", "HR Name")}{inp("work_email", "Work Email", "email")}{inp("contact_number", "Contact")}
        {isVisit ? (<>
          <Field label="Purpose"><select className="field" value={f.visit_purpose} onChange={set("visit_purpose")}>{PURPOSES.map((p) => <option key={p}>{p}</option>)}</select></Field>
          {inp("requested_date", "Date", "date")}{inp("requested_start_time", "Start", "time")}{inp("requested_end_time", "End", "time")}
        </>) : (<>
          {inp("preferred_date", "Date", "date")}{inp("preferred_time", "Time", "time")}
          <Field label="Duration"><select className="field" value={f.duration} onChange={set("duration")}>{[15, 30, 45, 60].map((d) => <option key={d} value={d}>{d} min</option>)}</select></Field>
          <Field label="Mode"><select className="field" value={f.call_mode} onChange={set("call_mode")}>{["Phone", "Google Meet", "Other"].map((d) => <option key={d}>{d}</option>)}</select></Field>
          {inp("discussion_purpose", "Purpose")}{inp("meeting_link", "Meeting link")}
        </>)}
      </div>
      <button className="btn-primary" disabled={busy} onClick={submit} data-testid="sched-submit-btn">{busy ? "Scheduling…" : "Schedule & send confirmation"}</button>
    </Modal>
  );
}
