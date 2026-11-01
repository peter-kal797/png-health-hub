# backend/app/main.py
import asyncio
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine, AsyncSessionLocal
from app.routers import (
    auth_router, clinical_router, encounters_router, facilities_router,
    fhir_router, operations_router, patients_router, reports_router,
    sync_router, analytics_router, referrals_router, dhis2_router,
    supply_chain_router, guidelines_router, surveillance_router,
)

logger = logging.getLogger("png_hub")
logging.basicConfig(level=getattr(settings, "LOG_LEVEL", "INFO"))

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def split_sql_statements(sql: str) -> list[str]:
    """
    Split a SQL script into individual statements.

    Handles:
      - line comments (-- ...)
      - block comments (/* ... */)
      - single-quoted strings with '' escapes
      - dollar-quoted strings ($$ ... $$, $tag$ ... $tag$)
      - semicolons only at statement boundaries
    """
    statements: list[str] = []
    buf: list[str] = []
    i, n = 0, len(sql)

    def flush():
        stmt = "".join(buf).strip()
        if stmt and not re.fullmatch(r"[;\s]*", stmt):
            statements.append(stmt)
        buf.clear()

    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""

        # Line comment
        if ch == "-" and nxt == "-":
            while i < n and sql[i] != "\n":
                i += 1
            continue

        # Block comment
        if ch == "/" and nxt == "*":
            i += 2
            while i + 1 < n and not (sql[i] == "*" and sql[i + 1] == "/"):
                i += 1
            i += 2
            continue

        # Single-quoted string
        if ch == "'":
            buf.append(ch)
            i += 1
            while i < n:
                buf.append(sql[i])
                if sql[i] == "'" and i + 1 < n and sql[i + 1] == "'":
                    buf.append(sql[i + 1])
                    i += 2
                    continue
                if sql[i] == "'":
                    i += 1
                    break
                i += 1
            continue

        # Dollar-quoted string ($tag$ ... $tag$)
        if ch == "$":
            m = re.match(r"\$[A-Za-z_]*\$", sql[i:])
            if m:
                tag = m.group(0)
                buf.append(tag)
                i += len(tag)
                end = sql.find(tag, i)
                if end == -1:
                    buf.append(sql[i:])
                    i = n
                else:
                    buf.append(sql[i:end + len(tag)])
                    i = end + len(tag)
                continue

        # Statement boundary
        if ch == ";":
            flush()
            i += 1
            continue

        buf.append(ch)
        i += 1

    flush()
    return statements


async def run_migration_file(session: AsyncSession, path: Path) -> int:
    sql = path.read_text(encoding="utf-8")
    stmts = split_sql_statements(sql)
    executed = 0
    for idx, stmt in enumerate(stmts, start=1):
        try:
            await session.execute(text(stmt))
            await session.commit()
            executed += 1
        except Exception as e:
            await session.rollback()
            logger.error(
                "Migration %s stmt #%d failed: %s\n--- SQL ---\n%s\n-----------",
                path.name, idx, e, stmt[:500],
            )
            raise
    return executed


async def _auto_migrate() -> dict:
    """Run every .sql file in migrations/ in lexicographic order."""
    if not MIGRATIONS_DIR.exists():
        logger.warning("Migrations dir %s missing", MIGRATIONS_DIR)
        return {"status": "no_migrations_dir", "files": []}

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    report = {"status": "ok", "files": [], "errors": []}

    # Verify connectivity once
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))

    for f in files:
        try:
            async with AsyncSessionLocal() as session:
                count = await run_migration_file(session, f)
            report["files"].append({"file": f.name, "statements": count})
            logger.info("✓ %s (%d statements)", f.name, count)
        except Exception as e:
            report["status"] = "failed"
            report["errors"].append({"file": f.name, "error": str(e)})
            logger.exception("✗ %s", f.name)
            break
    return report


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Booting PNG Health Hub — running auto-migrations")
    try:
        await _auto_migrate()
    except Exception:
        logger.exception("Auto-migration failed; app will still start")
    yield
    await engine.dispose()


app = FastAPI(title="PNG Health Hub", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    auth_router, patients_router, encounters_router, clinical_router,
    facilities_router, reports_router, operations_router, sync_router,
    fhir_router, analytics_router, referrals_router, dhis2_router,
    supply_chain_router, guidelines_router, surveillance_router,
):
    app.include_router(r.router, prefix="")

# ---- SMS webhook (kept at /api/v1/sms/inbound) ----
# from app.routers import sms_router  # noqa: E402
# app.include_router(sms_router.router, prefix="")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/migrate")
async def debug_migrate():
    """Re-run migrations on demand and report per-file results."""
    try:
        return await _auto_migrate()
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.get("/debug/tables")
async def debug_tables():
    """List all tables in the public schema with row counts."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        ))
        tables = [r[0] for r in res.all()]
        counts = {}
        for t in tables:
            try:
                c = await session.execute(text(f'SELECT count(*) FROM "{t}"'))
                counts[t] = c.scalar()
            except Exception:
                counts[t] = "ERR"
        return {"tables": tables, "counts": counts}
