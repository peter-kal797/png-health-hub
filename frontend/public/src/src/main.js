import { api, setToken, isOnline } from "./api.js";
import { getDeviceKey } from "./crypto.js";
import {
  cachePatient, getCachedPatient, queueEncounter,
  listPending, markSynced, decryptQueueItem, purgeStalePatients,
} from "./db.js";

const PIN_FOR_DEMO = "123456";
let deviceKey = null;

const $ = (s) => document.querySelector(s);
const status = (s) => { $("#status").textContent = s; };

async function init() {
  deviceKey = await getDeviceKey(PIN_FOR_DEMO);

  if ("serviceWorker" in navigator) {
    try { await navigator.serviceWorker.register("/sw.js"); }
    catch (e) { console.warn("SW registration failed", e); }
  }

  const purged = await purgeStalePatients(7);
  if (purged) console.log(`Purged ${purged} stale patient records`);

  $("#btn-login").onclick = async () => {
    try {
      const res = await api.login($("#username").value, $("#password").value);
      setToken(res.access_token, res.facility);
      status(`Logged in as ${res.full_name} (${res.role}) @ ${res.facility}`);
    } catch (e) { status("Login failed: " + e.message); }
  };

  $("#btn-lookup").onclick = async () => {
    const id = $("#lookup-id").value.trim();
    if (!id) return;
    try {
      if (isOnline()) {
        const p = await api.getPatient(id);
        await cachePatient(deviceKey, p);
        $("#patient-out").textContent = JSON.stringify(p, null, 2);
      } else {
        const cached = await getCachedPatient(deviceKey, id);
        $("#patient-out").textContent = cached
          ? JSON.stringify({ ...cached, _offline: true }, null, 2)
          : "Not in offline cache.";
      }
    } catch (e) { $("#patient-out").textContent = "Error: " + e.message; }
  };

  $("#btn-record").onclick = async () => {
    const enc = {
      patient_id: $("#enc-patient").value.trim(),
      facility_name: "CHW_LOCAL",
      health_worker_id: "device",
      symptoms: $("#enc-symptoms").value,
      diagnosis: $("#enc-diagnosis").value,
      medications_prescribed: $("#enc-meds").value,
      client_event_id: crypto.randomUUID(),
    };
    if (!enc.patient_id) return;
    try {
      if (isOnline()) {
        const saved = await api.createEncounter(enc);
        $("#record-out").textContent = "Saved online:\n" + JSON.stringify(saved, null, 2);
      } else {
        await queueEncounter(deviceKey, enc);
        $("#record-out").textContent = "Queued offline. Will sync when online.";
        const reg = await navigator.serviceWorker.ready;
        if ("sync" in reg) await reg.sync.register("sync-encounters");
      }
    } catch (e) { $("#record-out").textContent = "Error: " + e.message; }
  };

  $("#btn-sync").onclick = async () => {
    const out = $("#sync-out");
    out.textContent = "Syncing...";
    try {
      const pending = await listPending();
      if (!pending.length) { out.textContent = "Nothing to sync."; return; }
      const payload = [];
      for (const rec of pending) {
        const item = await decryptQueueItem(deviceKey, rec);
        payload.push(item);
      }
      const result = await api.syncBatch("device-001", payload);
      for (const rec of pending) await markSynced(rec.id);
      out.textContent = JSON.stringify(result, null, 2);
    } catch (e) { out.textContent = "Sync error: " + e.message; }
  };
}

init();