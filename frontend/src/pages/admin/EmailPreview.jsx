import { useEffect, useState } from "react";
import { toast } from "sonner";
import Modal from "../../components/Modal";
import { api, errMsg } from "../../lib/api";

export default function EmailPreview({ tplKey = "invitation", lead, draft, onClose, onSend }) {
  const [p, setP] = useState(null);
  useEffect(() => {
    api.post(`/admin/templates/${tplKey}/preview`, { lead_id: lead?.id, subject: draft?.subject, body: draft?.body })
      .then((r) => setP(r.data)).catch((e) => { toast.error(errMsg(e)); onClose(); });
  }, []); // eslint-disable-line
  if (!p) return null;
  const linkify = (t) => t.split(/(https?:\/\/\S+)/g).map((s, i) => (/^https?:\/\//.test(s) ? <a key={i} href={s} target="_blank" rel="noreferrer" className="text-[#1D4ED8] underline">{s}</a> : s));
  return (
    <Modal open onClose={onClose} title="Email preview" wide testid="email-preview-modal">
      <div className="rounded-md border border-[#D6E4F7] text-sm">
        <div className="space-y-1 border-b border-[#D6E4F7] bg-[#EFF6FF] p-3 text-xs">
          <p><span className="inline-block w-16 text-[#64748B]">From</span><b data-testid="preview-from">{p.from}</b></p>
          <p><span className="inline-block w-16 text-[#64748B]">To</span><span data-testid="preview-to">{p.to}</span></p>
          <p><span className="inline-block w-16 text-[#64748B]">Subject</span><b data-testid="preview-subject">{p.subject}</b></p>
        </div>
        <div className="max-h-[55vh] overflow-y-auto whitespace-pre-wrap bg-white p-4 font-sans leading-relaxed text-[#172B4D]" data-testid="preview-body">{linkify(p.body)}</div>
      </div>
      <p className="text-xs text-[#64748B]">Sent as plain text exactly as shown{lead ? "" : ", with sample values filled in for placeholders"}.</p>
      {onSend && <button className="btn-primary w-fit" onClick={onSend} data-testid="preview-send-btn">{lead?.invitation_success_at ? "Resend invitation now" : "Send invitation now"}</button>}
    </Modal>
  );
}
