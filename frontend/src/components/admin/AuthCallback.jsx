import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, errMsg } from "../../lib/api";

export default function AuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const done = useRef(false);
  useEffect(() => {
    if (done.current) return;
    done.current = true;
    const sid = new URLSearchParams(location.hash.slice(1)).get("session_id");
    window.history.replaceState(null, "", window.location.pathname);
    api.post("/auth/session", { session_id: sid })
      .then((r) => navigate("/admin", { replace: true, state: { user: r.data } }))
      .catch((e) => navigate("/admin/login", { replace: true, state: { error: errMsg(e) } }));
  }, [location.hash, navigate]);
  return null;
}
