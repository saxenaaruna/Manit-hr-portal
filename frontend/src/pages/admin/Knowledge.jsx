import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { ExternalLink } from "lucide-react";
import { api, errMsg, fmt } from "../../lib/api";
import { PageHead } from "../../components/admin/AdminLayout";
import Modal, { Field } from "../../components/Modal";

const CATS = ["Institute Information", "Academic Programs", "Department Information", "Placement Process", "Internship Recruitment", "Eligibility Criteria", "Placement Statistics", "Campus Visit Guidelines", "Recruitment Invitation", "JNF Information", "Contact Information", "Other Approved Information"];

export default function Knowledge({ resourcesOnly }) {
  const [rows, setRows] = useState([]); const [edit, setEdit] = useState(null); const [cat, setCat] = useState("");
  const load = useCallback(() => api.get("/admin/kb").then((r) => setRows(r.data)), []);
  useEffect(() => { load(); }, [load]);
  const patch = async (id, p, msg) => { try { await api.patch(`/admin/kb/${id}`, p); toast.success(msg || "Saved"); load(); } catch (e) { toast.error(errMsg(e)); } };
  const del = async (r) => { if (!window.confirm(`Delete "${r.title}"?`)) return; await api.delete(`/admin/kb/${r.id}`); toast.success("Deleted"); load(); };
  const list = rows.filter((r) => (resourcesOnly ? r.is_resource : true) && (!cat || r.category === cat));
  const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
  return (
    <div>
      <PageHead title={resourcesOnly ? "Recruitment Resources" : "Knowledge Base"} desc={resourcesOnly ? "Official links shown publicly under Recruitment Resources." : "Only published entries are used by MANIT Connect and the public portal. Changes apply immediately."}>
        {!resourcesOnly && <select className="field w-auto" value={cat} onChange={(e) => setCat(e.target.value)} data-testid="kb-category-filter"><option value="">All categories</option>{CATS.map((c) => <option key={c}>{c}</option>)}</select>}
        <button className="btn-primary" onClick={() => setEdit({ title: "", category: resourcesOnly ? "Other Approved Information" : CATS[0], content: "", source_url: "", academic_year: "", validity_period: "", published: false, is_resource: !!resourcesOnly })} data-testid="kb-add-btn">Add entry</button>
      </PageHead>
      <div className="grid gap-3">
        {list.map((r, i) => (
          <div key={r.id} className="card p-4" data-testid={`kb-row-${i}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase tracking-wide text-[#2563EB]">{r.category}{r.is_resource ? " · Resource" : ""}{r.academic_year ? ` · ${r.academic_year}` : ""}</p>
                <p className="font-semibold text-[#0B2545]">{r.title}</p>
                <p className="mt-1 line-clamp-2 whitespace-pre-line text-sm text-[#64748B]">{r.content}</p>
                {r.source_url && <a href={r.source_url} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs text-[#1D4ED8]">{r.source_url}<ExternalLink className="h-3 w-3" /></a>}
                <p className="mt-1 text-[11px] text-[#64748B]">Last verified: {r.last_verified_at || "never"} · Updated {fmt(r.updated_at)}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded px-2 py-0.5 text-xs font-semibold ${r.published ? "bg-[#DBEAFE] text-[#1D4ED8]" : "bg-slate-100 text-slate-600"}`} data-testid={`kb-status-${i}`}>{r.published ? "Published" : "Unpublished"}</span>
                <button className="btn-outline px-2 py-1 text-xs" onClick={() => patch(r.id, { published: !r.published }, r.published ? "Unpublished" : "Published")} data-testid={`kb-toggle-${i}`}>{r.published ? "Unpublish" : "Publish"}</button>
                <button className="btn-outline px-2 py-1 text-xs" onClick={() => patch(r.id, { last_verified_at: today }, "Marked verified")} data-testid={`kb-verify-${i}`}>Mark verified</button>
                <button className="btn-outline px-2 py-1 text-xs" onClick={() => setEdit(r)} data-testid={`kb-edit-${i}`}>Edit</button>
                <button className="btn-outline px-2 py-1 text-xs text-red-600" onClick={() => del(r)} data-testid={`kb-delete-${i}`}>Delete</button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {edit && <KbForm entry={edit} onClose={() => setEdit(null)} onDone={() => { setEdit(null); load(); }} />}
    </div>
  );
}

function KbForm({ entry, onClose, onDone }) {
  const [f, setF] = useState(entry);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const save = async () => {
    const body = { title: f.title, category: f.category, content: f.content, source_url: f.source_url, academic_year: f.academic_year, validity_period: f.validity_period, published: f.published, is_resource: f.is_resource };
    try { entry.id ? await api.patch(`/admin/kb/${entry.id}`, body) : await api.post("/admin/kb", body); toast.success("Saved"); onDone(); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <Modal open onClose={onClose} title={entry.id ? "Edit entry" : "New entry"} wide testid="kb-form">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Title"><input className="field" value={f.title} onChange={set("title")} data-testid="kb-title" /></Field>
        <Field label="Category"><select className="field" value={f.category} onChange={set("category")} data-testid="kb-category">{CATS.map((c) => <option key={c}>{c}</option>)}</select></Field>
        <div className="sm:col-span-2"><Field label="Content"><textarea className="field" rows={8} value={f.content || ""} onChange={set("content")} data-testid="kb-content" /></Field></div>
        <Field label="Source URL"><input className="field" value={f.source_url || ""} onChange={set("source_url")} data-testid="kb-source" /></Field>
        <Field label="Academic Year"><input className="field" value={f.academic_year || ""} onChange={set("academic_year")} /></Field>
        <Field label="Validity Period"><input className="field" value={f.validity_period || ""} onChange={set("validity_period")} placeholder="e.g. until May 2027" /></Field>
        <div className="flex items-end gap-6 text-sm">
          <label className="flex items-center gap-2"><input type="checkbox" checked={!!f.published} onChange={set("published")} data-testid="kb-published" />Published</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={!!f.is_resource} onChange={set("is_resource")} />Show as public resource</label>
        </div>
      </div>
      <button className="btn-primary" onClick={save} data-testid="kb-save-btn">Save</button>
    </Modal>
  );
}
