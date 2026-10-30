import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .routers import (
    auth_router, encounters_router, patients_router, sync_router,
    fhir_router, analytics_router, facilities_router, clinical_router,
    reports_router, operations_router, referrals_router, dhis2_router,
    supply_chain_router, guidelines_router, surveillance_router,
)
from .sms.parser import handle_sms

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("hub")

app = FastAPI(
    title="PNG Cross-Hospital Digital Health Record Hub",
    version="0.1.0",
    description="Offline-first clinical records with SMS edge for rural CHPs.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(patients_router.router)
app.include_router(encounters_router.router)
app.include_router(sync_router.router)
app.include_router(fhir_router.router)
app.include_router(analytics_router.router)
app.include_router(facilities_router.router)
app.include_router(clinical_router.router)
app.include_router(reports_router.router)
app.include_router(operations_router.router)
app.include_router(referrals_router.router)
app.include_router(dhis2_router.router)
app.include_router(supply_chain_router.router)
app.include_router(guidelines_router.router)
app.include_router(surveillance_router.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "png-health-hub"}

class InboundSMS(BaseModel):
    from_: str
    text: str
    model_config = {"populate_by_name": True, "alias_generator": lambda s: "from" if s == "from_" else s}

@app.post("/api/v1/sms/inbound")
async def sms_inbound(body: InboundSMS, db: AsyncSession = Depends(get_db)):
    reply = await handle_sms(db, sender=body.from_, raw_text=body.text)
    log.info("SMS from %s -> %s", body.from_, reply[:60])
    return {"reply": reply}
# ---------- AUTO-MIGRATE ON STARTUP ----------
@app.on_event("startup")
async def _auto_migrate():
    """Run SQL migrations on boot. Idempotent — safe to run on every deploy."""
    import pathlib
    from .database import engine
    from sqlalchemy import text

    migrations_dir = pathlib.Path(__file__).parent.parent / "migrations"
    if not migrations_dir.exists():
        log.warning("No migrations directory found")
        return

    async with engine.begin() as conn:
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            log.info("Applying migration: %s", sql_file.name)
            sql = sql_file.read_text(encoding="utf-8")
            # Split on semicolons that are followed by a newline + non-whitespace
            for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
                try:
                    await conn.execute(text(stmt))
                except Exception as e:
                    log.warning("Migration stmt skipped (%s): %s", sql_file.name, str(e)[:100])
    log.info("Auto-migrate complete.")
# ---------- DIAGNOSTIC MIGRATION ENDPOINT ----------
@app.get("/debug/migrate")
async def debug_migrate():
    """Run migrations and return the actual error, if any."""
    import pathlib
    from .database import engine
    from sqlalchemy import text

    migrations_dir = pathlib.Path(__file__).parent.parent / "migrations"
    results = []

    async with engine.begin() as conn:
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            sql = sql_file.read_text(encoding="utf-8")
            try:
                # Execute the whole file as one block (Postgres handles multi-statement)
                await conn.execute(text(sql))
                results.append({"file": sql_file.name, "status": "OK"})
            except Exception as e:
                results.append({"file": sql_file.name, "status": "ERROR", "error": str(e)[:300]})

    return {"migrations": results}