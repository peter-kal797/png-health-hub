# PNG Cross-Hospital Digital Health Record Hub

Offline-first, SMS-interactive clinical record platform for Papua New Guinea.
Connects urban hospitals (4G/5G web portal) with zero-data rural Community
Health Posts (SMS + PWA). Compliant with NICTA directives and the PNG
Data Governance & Protection Bill.

## Stack
- Backend: FastAPI + Async SQLAlchemy + PostgreSQL 16
- Edge: Progressive Web App (IndexedDB + AES-256-GCM via WebCrypto)
- SMS: Structured GSM command parser with AES-GCM PSK envelope
- Auth: JWT (RS256-ready, HS256 dev default) with RBAC