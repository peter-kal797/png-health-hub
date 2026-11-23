import { api, setToken, clearToken, isOnline } from "./api.js";
import { getDeviceKey } from "./crypto.js";
import { cachePatient, queueEncounter, listPending, markSynced, decryptQueueItem } from "./db.js";

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
  if (pending.length > 0) { count.textContent = pending.length; badge.classList.remove("hidden"); }
  else { badge.classList.add("hidden"); }
}

async function flushQueue() {
  const pending = await listPending();
  if (!pending.length) return;
  toast("Syncing...");
  try {
    for (const rec of pending) {
      const item = await decryptQueueItem(deviceKey, rec);
      await api.createEncounter(item);
      await markSynced(rec.id);
    }
    toast("Synced!");
    checkQueue();
    if (currentPatient) loadHistory(currentPatient.patient_id);
  } catch (e) { toast("Sync failed: " + e.message); }
}

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.remove('hidden');
  };
});

function updateNetworkStatus() {
  const el = document.getElementById('network-status');
  if (navigator.onLine) {
    el.innerHTML = '<span style="width: 10px; height: 10px; background: #10b981; border-radius: 50%; display: inline-block;"></span> Online';
    el.style.color = '#10b981';
  } else {
    el.innerHTML = '<span style="width: 10px; height: 10px; background: #ef4444; border-radius: 50%; display: inline-block;"></span> Offline';
    el.style.color = '#ef4444';
  }
}
updateNetworkStatus();
window.addEventListener('online', updateNetworkStatus);
window.addEventListener('offline', updateNetworkStatus);

