import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Linkedin, ExternalLink, Phone, Mail, Building, FileText, Menu, X, Search } from "lucide-react";
import { api, errMsg, LINKS } from "../lib/api";
import ChatWidget from "../components/portal/ChatWidget";
import RequestForm from "../components/portal/RequestForm";

const NAV = [["home", "Home"], ["recruitment", "Recruitment Information"], ["programs", "Academic Programs"], ["brochure", "Placement Brochure"], ["resources", "Recruitment Resources"], ["visits", "Campus Visits"], ["call", "Schedule a Call"], ["contact", "Contact"]];

const Section = ({ id, eyebrow, title, children, alt }) => (
  <section id={id} className={`scroll-mt-20 px-5 py-16 md:px-12 md:py-20 ${alt ? "bg-white" : ""}`}>
    <div className="mx-auto max-w-6xl">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#2563EB]">{eyebrow}</p>
      <h2 className="font-serif-d mt-2 text-3xl text-[#0B2545] md:text-4xl">{title}</h2>
      <div className="mt-8">{children}</div>
    </div>
  </section>
);

const ext = { target: "_blank", rel: "noopener noreferrer" };

export default function Portal() {
  const [kb, setKb] = useState([]);
  const [chat, setChat] = useState(false);
  const [menu, setMenu] = useState(false);
  useEffect(() => { api.get("/public/kb").then((r) => setKb(r.data)).catch(() => {}); }, []);
  const byCat = (cats) => kb.filter((k) => cats.includes(k.category) && !k.is_resource);
  const resources = kb.filter((k) => k.is_resource);
  const jnf = resources.find((r) => r.category === "JNF Information")?.source_url || LINKS.jnf;

  return (
    <div className="bg-[#EFF6FF]">
      <header className="sticky top-0 z-40 bg-[#0B2545] text-white shadow">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3">
          <a href="#home" className="flex items-center gap-3" data-testid="brand-link">
            <img src="/img/logo.png" alt="MANIT Bhopal" className="h-9 w-auto md:h-11" />
          </a>
          <nav className="hidden items-center gap-4 text-[13px] xl:flex">
            {NAV.map(([id, l]) => <a key={id} href={`#${id}`} className="text-blue-100 transition-colors hover:text-white" data-testid={`nav-${id}`}>{l}</a>)}
            <button onClick={() => setChat(true)} className="text-blue-100 hover:text-white" data-testid="nav-chat">Chat with MANIT Connect</button>
            <Link to="/admin/login" className="text-blue-300 hover:text-white" data-testid="nav-admin-login">Admin Login</Link>
          </nav>
          <div className="flex items-center gap-2">
            <a href="#visits" className="hidden rounded-md bg-[#2563EB] px-4 py-2 text-sm font-semibold hover:bg-[#1D4ED8] sm:inline-block" data-testid="header-schedule-visit-btn">Schedule a Campus Visit</a>
            <button className="xl:hidden" onClick={() => setMenu(!menu)} aria-label="Menu" data-testid="mobile-menu-btn">{menu ? <X /> : <Menu />}</button>
          </div>
        </div>
        {menu && (
          <div className="grid gap-1 border-t border-white/10 px-5 py-3 text-sm xl:hidden">
            {NAV.map(([id, l]) => <a key={id} href={`#${id}`} onClick={() => setMenu(false)} className="py-1 text-blue-100">{l}</a>)}
            <button onClick={() => { setChat(true); setMenu(false); }} className="py-1 text-left text-blue-100">Chat with MANIT Connect</button>
            <Link to="/admin/login" className="py-1 text-blue-300">Admin Login</Link>
          </div>
        )}
      </header>

      <section id="home" className="relative overflow-hidden">
        <img src="/img/building.jpg" alt="MANIT Bhopal main building" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#0B2545]/95 via-[#0B2545]/80 to-[#123B70]/40" />
        <div className="relative mx-auto max-w-7xl px-5 py-24 md:px-12 md:py-36">
          <p className="fade-up text-xs font-semibold uppercase tracking-[0.25em] text-blue-200">Training & Placement Cell · MANIT Bhopal</p>
          <h1 className="font-serif-d fade-up mt-4 max-w-3xl text-4xl leading-tight text-white sm:text-5xl lg:text-6xl" data-testid="hero-title">Connect with Talent at MANIT Bhopal</h1>
          <p className="fade-up mt-6 max-w-2xl text-base text-blue-100 md:text-lg">Explore recruitment opportunities at MANIT Bhopal, connect with our Training & Placement Cell, access institutional information, and coordinate your campus recruitment activities.</p>
          <div className="fade-up mt-10 flex flex-wrap gap-3">
            <button onClick={() => setChat(true)} className="rounded-md bg-[#1D4ED8] px-5 py-3 text-sm font-semibold text-white hover:bg-[#2563EB]" data-testid="hero-chat-btn">Chat with MANIT Connect</button>
            <a href="#recruitment" className="rounded-md border border-white/40 bg-white/10 px-5 py-3 text-sm font-semibold text-white backdrop-blur hover:bg-white/20" data-testid="hero-explore-btn">Explore Recruitment Opportunities</a>
            <a href="#visits" className="rounded-md bg-white px-5 py-3 text-sm font-semibold text-[#0B2545] hover:bg-[#DBEAFE]" data-testid="hero-visit-btn">Schedule a Campus Visit</a>
          </div>
        </div>
      </section>

      <Section id="about" eyebrow="The Institute" title="Maulana Azad National Institute of Technology, Bhopal" alt>
        <div className="grid items-center gap-10 md:grid-cols-5">
          <img src="/img/building.jpg" alt="MANIT Bhopal campus" className="rounded-lg object-cover md:col-span-2" />
          <div className="md:col-span-3 space-y-4 text-[15px] leading-relaxed text-[#172B4D]">
            {(byCat(["Institute Information"])[0]?.content || "MANIT Bhopal is one of the leading National Institutes of Technology in India.").split("\n").map((p, i) => <p key={i}>{p}</p>)}
            <a href={LINKS.site} {...ext} className="inline-flex items-center gap-1 text-sm font-semibold text-[#1D4ED8] hover:underline" data-testid="official-site-link">www.manit.ac.in <ExternalLink className="h-3.5 w-3.5" /></a>
          </div>
        </div>
      </Section>

      <Section id="recruitment" eyebrow="For Recruiters" title="Recruitment Information">
        <div className="grid gap-5 md:grid-cols-2">
          {byCat(["Placement Process", "Internship Recruitment", "Campus Visit Guidelines", "Eligibility Criteria", "Placement Statistics"]).map((k) => (
            <article key={k.id} className="card p-6" data-testid="recruitment-info-card">
              <p className="text-xs font-semibold uppercase tracking-wide text-[#2563EB]">{k.category}</p>
              <h3 className="mt-1 text-lg font-semibold text-[#0B2545]">{k.title}</h3>
              <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-[#172B4D]">{k.content}</p>
            </article>
          ))}
        </div>
      </Section>

      <Section id="programs" eyebrow="Academics" title="Academic Programs" alt>
        <div className="grid gap-5 md:grid-cols-2">
          {byCat(["Academic Programs"]).map((k) => (
            <article key={k.id} className="rounded-lg border border-[#D6E4F7] bg-[#EFF6FF] p-6" data-testid="program-card">
              <h3 className="text-lg font-semibold text-[#0B2545]">{k.title}</h3>
              <ul className="mt-3 space-y-1.5 text-sm text-[#172B4D]">{k.content.split("\n").filter(Boolean).map((l, i) => <li key={i}>{l.replace(/^- /, "")}</li>)}</ul>
            </article>
          ))}
        </div>
      </Section>

      <Section id="brochure" eyebrow="Placement Brochure" title="Official Placement Brochures">
        <div className="grid gap-4 sm:grid-cols-2">
          <a href={LINKS.brochure} {...ext} className="card flex items-center gap-4 p-6 transition-colors hover:border-[#2563EB]" data-testid="brochure-link"><FileText className="h-8 w-8 text-[#1D4ED8]" /><div><p className="font-semibold text-[#0B2545]">MANIT Placement Brochure (PDF)</p><p className="text-xs text-[#64748B]">Opens the official brochure on manit.ac.in</p></div></a>
          <a href={LINKS.dept} {...ext} className="card flex items-center gap-4 p-6 transition-colors hover:border-[#2563EB]" data-testid="dept-brochure-link"><FileText className="h-8 w-8 text-[#1D4ED8]" /><div><p className="font-semibold text-[#0B2545]">Department-wise Placement Brochures</p><p className="text-xs text-[#64748B]">Opens the department brochure page</p></div></a>
        </div>
      </Section>

      <Section id="resources" eyebrow="Resources" title="Recruitment Resources" alt>
        <div className="divide-y divide-[#D6E4F7] rounded-lg border border-[#D6E4F7]">
          {(resources.length ? resources : []).map((r) => (
            <a key={r.id} href={r.source_url} {...ext} className="flex items-center justify-between gap-4 p-5 transition-colors hover:bg-[#EFF6FF]" data-testid="resource-link">
              <div><p className="font-semibold text-[#0B2545]">{r.title}</p><p className="mt-1 text-sm text-[#64748B]">{r.content}</p></div>
              <ExternalLink className="h-4 w-4 shrink-0 text-[#1D4ED8]" />
            </a>
          ))}
        </div>
        <p className="mt-4 text-sm text-[#64748B]">Please complete the <a href={jnf} {...ext} className="font-semibold text-[#1D4ED8] hover:underline" data-testid="jnf-inline-link">Job Notification Form (JNF)</a> to begin the recruitment process.</p>
      </Section>

      <Section id="visits" eyebrow="Campus Visits" title="Request a Campus Visit">
        <p className="mb-6 max-w-3xl text-sm text-[#64748B]">Submit your preferred date and time. Every request is reviewed by the Head of T&P or an authorised administrator; an official confirmation is emailed only after approval.</p>
        <div className="card p-6 md:p-8"><RequestForm kind="visits" /></div>
      </Section>

      <Section id="call" eyebrow="Speak with Us" title="Schedule a Call with the Head of T&P" alt>
        <p className="mb-6 max-w-3xl text-sm text-[#64748B]">Request a discussion with Dr. Aruna Saxena. Your preferred slot will be reviewed and confirmed by email after approval.</p>
        <div className="rounded-lg border border-[#D6E4F7] bg-[#EFF6FF] p-6 md:p-8"><RequestForm kind="calls" /></div>
      </Section>

      <StatusLookup />

      <Section id="contact" eyebrow="Leadership & Contact" title="Head of Training & Placement" alt>
        <div className="grid items-start gap-10 md:grid-cols-5">
          <img src="/img/aruna.png" alt="Dr. Aruna Saxena" className="w-full rounded-lg border border-[#D6E4F7] object-cover md:col-span-2" data-testid="head-photo" />
          <div className="md:col-span-3">
            <h3 className="font-serif-d text-3xl text-[#0B2545]" data-testid="head-name">Dr. Aruna Saxena</h3>
            <p className="mt-1 text-[#123B70]">Professor & Head<br />Training & Placement Cell<br />MANIT Bhopal</p>
            <div className="mt-6 space-y-3 text-sm">
              <p className="flex items-center gap-3"><Phone className="h-4 w-4 text-[#1D4ED8]" />Mobile: <a href="tel:+917898216935" className="font-medium" data-testid="head-mobile">+91 78982 16935</a></p>
              <p className="flex items-center gap-3"><Building className="h-4 w-4 text-[#1D4ED8]" />Office: <a href="tel:07552670802" className="font-medium">0755-2670802</a></p>
              <p className="flex items-center gap-3"><Mail className="h-4 w-4 text-[#1D4ED8]" />Email: <a href="mailto:tpwnitb@gmail.com" className="font-medium text-[#1D4ED8] hover:underline" data-testid="head-email">tpwnitb@gmail.com</a></p>
            </div>
            <div className="mt-10 rounded-lg border border-[#D6E4F7] bg-[#EFF6FF] p-6" id="connect">
              <h4 className="font-serif-d text-xl text-[#0B2545]">Connect with MANIT Training & Placement</h4>
              <div className="mt-4 grid gap-3">
                <a href={LINKS.liHead} {...ext} className="flex items-center gap-3 rounded-md bg-white p-3 text-sm font-medium text-[#123B70] hover:bg-[#DBEAFE]" data-testid="linkedin-head-link"><Linkedin className="h-5 w-5 text-[#0A66C2]" />Head of Training & Placement — Dr. Aruna Saxena</a>
                <a href={LINKS.liCell} {...ext} className="flex items-center gap-3 rounded-md bg-white p-3 text-sm font-medium text-[#123B70] hover:bg-[#DBEAFE]" data-testid="linkedin-cell-link"><Linkedin className="h-5 w-5 text-[#0A66C2]" />MANIT Training & Placement Cell</a>
              </div>
            </div>
          </div>
        </div>
      </Section>

      <footer className="bg-[#0B2545] px-5 py-12 text-sm text-blue-100 md:px-12">
        <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-3">
          <div><img src="/img/logo.png" alt="MANIT" className="h-10 w-auto" /><p className="mt-4 font-semibold text-white">MANIT Bhopal — Training & Placement Cell</p></div>
          <div className="space-y-2">
            <a href={LINKS.site} {...ext} className="block hover:text-white">Official MANIT Website</a>
            <a href={LINKS.tp} {...ext} className="block hover:text-white">Training & Placement Cell</a>
            <a href={LINKS.brochure} {...ext} className="block hover:text-white">Placement Brochure</a>
            <a href={jnf} {...ext} className="block hover:text-white">Job Notification Form</a>
          </div>
          <div className="space-y-2">
            <a href="mailto:tpwnitb@gmail.com" className="block hover:text-white" data-testid="footer-email">tpwnitb@gmail.com</a>
            <p>+91 78982 16935 · 0755-2670802</p>
            <Link to="/admin/login" className="block text-blue-300 hover:text-white" data-testid="footer-admin-login">Admin Login</Link>
          </div>
        </div>
      </footer>
      <ChatWidget open={chat} setOpen={setChat} />
    </div>
  );
}

function StatusLookup() {
  const [id, setId] = useState(""); const [email, setEmail] = useState(""); const [res, setRes] = useState(null);
  const go = async (e) => {
    e.preventDefault();
    try { setRes((await api.get("/public/status", { params: { request_id: id, email } })).data); }
    catch (err) { setRes({ error: errMsg(err) }); }
  };
  return (
    <section className="px-5 pb-16 md:px-12">
      <form onSubmit={go} className="card mx-auto flex max-w-6xl flex-wrap items-end gap-3 p-5" data-testid="status-lookup-form">
        <div className="mr-auto"><p className="font-semibold text-[#0B2545]">Check request status</p><p className="text-xs text-[#64748B]">Enter your request ID and the work email used.</p></div>
        <input className="field max-w-[160px]" placeholder="VR-XXXXXX" value={id} onChange={(e) => setId(e.target.value)} required data-testid="status-request-id" />
        <input className="field max-w-[240px]" type="email" placeholder="Work email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="status-email" />
        <button className="btn-primary" data-testid="status-check-btn"><Search className="h-4 w-4" />Check</button>
        {res && <p className="w-full text-sm" data-testid="status-result">{res.error ? <span className="text-red-600">{res.error}</span> : <>{res.type} <b>{res.id}</b> — <b>{res.status}</b>{res.approved_date && ["Approved", "Rescheduled"].includes(res.status) ? ` · ${res.approved_date} ${res.start}–${res.end} IST` : ""}{res.status === "Alternative Proposed" ? ` · Proposed: ${res.proposed_date} ${res.proposed_start_time}–${res.proposed_end_time}` : ""}</>}</p>}
      </form>
    </section>
  );
}
