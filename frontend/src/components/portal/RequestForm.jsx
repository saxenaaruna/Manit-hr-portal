import { useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { Field } from "../Modal";

const PURPOSES = ["Campus Placement Drive", "Internship Recruitment", "Pre-Placement Talk", "Recruitment Assessment / Interview", "Company Presentation", "Other"];
const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });

const VISIT_INIT = { company_name: "", hr_name: "", designation: "", work_email: "", contact_number: "", visit_purpose: PURPOSES[0], requested_date: "", requested_start_time: "10:00", requested_end_time: "13:00", remarks: "" };
const CALL_INIT = { company_name: "", hr_name: "", designation: "", work_email: "", contact_number: "", preferred_date: "", preferred_time: "11:00", duration: 30, discussion_purpose: "", call_mode: "Google Meet", remarks: "" };

export default function RequestForm({ kind }) {
  const isVisit = kind === "visits";
  const [f, setF] = useState(isVisit ? VISIT_INIT : CALL_INIT);
  const [busy, setBusy] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const dateKey = isVisit ? "requested_date" : "preferred_date";
  const pre = `${kind}-form`;

  const checkDate = async (d) => {
    setF((p) => ({ ...p, [dateKey]: d }));
    if (!d) return setBusy(null);
    try { setBusy((await api.get(`/public/availability?date=${d}`)).data); } catch { setBusy(null); }
  };
  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const r = await api.post(`/public/${kind}`, { ...f, duration: Number(f.duration) });
      setResult(r.data); setF(isVisit ? VISIT_INIT : CALL_INIT); setBusy(null);
    } catch (err) { toast.error(errMsg(err)); } finally { setLoading(false); }
  };

  if (result) return (
    <div className="rounded-lg border border-[#93B4EC] bg-[#DBEAFE] p-6" data-testid={`${pre}-success`}>
      <p className="text-sm font-semibold text-[#0B2545]">Request ID: <span data-testid={`${pre}-request-id`}>{result.id}</span></p>
      <p className="mt-2 text-sm text-[#172B4D]">{result.message}</p>
      <button className="btn-outline mt-4" onClick={() => setResult(null)} data-testid={`${pre}-new-btn`}>Submit another request</button>
    </div>
  );

  const inp = (k, label, props = {}) => <Field label={label}><input className="field" value={f[k]} onChange={set(k)} data-testid={`${pre}-${k}`} {...props} /></Field>;
  return (
    <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" data-testid={pre}>
      {inp("company_name", "Company Name *", { required: true })}
      {inp("hr_name", "HR Representative Name *", { required: true })}
      {inp("designation", "Designation")}
      {inp("work_email", "Work Email *", { type: "email", required: true })}
      {inp("contact_number", "Contact Number")}
      {isVisit ? (
        <Field label="Purpose of Visit *"><select className="field" value={f.visit_purpose} onChange={set("visit_purpose")} data-testid={`${pre}-visit_purpose`}>{PURPOSES.map((p) => <option key={p}>{p}</option>)}</select></Field>
      ) : (
        <Field label="Preferred Mode"><select className="field" value={f.call_mode} onChange={set("call_mode")} data-testid={`${pre}-call_mode`}>{["Phone", "Google Meet", "Other"].map((p) => <option key={p}>{p}</option>)}</select></Field>
      )}
      <Field label="Preferred Date *"><input type="date" min={today} required className="field" value={f[dateKey]} onChange={(e) => checkDate(e.target.value)} data-testid={`${pre}-date`} /></Field>
      {isVisit ? (
        <div className="grid grid-cols-2 gap-3">
          {inp("requested_start_time", "Start Time *", { type: "time", required: true })}
          {inp("requested_end_time", "End Time *", { type: "time", required: true })}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {inp("preferred_time", "Preferred Time *", { type: "time", required: true })}
          <Field label="Duration"><select className="field" value={f.duration} onChange={set("duration")} data-testid={`${pre}-duration`}>{[15, 30, 45, 60].map((d) => <option key={d} value={d}>{d} minutes</option>)}</select></Field>
        </div>
      )}
      {!isVisit && <div className="sm:col-span-2">{inp("discussion_purpose", "Discussion Purpose")}</div>}
      {busy && (
        <div className="rounded-md border border-[#D6E4F7] bg-[#EFF6FF] p-3 text-xs text-[#123B70] sm:col-span-2" data-testid={`${pre}-availability`}>
          <b>Already booked on this date:</b> {busy.busy.length ? busy.busy.map((b) => `${b.start}–${b.end}`).join(", ") : "No confirmed bookings"}.
          {busy.google_calendar !== "checked" && " (Only internal bookings checked.)"} Availability is indicative — all requests are reviewed by the T&P Cell.
        </div>
      )}
      <div className="sm:col-span-2"><Field label="Additional Remarks"><textarea rows={3} className="field" value={f.remarks} onChange={set("remarks")} data-testid={`${pre}-remarks`} /></Field></div>
      <div className="sm:col-span-2"><button className="btn-primary" disabled={loading} data-testid={`${pre}-submit`}>{loading ? "Submitting…" : isVisit ? "Submit Visit Request" : "Request a Call"}</button></div>
    </form>
  );
}
