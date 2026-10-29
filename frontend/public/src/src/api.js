const BASE = "http://localhost:8000";

let _token = localStorage.getItem("hub_jwt") || null;
let _facility = localStorage.getItem("hub_facility") || "";

export function setToken(t, facility) {
  _token = t;
  _facility = facility || _facility;
  if (t) localStorage.setItem("hub_jwt", t);
  if (facility) localStorage.setItem("hub_facility", facility);
}
export function getToken() { return _token; }
export function getFacility() { return _facility; }
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
  getPatient: (id) => request(`/api/v1/patients/${encodeURIComponent(id)}`),
  createEncounter: (body) =>
    request("/api/v1/encounters", { method: "POST", body: JSON.stringify(body) }),
  syncBatch: (device_id, encounters) =>
    request("/api/v1/sync/batch", {
      method: "POST",
      body: JSON.stringify({ device_id, encounters }),
    }),
};