async function init() {
  deviceKey = await getDeviceKey("123456");
  $("#sync-badge").onclick = flushQueue;
  checkQueue();

  $("#btn-login").onclick = async () => {
    try {
      const res = await api.login($("#username").value, $("#password").value);
      setToken(res.access_token, res.facility);
      $("#login-view").classList.add("hidden");
      $("#app-view").classList.remove("hidden");
      $("#user-badge").textContent = res.full_name;
      toast("Authenticated");
    } catch (e) { $("#login-status").textContent = "Login failed: " + e.message; }
  };

  $("#btn-logout").onclick = () => { clearToken(); location.reload(); };

  $("#btn-search").onclick = async () => {
    const q = $("#search-input").value.trim();
    if (!q) return;
    try {
      const results = await api.searchPatients(q);
      const list = $("#patient-list");
      list.innerHTML = "";
      if (!results.length) { list.innerHTML = '<div style="padding:16px;text-align:center;color:#94a3b8;">No patients found.</div>'; return; }
      results.forEach(p => {
        const div = document.createElement("div");
        div.className = "patient-item";
        div.innerHTML = '<div class="name">' + p.first_name + ' ' + p.last_name + '</div><div class="id">' + p.patient_id + '</div>';
        div.onclick = () => selectPatient(p);
        list.appendChild(div);
      });
    } catch (e) { toast("Search failed: " + e.message); }
  };

  // UPDATED DIAGNOSIS SEARCH
  $("#btn-diag-search").onclick = async () => {
    const q = $("#diag-search").value.trim();
    if (!q) return;
    try {
      const results = await api.searchDiagnoses(q);
      const list = $("#patient-list");
      list.innerHTML = "";
      if (!results.length) { 
        list.innerHTML = '<div style="padding:16px;text-align:center;color:#94a3b8;">No encounters found matching that diagnosis.</div>'; 
        return; 
      }
      results.forEach(r => {
        const div = document.createElement("div");
        div.className = "patient-item";
        div.innerHTML = '<div class="name">' + r.diagnosis + '</div><div class="id">Patient: ' + r.patient_id + ' @ ' + r.facility + '</div>';
        div.onclick = async () => {
          try {
            const patient = await api.getPatient(r.patient_id);
            selectPatient(patient);
          } catch (e) {
            toast("Failed to load patient: " + e.message);
          }
        };
        list.appendChild(div);
      });
    } catch (e) { toast("Search failed: " + e.message); }
  };

  let html5QrCode = null;
  $("#btn-scan").onclick = async () => {
    const modal = document.getElementById("scanner-modal");
    modal.style.display = "block";
    if (!html5QrCode) html5QrCode = new Html5Qrcode("qr-reader");
    try {
      await html5QrCode.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        async (decodedText) => {
          await html5QrCode.stop();
          modal.style.display = "none";
          if (decodedText.startsWith("PNG-SP-")) {
            $("#search-input").value = decodedText;
            $("#btn-search").click();
          } else { toast("Invalid QR Code"); }
        },
        () => {}
      );
    } catch (err) {
      toast("Camera error: " + err.message);
      modal.style.display = "none";
    }
  };
  $("#btn-close-scanner").onclick = async () => {
    if (html5QrCode && html5QrCode.isScanning) await html5QrCode.stop();
    document.getElementById("scanner-modal").style.display = "none";
  };

  $("#btn-show-register").onclick = () => {
    document.getElementById("registerModal").style.display = "flex";
  };

  $("#btnSavePatient").onclick = async () => {
    const fName = document.getElementById("regFirstName").value;
    const lName = document.getElementById("regLastName").value;
    const dob = document.getElementById("regDob").value;
    const gender = document.getElementById("regGender").value;
    const province = document.getElementById("regProvince").value;
    const blood = document.getElementById("regBlood").value;
    const allergies = document.getElementById("regAllergies").value || 'None';

    if (!fName || !lName || !dob) {
        alert("First Name, Last Name, and Date of Birth are required!");
        return;
    }

    const randomNum = Math.floor(Math.random() * 900000) + 100000;
    const patientId = `PNG-SP-${randomNum}`;

    try {
        await api.registerPatient({
            patient_id: patientId,
            first_name: fName,
            last_name: lName,
            date_of_birth: dob,
            gender: gender,
            home_province: province,
            blood_type: blood,
            severe_allergies: allergies
        });
        
        alert(`Patient Registered Successfully! ID: ${patientId}`);
        document.getElementById('registerModal').style.display = 'none';
        document.getElementById('regFirstName').value = '';
        document.getElementById('regLastName').value = '';
        document.getElementById('regDob').value = '';
        
        $("#search-input").value = patientId;
        $("#btn-search").click();
    } catch (e) {
        console.error(e);
        alert(`Error: ${e.message || 'Failed to register patient'}`);
    }
  };

  $("#btn-save-encounter").onclick = async () => {
    if (!currentPatient) return;
    const enc = {
      patient_id: currentPatient.patient_id, facility_name: "CHW_LOCAL", health_worker_id: "device",
      symptoms: $("#enc-symptoms").value, diagnosis: $("#enc-diagnosis").value,
      medications_prescribed: $("#enc-meds").value, blood_pressure: $("#enc-bp").value || null,
      temperature: $("#enc-temp").value || null, heart_rate: $("#enc-hr").value || null,
      weight: $("#enc-weight").value || null, client_event_id: crypto.randomUUID()
    };
    try {
      if (isOnline()) { await api.createEncounter(enc); toast("Saved!"); }
      else { await queueEncounter(deviceKey, enc); toast("Queued offline"); }
      $("#enc-symptoms").value = ""; $("#enc-diagnosis").value = ""; $("#enc-meds").value = "";
      loadHistory(currentPatient.patient_id);
    } catch (e) { toast("Failed: " + e.message); }
  };

  $("#btn-save-vax").onclick = async () => {
    if (!currentPatient) return;
    const body = {
      patient_id: currentPatient.patient_id, vaccine_name: $("#vax-name").value,
      dose_number: $("#vax-dose").value, date_administered: $("#vax-date").value,
      administered_by: $("#vax-by").value
    };
    try { await api.addVaccination(body); toast("Saved!"); loadVaccines(currentPatient.patient_id); }
    catch (e) { toast("Failed: " + e.message); }
  };

  $("#btn-save-maternal").onclick = async () => {
    if (!currentPatient) return;
    const body = {
      patient_id: currentPatient.patient_id, visit_date: $("#mat-date").value,
      gestational_age_weeks: $("#mat-age").value ? parseInt($("#mat-age").value) : null,
      blood_pressure: $("#mat-bp").value, weight: $("#mat-weight").value,
      fetal_heart_rate: $("#mat-fhr").value, notes: $("#mat-notes").value
    };
    try { await api.addMaternal(body); toast("Saved!"); loadMaternal(currentPatient.patient_id); }
    catch (e) { toast("Failed: " + e.message); }
  };

  $("#btn-add-inventory").onclick = async () => {
    const body = {
      drug_name: $("#inv-name").value, quantity: parseInt($("#inv-qty").value),
      unit: $("#inv-unit").value, facility_name: $("#inv-facility").value
    };
    try { await api.addInventory(body); toast("Inventory added"); loadInventory(); }
    catch (e) { toast("Failed: " + e.message); }
  };

  $("#btn-add-bill").onclick = async () => {
    if (!currentPatient) return;
    const amt = parseFloat($("#bill-amount").value);
    if (isNaN(amt) || amt <= 0) { toast("Enter a valid amount"); return; }
    const body = {
      patient_id: currentPatient.patient_id,
      description: $("#bill-desc").value || "Consultation",
      amount: amt
    };
    try {
      await api.addBill(body);
      toast("Bill added");
      $("#bill-desc").value = ""; $("#bill-amount").value = "";
      loadBills(currentPatient.patient_id);
    } catch (e) { toast("Failed: " + e.message); }
  };

  $("#btn-print-bill").onclick = async () => {
    if (!currentPatient) return;
    try {
      const res = await api.printBill(currentPatient.patient_id);
      const w = window.open("", "_blank");
      w.document.write(res.html); w.document.close(); w.print();
    } catch (e) { toast("Failed: " + e.message); }
  };

  $("#btn-create-referral").onclick = async () => {
    if (!currentPatient) { toast("Select a patient first."); return; }
    const body = {
      patient_id: currentPatient.patient_id,
      from_facility: $("#ref-from").value,
      to_facility: $("#ref-to").value,
      reason: $("#ref-reason").value
    };
    try {
      await api.createReferral(body);
      toast("Referral created");
      $("#ref-reason").value = "";
      loadInboundReferrals();
    } catch (e) { toast("Failed: " + e.message); }
  };

  $("#guide-search").oninput = async (e) => {
    const q = e.target.value.trim();
    try {
      const guides = q ? await api.searchGuidelines(q) : await api.listGuidelines();
      document.getElementById("guidelines-list").innerHTML = guides.length
        ? guides.map(g => '<div style="padding:12px;border-bottom:1px solid #334155;"><div style="color:#0ea5e9;font-weight:bold;">' + g.title + '</div><div style="font-size:12px;color:#94a3b8;">' + g.category + '</div><div style="margin-top:8px;">' + g.content + '</div></div>').join('')
        : '<div style="color:#94a3b8;">No results.</div>';
    } catch (e) { console.error(e); }
  };

  $("#btn-qr").onclick = () => {
    if (!currentPatient) return;
    const modal = document.getElementById("qr-modal");
    modal.innerHTML = '<div id="qr-canvas"></div><button id="qr-close" style="margin-top:16px; background:#ef4444; color:white;">Close</button>';
    modal.style.display = "block";
    new QRCode(document.getElementById("qr-canvas"), { text: currentPatient.patient_id, width: 200, height: 200 });
    document.getElementById("qr-close").onclick = () => modal.style.display = "none";
  };

  $("#btn-print").onclick = async () => {
    if (!currentPatient) return;
    try {
      const report = await api.getFullReport(currentPatient.patient_id);
      const printWindow = window.open("", "_blank");
      const encRows = report.encounters.map(e => '<tr><td>' + e.date.substring(0,10) + '</td><td>' + e.facility + '</td><td>' + e.diagnosis + '</td></tr>').join('');
      const vaxRows = report.vaccines.map(v => '<tr><td>' + v.date + '</td><td>' + v.name + '</td><td>' + v.dose + '</td></tr>').join('');
      printWindow.document.write('<html><head><title>Report</title><style>body{font-family:sans-serif;padding:40px;}h1{color:#0ea5e9;}table{width:100%;border-collapse:collapse;}th,td{padding:8px;border-bottom:1px solid #eee;text-align:left;}.allergy{color:#ef4444;border:1px solid #ef4444;padding:8px;}</style></head><body><h1>Patient Report</h1><p><strong>Name:</strong> ' + report.patient.name + '</p><p><strong>ID:</strong> ' + report.patient.patient_id + '</p><p><strong>DOB:</strong> ' + report.patient.dob + '</p><p class="allergy">ALLERGY: ' + report.patient.allergies + '</p><h2>Encounters</h2><table><tr><th>Date</th><th>Facility</th><th>Diagnosis</th></tr>' + encRows + '</table><h2>Vaccinations</h2><table><tr><th>Date</th><th>Vaccine</th><th>Dose</th></tr>' + vaxRows + '</table></body></html>');
      printWindow.document.close(); printWindow.print();
    } catch (e) { toast("Failed: " + e.message); }
  };
}

