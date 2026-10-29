import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog

GENESIS_HASH = "0" * 64


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


async def write_audit(
    db: AsyncSession,
    *,
    event_type: str,
    operator_id: str,
    target_patient: str | None,
    facility: str | None,
    channel: str,
    payload: dict,
) -> AuditLog:
    last_q = await db.execute(
        select(AuditLog).order_by(AuditLog.log_id.desc()).limit(1).with_for_update()
    )
    last = last_q.scalar_one_or_none()
    prev_hash = last.chain_hash if last else GENESIS_HASH

    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_hash = _sha256_hex(canonical)
    chain_hash = _sha256_hex(prev_hash + canonical + payload_hash)

    entry = AuditLog(
        timestamp=datetime.now(timezone.utc),
        event_type=event_type,
        operator_id=operator_id,
        target_patient=target_patient,
        facility=facility,
        channel=channel,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
        chain_hash=chain_hash,
    )
    db.add(entry)
    await db.flush()
    return entry