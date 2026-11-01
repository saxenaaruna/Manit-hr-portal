import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LayoutDashboard, Table2, Mail, FileCheck2, Building2, CalendarDays, PhoneCall, BookOpen, Link2, FileText, History, Settings, LogOut } from "lucide-react";
import { api } from "../../lib/api";

const NAV = [
  ["", "Dashboard", LayoutDashboard], ["leads", "Company Leads Spreadsheet", Table2], ["emails", "Email Communication", Mail],
  ["jnf", "JNF Tracking", FileCheck2], ["visits", "Visit Requests", Building2], ["calendar", "Recruitment Calendar", CalendarDays],
  ["calls", "Call Scheduling", PhoneCall], ["kb", "Knowledge Base", BookOpen], ["resources", "Recruitment Resources", Link2],
  ["templates", "Email Templates", FileText], ["activity", "Activity History", History], ["settings", "Settings", Settings],
];

export default function AdminLayout({ user }) {
  const navigate = useNavigate();
  const logout = async () => { await api.post("/auth/logout"); navigate("/admin/login"); };
  return (
    <div className="flex min-h-screen bg-[#EFF6FF]">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col bg-[#0B2545] text-blue-100 lg:flex">
        <div className="border-b border-white/10 p-5">
          <img src="/img/logo.png" alt="MANIT" className="h-9 w-auto" />
          <p className="mt-3 text-xs uppercase tracking-[0.2em] text-blue-300">T&P Admin</p>
        </div>
        <nav className="flex-1 overflow-y-auto p-3">
          {NAV.map(([to, label, Icon]) => (
            <NavLink key={to} to={`/admin${to ? "/" + to : ""}`} end={!to} data-testid={`nav-${to || "dashboard"}`}
              className={({ isActive }) => `mb-0.5 flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${isActive ? "bg-[#2563EB] text-white" : "hover:bg-white/10"}`}>
              <Icon className="h-4 w-4" />{label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/10 p-4 text-xs">
          <p className="truncate text-white" data-testid="admin-user-email">{user?.email}</p>
          <button onClick={logout} className="mt-2 flex items-center gap-2 text-blue-200 hover:text-white" data-testid="logout-btn"><LogOut className="h-4 w-4" />Logout</button>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <div className="flex gap-2 overflow-x-auto bg-[#0B2545] p-2 lg:hidden">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={`/admin${to ? "/" + to : ""}`} end={!to} className={({ isActive }) => `whitespace-nowrap rounded px-3 py-1 text-xs ${isActive ? "bg-[#2563EB] text-white" : "text-blue-100"}`}>{label}</NavLink>
          ))}
          <button onClick={logout} className="whitespace-nowrap px-3 text-xs text-blue-100">Logout</button>
        </div>
        <main className="p-4 md:p-8"><Outlet context={{ user }} /></main>
      </div>
    </div>
  );
}

export const PageHead = ({ title, desc, children }) => (
  <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 className="font-serif-d text-3xl text-[#0B2545]" data-testid="page-title">{title}</h1>
      {desc && <p className="mt-1 text-sm text-[#64748B]">{desc}</p>}
    </div>
    <div className="flex flex-wrap gap-2">{children}</div>
  </div>
);
