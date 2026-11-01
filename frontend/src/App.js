import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import Portal from "./pages/Portal";
import AdminLogin from "./pages/AdminLogin";
import AuthCallback from "./components/admin/AuthCallback";
import ProtectedRoute from "./components/admin/ProtectedRoute";
import AdminLayout from "./components/admin/AdminLayout";
import Dashboard from "./pages/admin/Dashboard";
import Leads from "./pages/admin/Leads";
import Emails from "./pages/admin/Emails";
import Jnf from "./pages/admin/Jnf";
import Requests from "./pages/admin/Requests";
import CalendarView from "./pages/admin/CalendarView";
import Knowledge from "./pages/admin/Knowledge";
import Templates from "./pages/admin/Templates";
import Activity from "./pages/admin/Activity";
import Settings from "./pages/admin/Settings";

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<Portal />} />
      <Route path="/admin/login" element={<AdminLogin />} />
      <Route path="/admin" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="leads" element={<Leads />} />
        <Route path="emails" element={<Emails />} />
        <Route path="jnf" element={<Jnf />} />
        <Route path="visits" element={<Requests kind="visits" />} />
        <Route path="calls" element={<Requests kind="calls" />} />
        <Route path="calendar" element={<CalendarView />} />
        <Route path="kb" element={<Knowledge />} />
        <Route path="resources" element={<Knowledge resourcesOnly />} />
        <Route path="templates" element={<Templates />} />
        <Route path="activity" element={<Activity />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRouter />
      <Toaster richColors position="top-right" />
    </BrowserRouter>
  );
}
