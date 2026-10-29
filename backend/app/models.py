import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    facility_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Patient(Base):
    __tablename__ = "patients"

    patient_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    national_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    home_province: Mapped[str] = mapped_column(String(50), nullable=False)
    blood_type: Mapped[str] = mapped_column(String(3), nullable=False)
    severe_allergies: Mapped[str] = mapped_column(Text, default="NONE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Encounter(Base):
    __tablename__ = "encounters"

    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(String(50), nullable=False)
    facility_name: Mapped[str] = mapped_column(String(150), nullable=False)
    health_worker_id: Mapped[str] = mapped_column(String(80), nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    medications_prescribed: Mapped[str] = mapped_column(Text, nullable=False)
    
    blood_pressure: Mapped[str | None] = mapped_column(String(20), nullable=True)
    temperature: Mapped[str | None] = mapped_column(String(20), nullable=True)
    weight: Mapped[str | None] = mapped_column(String(20), nullable=True)
    heart_rate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    is_synced: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    client_event_id: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(80), nullable=False)
    target_patient: Mapped[str | None] = mapped_column(String(50), nullable=True)
    facility: Mapped[str | None] = mapped_column(String(150), nullable=True)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    chain_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class Facility(Base):
    __tablename__ = "facilities"
    
    facility_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    province: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)


class Vaccination(Base):
    __tablename__ = "vaccinations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(String(50), nullable=False)
    vaccine_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dose_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_administered: Mapped[date] = mapped_column(Date, nullable=False)
    administered_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MaternalRecord(Base):
    __tablename__ = "maternal_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(String(50), nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    gestational_age_weeks: Mapped[int | None] = mapped_column(nullable=True)
    blood_pressure: Mapped[str | None] = mapped_column(String(20), nullable=True)
    weight: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fetal_heart_rate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="tablets")
    facility_name: Mapped[str] = mapped_column(String(150), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNPAID")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(String(50), nullable=False)
    from_facility: Mapped[str] = mapped_column(String(150), nullable=False)
    to_facility: Mapped[str] = mapped_column(String(150), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    accepted_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Guideline(Base):
    __tablename__ = "guidelines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)