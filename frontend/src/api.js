const BASE = "https://png-health-backend.onrender.com";
let _token = localStorage.getItem("hub_jwt") || null;
let _facility = localStorage.getItem("hub_facility") || "";

export function setToken(t, facility) { _token = t; if (t) localStorage.setItem("hub_jwt", t); if (facility) localStorage.setItem("hub_facility", facility); }
export function clearToken() { _token = null; localStorage.removeItem("hub_jwt"); }
export function isOnline() { return navigator.onLine; }

async function request(path, opts = {}) {
  if (!navigator.onLine) throw new Error("offline");
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (_token) headers["Authorization"] = `Bearer ${_token}`;
  const res = await fetch(BASE + path, { ...opts, headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  login: (u, p) => request("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username: u, password: p }) }),
  searchPatients: (q) => request(`/api/v1/patients?q=${encodeURIComponent(q)}`),
  getPatient: (id) => request(`/api/v1/patients/${encodeURIComponent(id)}`),
  getHistory: (id) => request(`/api/v1/patients/${encodeURIComponent(id)}/encounters`),
  registerPatient: (body) => request("/api/v1/patients", { method: "POST", body: JSON.stringify(body) }),
  createEncounter: (body) => request("/api/v1/encounters", { method: "POST", body: JSON.stringify(body) }),
    // Referrals
  listOutbound: (facility) => request(`/api/v1/referrals/outbound/${encodeURIComponent(facility)}`),
  listInbound: (facility) => request(`/api/v1/referrals/inbound/${encodeURIComponent(facility)}`),
  createReferral: (body) => request("/api/v1/referrals", { method: "POST", body: JSON.stringify(body) }),
  acceptReferral: (id) => request(`/api/v1/referrals/${encodeURIComponent(id)}/accept`, { method: "POST" }),
  // DHIS2
  dhis2Summary: () => request("/api/v1/dhis2/summary"),
  // Supply Chain
  inventoryAll: () => request("/api/v1/supply/inventory-all"),
  dispatchStock: (body) => request("/api/v1/supply/dispatch", { method: "POST", body: JSON.stringify(body) }),
  listDispatches: () => request("/api/v1/supply/dispatches"),
  receiveDispatch: (id) => request(`/api/v1/supply/dispatches/${encodeURIComponent(id)}/receive`, { method: "POST" }),
  // Guidelines
  listGuidelines: () => request("/api/v1/guidelines"),
  searchGuidelines: (q) => request(`/api/v1/guidelines/search?q=${encodeURIComponent(q)}`),
  // Surveillance
  surveillanceAnomalies: () => request("/api/v1/surveillance/anomalies"),
  syndromicSurveillance: () => request("/api/v1/surveillance/syndromic"),
};
// ---------- PREMIUM FEATURES (appended) ----------
export const premiumApi = {
  // Referrals
  listOutbound: (facility) => request(`/api/v1/referrals/outbound/${encodeURIComponent(facility)}`),
  listInbound: (facility) => request(`/api/v1/referrals/inbound/${encodeURIComponent(facility)}`),
  createReferral: (body) => request("/api/v1/referrals", { method: "POST", body: JSON.stringify(body) }),
  acceptReferral: (id) => request(`/api/v1/referrals/${encodeURIComponent(id)}/accept`, { method: "POST" }),
  // DHIS2
  dhis2Summary: () => request("/api/v1/dhis2/summary"),
  // Supply chain
  inventoryAll: () => request("/api/v1/supply/inventory-all"),
  dispatchStock: (body) => request("/api/v1/supply/dispatch", { method: "POST", body: JSON.stringify(body) }),
  listDispatches: () => request("/api/v1/supply/dispatches"),
  receiveDispatch: (id) => request(`/api/v1/supply/dispatches/${encodeURIComponent(id)}/receive`, { method: "POST" }),
  // Guidelines
  listGuidelines: () => request("/api/v1/guidelines"),
  searchGuidelines: (q) => request(`/api/v1/guidelines/search?q=${encodeURIComponent(q)}`),
  // Surveillance
  surveillanceAnomalies: () => request("/api/v1/surveillance/anomalies"),
  syndromicSurveillance: () => request("/api/v1/surveillance/syndromic"),
};