async function loadInboundReferrals() {
  try {
    const facility = document.getElementById("ref-to").value;
    const refs = await api.listInbound(facility);
    const container = document.getElementById("inbound-list");
    if (!refs.length) { container.innerHTML = '<div style="color:#94a3b8;">No pending referrals.</div>'; return; }
    container.innerHTML = refs.map(r => '<div style="padding:12px;border-bottom:1px solid #334155;"><strong>' + r.patient_id + '</strong> - ' + r.reason + '<br><span style="color:#94a3b8;">From: ' + r.from_facility + '</span><button onclick="acceptReferral(\'' + r.id + '\')" style="width:auto;margin-top:8px;padding:6px 12px;background:#10b981;color:white;font-size:12px;">Accept</button></div>').join('');
  } catch (e) { console.error(e); }
}

window.acceptReferral = async function(id) {
  try {
    await api.acceptReferral(id);
    toast("Referral accepted!");
    loadInboundReferrals();
  } catch (e) { toast("Failed: " + e.message); }
};

async function loadGuidelines() {
  try {
    const guides = await api.listGuidelines();
    document.getElementById("guidelines-list").innerHTML = guides.length
      ? guides.map(g => '<div style="padding:12px;border-bottom:1px solid #334155;"><div style="color:#0ea5e9;font-weight:bold;">' + g.title + '</div><div style="font-size:12px;color:#94a3b8;">' + g.category + '</div><div style="margin-top:8px;">' + g.content + '</div></div>').join('')
      : '<div style="color:#94a3b8;">No guidelines loaded.</div>';
  } catch (e) { console.error(e); }
}

