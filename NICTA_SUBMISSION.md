# NICTA Pilot Submission: PNG Cross-Hospital Digital Health Record Hub

## Executive Summary
The PNG Cross-Hospital Digital Health Record Hub is an offline-first, cryptographically secure medical records platform designed to bridge the gap between urban hospitals (with 4G/5G coverage) and rural Community Health Posts (CHPs) with zero data connectivity. 

## Compliance with NICTA Goals
1. **Universal Access Scheme (UAS):** Utilizes AES-256-GCM encrypted GSM/USSD fallback for zero-data areas, allowing health workers to query patient allergies and log diagnoses via standard SMS.
2. **Cybersecurity & Data Sovereignty:** All data is hosted on a local PostgreSQL instance. Edge devices encrypt local caches using hardware-derived PBKDF2 keys. 
3. **Data Governance and Protection Bill:** Includes a cryptographic, hash-chained audit ledger (immutable logs) that records every read/write action with SHA-256 verification.
4. **SevisPass Integration:** Patient IDs are validated against the `PNG-SP-XXXXXX` government format, ready for live SevisPass API bridging.

## Technology Stack
- **Backend:** Python (FastAPI), SQLAlchemy (Async), PostgreSQL 16.
- **Frontend:** HTML5, JavaScript (ES Modules), IndexedDB, WebCrypto API.
- **Interoperability:** HL7 FHIR R4 `Patient` resource endpoint (`/api/v1/fhir/Patient/{id}`) for National Department of Health (NDoH) integration.

## How to Run the Pilot
1. Start the database: `docker compose up -d`
2. Start the backend: `cd backend && .\.venv\Scripts\Activate.ps1 && uvicorn app.main:app --reload --port 8000`
3. Start the frontend: `cd frontend && npm run dev`
4. Access the PWA at `http://127.0.0.1:5173`
5. Login with the Community Health Worker credentials (`chw_demo` / `demo1234`).

## Security Proof
- Hash-chained audit logs are stored in the `audit_logs` table.
- Offline records are secured in the browser via AES-256-GCM. If a tablet is stolen, the records are cryptographically unreadable without the worker's PIN.