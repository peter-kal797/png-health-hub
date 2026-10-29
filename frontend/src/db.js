import { encryptLocal, decryptLocal } from "./crypto.js";

const DB_NAME = "png_health_hub";
const DB_VERSION = 1;

let _db = null;

export function openDB() {
  if (_db) return Promise.resolve(_db);
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains("patients_cache")) {
        db.createObjectStore("patients_cache", { keyPath: "patient_id" });
      }
      if (!db.objectStoreNames.contains("sync_queue")) {
        const q = db.createObjectStore("sync_queue", { keyPath: "id", autoIncrement: true });
        q.createIndex("by_status", "status", { unique: false });
      }
    };
    req.onsuccess = () => { _db = req.result; resolve(_db); };
    req.onerror = () => reject(req.error);
  });
}

async function tx(storeName, mode, fn) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const t = db.transaction(storeName, mode);
    const store = t.objectStore(storeName);
    const result = fn(store);
    t.oncomplete = () => resolve(result);
    t.onerror = () => reject(t.error);
  });
}

export async function cachePatient(key, patientObj) {
  const encrypted = await encryptLocal(key, JSON.stringify(patientObj));
  const rec = {
    patient_id: patientObj.patient_id,
    cipher: encrypted,
    cached_at: Date.now(),
  };
  await tx("patients_cache", "readwrite", (s) => s.put(rec));
  return rec;
}

export async function getCachedPatient(key, patient_id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const t = db.transaction("patients_cache", "readonly");
    const req = t.objectStore("patients_cache").get(patient_id);
    req.onsuccess = async () => {
      const rec = req.result;
      if (!rec) return resolve(null);
      try {
        const plain = await decryptLocal(key, new Uint8Array(rec.cipher));
        resolve(JSON.parse(plain));
      } catch { resolve(null); }
    };
    req.onerror = () => reject(req.error);
  });
}

export async function purgeStalePatients(maxAgeDays = 7) {
  const cutoff = Date.now() - maxAgeDays * 24 * 60 * 60 * 1000;
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const t = db.transaction("patients_cache", "readwrite");
    const store = t.objectStore("patients_cache");
    const req = store.openCursor();
    let purged = 0;
    req.onsuccess = () => {
      const cursor = req.result;
      if (cursor) {
        if (cursor.value.cached_at < cutoff) { cursor.delete(); purged++; }
        cursor.continue();
      } else {
        resolve(purged);
      }
    };
    req.onerror = () => reject(req.error);
  });
}

export async function queueEncounter(key, encounter) {
  const encrypted = await encryptLocal(key, JSON.stringify(encounter));
  const rec = { cipher: encrypted, status: "pending", created_at: Date.now() };
  await tx("sync_queue", "readwrite", (s) => s.add(rec));
}

export async function listPending() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const t = db.transaction("sync_queue", "readonly");
    const idx = t.objectStore("sync_queue").index("by_status");
    const req = idx.getAll("pending");
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

export async function markSynced(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const t = db.transaction("sync_queue", "readwrite");
    const store = t.objectStore("sync_queue");
    const get = store.get(id);
    get.onsuccess = () => {
      const rec = get.result;
      if (!rec) return;
      rec.status = "synced";
      store.put(rec);
    };
    t.oncomplete = () => resolve();
    t.onerror = () => reject(t.error);
  });
}

export async function decryptQueueItem(key, rec) {
  const plain = await decryptLocal(key, new Uint8Array(rec.cipher));
  return JSON.parse(plain);
}