async function loadInventory() {
  try {
    const items = await api.listInventory();
    document.getElementById("inventory-list").innerHTML = items.length ? items.map(i => '<div style="display:flex;justify-content:space-between;padding:8px;border-bottom:1px solid #334155;"><span>' + i.drug_name + '</span><span>' + i.quantity + ' ' + i.unit + '</span></div>').join('') : '<div style="color:#94a3b8;">No inventory recorded.</div>';
    checkLowStock();
  } catch (e) { console.error(e); }
}

async function checkLowStock() {
  try {
    const items = await api.lowStock();
    const alert = document.getElementById("low-stock-alert");
    const list = document.getElementById("low-stock-list");
    if (!items.length) { alert.style.display = "none"; return; }
    alert.style.display = "block";
    list.innerHTML = items.map(i => i.drug_name + ' (' + i.quantity + ' ' + i.unit + ')').join(", ");
  } catch (e) { console.error(e); }
}

async function loadBills(pid) {
  try {
    const bills = await api.listBills(pid);
    document.getElementById("bills-list").innerHTML = bills.length ? bills.map(b => '<div style="display:flex;justify-content:space-between;padding:8px;border-bottom:1px solid #334155;"><span>' + b.description + '</span><span>PGK ' + parseFloat(b.amount).toFixed(2) + '</span></div>').join('') : '<div style="color:#94a3b8;">No bills recorded.</div>';
  } catch (e) { console.error(e); }
}

async function loadVaccines(pid) {
  const timeline = $("#vax-timeline");
  timeline.innerHTML = '<div style="color:#94a3b8;">Loading...</div>';
  try {
    const history = await api.listVaccinations(pid);
    timeline.innerHTML = history.length ? history.map(v => '<div class="timeline-item"><div class="timeline-date">' + v.date_administered + '</div><div class="timeline-content"><strong>' + v.vaccine_name + '</strong> (Dose ' + (v.dose_number || '-') + ')<br>' + (v.administered_by || '') + '</div></div>').join('') : '<div style="color:#94a3b8;">None.</div>';
  } catch (e) { timeline.innerHTML = '<div style="color:#ef4444;">Failed.</div>'; }
}

