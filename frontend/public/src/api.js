const BASE = "http://localhost:8000";
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
  login: (username, password) =>
    request("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  searchPatients: (q) => request(`/api/v1/patients?q=${encodeURIComponent(q)}`),
  getPatient: (id) => request(`/api/v1/patients/${encodeURIComponent(id)}`),
  getHistory: (id) => request(`/api/v1/patients/${encodeURIComponent(id)}/encounters`),
  registerPatient: (body) => request("/api/v1/patients", { method: "POST", body: JSON.stringify(body) }),
  createEncounter: (body) => request("/api/v1/encounters", { method: "POST", body: JSON.stringify(body) }),
  listVaccinations: (id) => request(`/api/v1/clinical/vaccinations/${encodeURIComponent(id)}`),
  addVaccination: (body) => request("/api/v1/clinical/vaccinations", { method: "POST", body: JSON.stringify(body) }),
  listMaternal: (id) => request(`/api/v1/clinical/maternal/${encodeURIComponent(id)}`),
  addMaternal: (body) => request("/api/v1/clinical/maternal", { method: "POST", body: JSON.stringify(body) }),
  getFullReport: (id) => request(`/api/v1/reports/${encodeURIComponent(id)}`),
    listInventory: () => request("/api/v1/operations/inventory"),
  addInventory: (body) => request("/api/v1/operations/inventory", { method: "POST", body: JSON.stringify(body) }),
  listBills: (id) => request(`/api/v1/operations/bills/${encodeURIComponent(id)}`),
  addBill: (body) => request("/api/v1/operations/bills", { method: "POST", body: JSON.stringify(body) }),
    searchDiagnoses: (q) => request(`/api/v1/encounters/search/diagnosis?q=${encodeURIComponent(q)}`),
  lowStock: () => request("/api/v1/operations/low-stock"),
  printBill: (id) => request(`/api/v1/operations/bills/${encodeURIComponent(id)}/print`),
};