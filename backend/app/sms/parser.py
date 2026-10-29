import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Encounter, Patient
from ..security.audit import write_audit
from ..security.sms_crypto import PREFIX as ENC_PREFIX, decrypt_sms

log = logging.getLogger("sms")

RE_ALGY = re.compile(r"^HLTH\s+ALGY\s+(?P<pid>[\w\-]+)\s*$", re.IGNORECASE)
RE_DIAG = re.compile(r"^HLTH\s+DIAG\s+(?P<pid>[\w\-]+)\s*$", re.IGNORECASE)
RE_LOG = re.compile(
    r"^HLTH\s+LOG\s+(?P<pid>[\w\-]+)#(?P<diag>[^#]+)#(?P<meds>[^#]+)\s*$",
    re.IGNORECASE,
)

SMS_MAX = 300


def _truncate(msg: str) -> str:
    return msg if len(msg) <= SMS_MAX else msg[: SMS_MAX - 3] + "..."


async def handle_sms(db: AsyncSession, sender: str, raw_text: str) -> str:
    text = raw_text.strip()

    channel = "SMS_PLAIN"
    if text.upper().startswith(ENC_PREFIX.strip()):
        try:
            text = decrypt_sms(text)
            channel = "SMS_ENCRYPTED"
        except ValueError:
            await write_audit(
                db,
                event_type="SMS_DECRYPT_FAIL",
                operator_id=sender,
                target_patient=None,
                facility=None,
                channel="SMS_ENCRYPTED",
                payload={"from": sender, "raw_len": len(raw_text)},
            )
            await db.commit()
            return _truncate("ERROR: unable to decrypt. Check device PSK.")
    elif re.fullmatch(r"[A-Za-z0-9_\-]{40,}", text):
        try:
            text = decrypt_sms(text)
            channel = "SMS_ENCRYPTED"
        except ValueError:
            pass

    m = None
    if m := RE_ALGY.match(text):
        reply = await _cmd_algy(db, m["pid"])
    elif m := RE_DIAG.match(text):
        reply = await _cmd_diag(db, m["pid"])
    elif m := RE_LOG.match(text):
        reply = await _cmd_log(db, m["pid"], m["diag"].strip(), m["meds"].strip(), sender)
    else:
        reply = "ERROR: Unknown syntax. Use HLTH ALGY|DIAG|LOG."

    await write_audit(
        db,
        event_type="SMS_COMMAND",
        operator_id=sender,
        target_patient=(m["pid"] if m else None),
        facility=None,
        channel=channel,
        payload={"command": text[:60], "reply_len": len(reply)},
    )
    await db.commit()
    return _truncate(reply)


async def _cmd_algy(db: AsyncSession, pid: str) -> str:
    q = await db.execute(select(Patient).where(Patient.patient_id == pid))
    p = q.scalar_one_or_none()
    if not p:
        return "ERROR: Patient ID not found in national health registry."
    return (
        f"RE: {p.first_name} {p.last_name}. ALLERGIES: {p.severe_allergies}. "
        f"BLOOD: {p.blood_type}."
    )


async def _cmd_diag(db: AsyncSession, pid: str) -> str:
    q = await db.execute(select(Patient).where(Patient.patient_id == pid))
    p = q.scalar_one_or_none()
    if not p:
        return "ERROR: Patient ID not found."
    eq = await db.execute(
        select(Encounter)
        .where(Encounter.patient_id == pid)
        .order_by(Encounter.created_at.desc())
        .limit(2)
    )
    rows = eq.scalars().all()
    if not rows:
        return f"RE: {p.first_name} {p.last_name}. No prior diagnoses recorded."
    parts = [
        f"{r.created_at:%d/%m/%y}: {r.diagnosis[:40]} @ {r.facility_name[:20]}"
        for r in rows
    ]
    return f"RE: {p.first_name} {p.last_name}. " + " | ".join(parts)


async def _cmd_log(db: AsyncSession, pid: str, diag: str, meds: str, sender: str) -> str:
    q = await db.execute(select(Patient).where(Patient.patient_id == pid))
    p = q.scalar_one_or_none()
    if not p:
        return "ERROR: Patient ID not found."
    enc = Encounter(
        patient_id=pid,
        facility_name="SMS_REMOTE",
        health_worker_id=sender,
        symptoms="(via SMS)",
        diagnosis=diag[:500],
        medications_prescribed=meds[:500],
        is_synced=True,
    )
    db.add(enc)
    await db.flush()
    return f"SUCCESS: Encounter logged for {pid} at {enc.created_at:%d/%m/%y %H:%M}."