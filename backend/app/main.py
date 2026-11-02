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

        if ch == "-" and nxt == "-":
            while i < n and sql[i] != "\n":
                i += 1
            continue

        if ch == "/" and nxt == "*":
            i += 2
            while i + 1 < n and not (sql[i] == "*" and sql[i + 1] == "/"):
                i += 1
            i += 2
            continue

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
    if not MIGRATIONS_DIR.exists():
        logger.warning("Migrations dir %s missing", MIGRATIONS_DIR)
        return {"status": "no_migrations_dir", "files": []}

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    report = {"status": "ok", "files": [], "errors": []}

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        return {"status": "db_unreachable", "error": str(e)}

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
            # Don't break, continue to next file
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
    allow_origins=["*"], # Allow all for now to fix CORS
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
    app.include_router(r.router) # Removed prefix here, assuming routers define their own

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/debug/migrate")
async def debug_migrate():
    try:
        return await _auto_migrate()
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@app.get("/debug/tables")
async def debug_tables():
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