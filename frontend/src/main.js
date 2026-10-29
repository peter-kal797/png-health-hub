import { api, setToken, clearToken, isOnline } from "./api.js";
import { getDeviceKey } from "./crypto.js";
import { cachePatient, getCachedPatient, queueEncounter, listPending, markSynced, decryptQueueItem } from "./db.js";

let deviceKey = null;
let currentPatient = null;

const $ = (s) => document.querySelector(s);
const toast = (msg) => {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 3000);
};

async function checkQueue() {
  const pending = await listPending();
  const badge = $("#sync-badge");
  const count = $("#sync-count");
  if (pending.length > 0) {
    count.textContent = pending.length;
    badge.classList.remove("hidden");
  } else {
    badge.classList.add("hidden");
  }
}

async function flushQueue() {
  const pending = await listPending();
  if (!pending.length) return;
  toast("Syncing offline records...");
  
  try {
    const payload = [];
    for (const rec of pending) {
      const item = await decryptQueueItem(deviceKey, rec);
      payload.push(item);
    }
    for (const item of payload) {
       await api.createEncounter(item);
    }
    for (const rec of pending) await markSynced(rec.id);
    toast("Offline records synced successfully!");
    checkQueue();
    if (currentPatient) loadHistory(currentPatient.patient_id);
  } catch (e) {
    toast("Sync failed: " + e.message);
  }
}

async function init() {
  deviceKey = await getDeviceKey("123456");
  
  // Sync Badge Logic
  $("#sync-badge").onclick = flushQueue;
  checkQueue();
  window.addEventListener('online', () => { toast("Connection restored!"); checkQueue(); });
  window.addEventListener('offline', () => { toast("Connection lost. Working offline."); });

  // Login
  $("#btn-login").onclick = async () => {
    try {
      const res = await api.login($("#username").value, $("#password").value);
      setToken(res.access_token, res.facility);
      $("#login-view").classList.add("hidden");
      $("#app-view").classList.remove("hidden");
      $("#user-badge").textContent = res.full_name;
      toast("Authenticated successfully");
    } catch (e) { $("#login-status").textContent = "Login failed: " + e.message; $("#login-status").style.color = "#ef4444"; }
  };

  $("#btn-logout").onclick = () => { clearToken(); location.reload(); };

  // Search
  $("#btn-search").onclick = async () => {
    const q = $("#search-input").value.trim();
    if (!q) return;
    try {
      const results = await api.searchPatients(q);
      const list = $("#patient-list");
      list.innerHTML = "";
      if (!results.length) { list.innerHTML = '<div style="padding: 16px; text-align: center; color: #94a3b8;">No patients found.</div>'; return; }
      
      results.forEach(p => {
        const div = document.createElement("div");
        div.className = "patient-item";
        div.innerHTML = `<div class="name">${p.first_name} ${p.last_name}</div><div class="id">${p.patient_id}</div>`;
        div.onclick = () => selectPatient(p);
        list.appendChild(div);
      });
    } catch (e) { toast("Search failed: " + e.message); }
  };

  // Register Form Toggle
  $("#btn-show-register").onclick = () => {
    $("#empty-state").classList.add("hidden");
    $("#patient-details").classList.add("hidden");
    $("#register-form").classList.remove("hidden");
  };

  // Save Patient
  $("#btn-save-patient").onclick = async () => {
    const body = {
      patient_id: $("#reg-id").value,
      date_of_birth: $("#reg-dob").value,
      first_name: $("#reg-fname").value,
      last_name: $("#reg-lname").value,
      gender: $("#reg-gender").value,
      blood_type: $("#reg-blood").value,
      home_province: $("#reg-province").value,
      severe_allergies: $("#reg-allergies").value || "NONE"
    };
    try {
      await api.registerPatient(body);
      toast("Patient registered to National Registry");
      $("#register-form").classList.add("hidden");
      $("#empty-state").classList.remove("hidden");
      $("#search-input").value = body.patient_id;
      $("#btn-search").click();
    } catch (e) { toast("Registration failed: " + e.message); }
  };

  // Save Encounter
  $("#btn-save-encounter").onclick = async () => {
    if (!currentPatient) return;
    const enc = {
      patient_id: currentPatient.patient_id,
      facility_name: "CHW_LOCAL",
      health_worker_id: "device",
      symptoms: $("#enc-symptoms").value,
      diagnosis: $("#enc-diagnosis").value,
      medications_prescribed: $("#enc-meds").value,
      client_event_id: crypto.randomUUID(),
    };
    try {
      if (isOnline()) {
        await api.createEncounter(enc);
        toast("Encounter saved to database");
      } else {
        await queueEncounter(deviceKey, enc);
        toast("Queued offline. Will sync when online.");
      }
      // Clear inputs and reload history
      $("#enc-symptoms").value = ""; $("#enc-diagnosis").value = ""; $("#enc-meds").value = "";
      loadHistory(currentPatient.patient_id);
    } catch (e) { toast("Save failed: " + e.message); }
  };
}

async function selectPatient(patient) {
  currentPatient = patient;
  document.querySelectorAll('.patient-item').forEach(el => el.classList.remove('active'));
  $("#empty-state").classList.add("hidden");
  $("#register-form").classList.add("hidden");
  $("#patient-details").classList.remove("hidden");

  $("#det-name").textContent = `${patient.first_name} ${patient.last_name}`;
  $("#det-id").textContent = patient.patient_id;
  $("#det-dob").textContent = patient.date_of_birth;
  $("#det-blood").textContent = patient.blood_type;

  if (patient.severe_allergies && patient.severe_allergies !== "NONE") {
    $("#allergy-alert").classList.remove("hidden");
    $("#det-allergies").textContent = patient.severe_allergies;
  } else {
    $("#allergy-alert").classList.add("hidden");
  }

  await cachePatient(deviceKey, patient);
  loadHistory(patient.patient_id);
}

async function loadHistory(pid) {
  const timeline = $("#encounter-timeline");
  timeline.innerHTML = '<div style="color: #94a3b8;">Loading history...</div>';
  try {
    if (!isOnline()) throw new Error("offline");
    const history = await api.getHistory(pid);
    timeline.innerHTML = "";
    if (!history.length) { timeline.innerHTML = '<div style="color: #94a3b8;">No prior encounters.</div>'; return; }
    
    history.forEach(h => {
      const date = new Date(h.created_at).toLocaleString();
      timeline.innerHTML += `
        <div class="timeline-item">
          <div class="timeline-date">${date} | ${h.facility_name}</div>
          <div class="timeline-content">
            <strong>Diagnosis:</strong> ${h.diagnosis}<br>
            <strong>Symptoms:</strong> ${h.symptoms}<br>
            <strong>Meds:</strong> ${h.medications_prescribed}
          </div>
        </div>
      `;
    });
  } catch (e) {
    timeline.innerHTML = '<div style="color: #ef4444;">Offline: Cannot fetch full history.</div>';
  }
}

init();