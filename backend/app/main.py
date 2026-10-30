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

# ============================================================
# AUTO-MIGRATE + DIAGNOSTIC
# ============================================================
def _split_sql_statements(sql: str) -> list[str]:
    """Split a multi-statement SQL file into individual commands."""
    import re as _re
    # Strip full-line comments
    lines = []
    for line in sql.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)

    # Split on ; followed by optional whitespace + newline OR end of string
    parts = _re.split(r";\s*(?:\n|$)", cleaned)
    return [p.strip() for p in parts if p.strip()]


async def _run_migrations(log_errors: bool = True) -> list[dict]:
    import pathlib
    from .database import engine
    from sqlalchemy import text

    migrations_dir = pathlib.Path(__file__).parent.parent / "migrations"
    results: list[dict] = []

    if not migrations_dir.exists():
        log.warning("No migrations directory found at %s", migrations_dir)
        return results

    async with engine.begin() as conn:
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            statements = _split_sql_statements(sql_file.read_text(encoding="utf-8"))
            ok = 0
            failed = 0
            first_error: str | None = None
            for stmt in statements:
                try:
                    await conn.execute(text(stmt))
                    ok += 1
                except Exception as e:
                    failed += 1
                    if first_error is None:
                        first_error = str(e)[:300]
                    if log_errors:
                        log.warning("Statement failed in %s: %s", sql_file.name, str(e)[:150])
            results.append({
                "file": sql_file.name,
                "statements": len(statements),
                "ok": ok,
                "failed": failed,
                "first_error": first_error,
            })
    return results


@app.on_event("startup")
async def _auto_migrate():
    log.info("Applying migrations...")
    try:
        res = await _run_migrations(log_errors=False)
        for r in res:
            log.info("  %s: %d ok, %d failed", r["file"], r["ok"], r["failed"])
        log.info("Auto-migrate complete.")
    except Exception as e:
        log.error("Auto-migrate failed: %s", e)


@app.get("/debug/migrate")
async def debug_migrate():
    res = await _run_migrations(log_errors=True)
    return {"migrations": res}