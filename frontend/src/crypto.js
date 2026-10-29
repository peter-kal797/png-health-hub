const MASTER_PSK = "CHANGE_ME_32_byte_master_secret_for_sms";

function b64urlEncode(bytes) {
  let s = btoa(String.fromCharCode(...new Uint8Array(bytes)));
  return s.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function b64urlDecode(str) {
  const pad = "=".repeat((4 - (str.length % 4)) % 4);
  const s = (str + pad).replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
}

async function sha256(bytes) {
  return new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
}
async function hmacSha256(keyBytes, msgBytes) {
  const key = await crypto.subtle.importKey(
    "raw", keyBytes, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, msgBytes));
}

export async function monthlyPsk(year, month) {
  const master = new TextEncoder().encode(MASTER_PSK);
  const msg = new TextEncoder().encode(`${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}`);
  return hmacSha256(master, msg);
}
export async function currentPsk() {
  const now = new Date();
  return monthlyPsk(now.getUTCFullYear(), now.getUTCMonth() + 1);
}
export async function previousPsk() {
  const now = new Date();
  let y = now.getUTCFullYear(), m = now.getUTCMonth();
  if (m === 0) { y -= 1; m = 12; }
  return monthlyPsk(y, m);
}

export async function encryptSms(plaintext) {
  const key = await currentPsk();
  const k = await crypto.subtle.importKey("raw", key, "AES-GCM", false, ["encrypt"]);
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const ct = new Uint8Array(await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: nonce }, k, new TextEncoder().encode(plaintext)
  ));
  const combined = new Uint8Array(12 + ct.byteLength);
  combined.set(nonce, 0); combined.set(ct, 12);
  return "HLTH ENC " + b64urlEncode(combined);
}

export async function decryptSms(payload) {
  const body = payload.startsWith("HLTH ENC ") ? payload.slice(9) : payload;
  const raw = b64urlDecode(body.trim());
  const nonce = raw.slice(0, 12);
  const ct = raw.slice(12);
  for (const key of [await currentPsk(), await previousPsk()]) {
    try {
      const k = await crypto.subtle.importKey("raw", key, "AES-GCM", false, ["decrypt"]);
      const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: nonce }, k, ct);
      return new TextDecoder().decode(pt);
    } catch {}
  }
  throw new Error("decrypt_failed");
}

const DEVICE_SALT_KEY = "png_hub_device_salt";

export async function getDeviceKey(pin) {
  let saltB64 = localStorage.getItem(DEVICE_SALT_KEY);
  if (!saltB64) {
    const salt = crypto.getRandomValues(new Uint8Array(16));
    saltB64 = b64urlEncode(salt);
    localStorage.setItem(DEVICE_SALT_KEY, saltB64);
  }
  const salt = b64urlDecode(saltB64);
  const baseKey = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(pin), "PBKDF2", false, ["deriveKey"]
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: 200000, hash: "SHA-256" },
    baseKey, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]
  );
}

export async function encryptLocal(key, plaintext) {
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const ct = new Uint8Array(await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: nonce }, key, new TextEncoder().encode(plaintext)
  ));
  const combined = new Uint8Array(12 + ct.byteLength);
  combined.set(nonce, 0); combined.set(ct, 12);
  return combined;
}
export async function decryptLocal(key, bytes) {
  const nonce = bytes.slice(0, 12);
  const ct = bytes.slice(12);
  const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: nonce }, key, ct);
  return new TextDecoder().decode(pt);
}

export { sha256 };