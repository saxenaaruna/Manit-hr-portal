import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({ baseURL: API, withCredentials: true });
export const errMsg = (e) => {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : e?.message || "Something went wrong";
};

export const LINKS = {
  tp: "https://www.manit.ac.in/training-placement-and-student-welfare-cell",
  brochure: "https://www.manit.ac.in/sites/default/files/documents/Placement_Brochure_MANIT.pdf",
  dept: "https://www.manit.ac.in/departmnet-wise-placement-brochure",
  jnf: "https://docs.google.com/document/d/1w1Q5-iCF7QW-GcY9G8NWQNm5FQwmmJyp/edit",
  site: "https://www.manit.ac.in",
  liHead: "https://www.linkedin.com/in/aruna-saxena-953188290/",
  liCell: "https://www.linkedin.com/in/tpc-manit-bhopal-4059a0325/",
};

export const STATUS_STYLE = {
  Hot: "bg-red-100 text-red-700 border-red-300",
  Warm: "bg-amber-100 text-amber-800 border-amber-300",
  Cold: "bg-slate-100 text-slate-600 border-slate-300",
};

export const fmt = (iso) => (iso ? new Date(iso).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" }) : "—");
