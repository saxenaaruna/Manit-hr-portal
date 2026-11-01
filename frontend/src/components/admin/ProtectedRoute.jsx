import { useEffect, useState, cloneElement } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../../lib/api";

export default function ProtectedRoute({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState(location.state?.user || null);
  useEffect(() => {
    if (user) return;
    api.get("/auth/me").then((r) => setUser(r.data)).catch(() => navigate("/admin/login", { replace: true }));
  }, [user, navigate]);
  if (!user) return <div className="flex h-screen items-center justify-center text-[#123B70]" data-testid="auth-loading">Verifying access…</div>;
  return cloneElement(children, { user });
}