async function loadMaternal(pid) {
  const timeline = $("#mat-timeline");
  timeline.innerHTML = '<div style="color:#94a3b8;">Loading...</div>';
  try {
    const history = await api.listMaternal(pid);
    timeline.innerHTML = history.length ? history.map(m => '<div class="timeline-item"><div class="timeline-date">' + m.visit_date + '</div><div class="timeline-content">Weeks: ' + (m.gestational_age_weeks || '-') + ' | BP: ' + (m.blood_pressure || '-') + ' | Weight: ' + (m.weight || '-') + '<br>' + (m.notes || '') + '</div></div>').join('') : '<div style="color:#94a3b8;">None.</div>';
  } catch (e) { timeline.innerHTML = '<div style="color:#ef4444;">Failed.</div>'; }
}

async function selectPatient(patient) {
  currentPatient = patient;
  document.querySelectorAll('.patient-item').forEach(el => el.classList.remove('active'));
  $("#empty-state").classList.add("hidden");
  $("#patient-details").classList.remove("hidden");
  $("#det-name").textContent = patient.first_name + " " + patient.last_name;
  $("#det-id").textContent = patient.patient_id;
  $("#det-dob").textContent = patient.date_of_birth;
  $("#det-blood").textContent = patient.blood_type;
  if (patient.severe_allergies && patient.severe_allergies !== "NONE") {
    $("#allergy-alert").classList.remove("hidden");
    $("#det-allergies").textContent = patient.severe_allergies;
  } else { $("#allergy-alert").classList.add("hidden"); }
  
  await cachePatient(deviceKey, patient);
  
  try { loadHistory(patient.patient_id); } catch (e) { console.error(e); }
  try { loadVaccines(patient.patient_id); } catch (e) { console.error(e); }
  try { loadMaternal(patient.patient_id); } catch (e) { console.error(e); }
  try { loadInventory(); } catch (e) { console.error(e); }
  try { loadBills(patient.patient_id); } catch (e) { console.error(e); }
  try { loadInboundReferrals(); } catch (e) { console.error(e); }
  try { loadGuidelines(); } catch (e) { console.error(e); }
  try { loadDashboard(); } catch (e) { console.error(e); }
}

async function loadHistory(pid) {
  const timeline = $("#encounter-timeline");
  timeline.innerHTML = '<div style="color:#94a3b8;">Loading...</div>';
  try {
    const history = await api.getHistory(pid);
    timeline.innerHTML = history.length ? history.map(h => '<div class="timeline-item"><div class="timeline-date">' + new Date(h.created_at).toLocaleString() + ' - ' + h.facility_name + '</div><div class="timeline-content"><strong>Dx:</strong> ' + h.diagnosis + '<br><strong>Sx:</strong> ' + h.symptoms + '<br><strong>Rx:</strong> ' + h.medications_prescribed + (h.blood_pressure ? '<br>BP: ' + h.blood_pressure : '') + (h.temperature ? ' | Temp: ' + h.temperature : '') + (h.heart_rate ? ' | HR: ' + h.heart_rate : '') + (h.weight ? ' | Wt: ' + h.weight : '') + '</div></div>').join('') : '<div style="color:#94a3b8;">No prior encounters.</div>';
  } catch (e) { timeline.innerHTML = '<div style="color:#ef4444;">Failed.</div>'; }
}
async function loadDashboard() {
  try {
    const data = await api.getAnalytics();
    
    document.getElementById("stat-patients").textContent = data.total_patients || 0;
    document.getElementById("stat-encounters").textContent = data.total_encounters || 0;
    
    const diagContainer = document.getElementById("stat-diagnoses");
    if (data.top_diagnoses && data.top_diagnoses.length) {
      diagContainer.innerHTML = data.top_diagnoses.map(d => 
        `<div style="display:flex; justify-content:space-between; padding: 12px; border-bottom: 1px solid #334155;">
          <span>${d.diagnosis}</span>
          <strong style="color:#0ea5e9;">${d.count} cases</strong>
        </div>`
      ).join('');
    } else {
      diagContainer.innerHTML = '<div style="color:#94a3b8;">No diagnosis data yet.</div>';
    }
  } catch (e) {
    console.warn("Could not load analytics:", e.message);
    document.getElementById("stat-patients").textContent = "-";
    document.getElementById("stat-encounters").textContent = "-";
    document.getElementById("stat-diagnoses").innerHTML = '<div style="color:#94a3b8;">Failed to load analytics. Check connection.</div>';
  }
}

init();