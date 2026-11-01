import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str
    facility: str


class PatientCreate(BaseModel):
    patient_id: str = Field(..., description="Format: PNG-SP-XXXXXX")
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    home_province: str
    blood_type: str
    severe_allergies: str = "NONE"


class PatientOut(BaseModel):
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    home_province: str
    blood_type: str
    severe_allergies: str

    model_config = {"from_attributes": True}


class EncounterIn(BaseModel):
    patient_id: str = Field(min_length=3, max_length=50)
    facility_name: str
    health_worker_id: str
    symptoms: str
    diagnosis: str
    medications_prescribed: str
    blood_pressure: str | None = None
    temperature: str | None = None
    weight: str | None = None
    heart_rate: str | None = None
    client_event_id: str | None = None


class EncounterOut(BaseModel):
    encounter_id: uuid.UUID
    patient_id: str
    facility_name: str
    health_worker_id: str
    symptoms: str
    diagnosis: str
    medications_prescribed: str
    blood_pressure: str | None = None
    temperature: str | None = None
    weight: str | None = None
    heart_rate: str | None = None
    is_synced: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncBatch(BaseModel):
    device_id: str
    encounters: list[EncounterIn]


class SyncResult(BaseModel):
    accepted: int
    duplicates: int
    rejected: int
    details: list[str] = []


class VaccinationIn(BaseModel):
    patient_id: str
    vaccine_name: str
    dose_number: str | None = None
    date_administered: date
    administered_by: str | None = None


class VaccinationOut(VaccinationIn):
    id: uuid.UUID
    created_at: datetime
    model_config = {"from_attributes": True}


class MaternalRecordIn(BaseModel):
    patient_id: str
    visit_date: date
    gestational_age_weeks: int | None = None
    blood_pressure: str | None = None
    weight: str | None = None
    fetal_heart_rate: str | None = None
    notes: str | None = None


class MaternalRecordOut(MaternalRecordIn):
    id: uuid.UUID
    created_at: datetime
    model_config = {"from_attributes": True}


class InventoryIn(BaseModel):
    drug_name: str
    quantity: int
    unit: str
    facility_name: str


class InventoryOut(InventoryIn):
    id: uuid.UUID
    last_updated: datetime
    model_config = {"from_attributes": True}


class BillIn(BaseModel):
    patient_id: str
    description: str
    amount: float


class BillOut(BillIn):
    id: uuid.UUID
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ReferralIn(BaseModel):
    patient_id: str
    from_facility: str
    to_facility: str
    reason: str


class ReferralOut(BaseModel):
    id: uuid.UUID
    patient_id: str
    from_facility: str
    to_facility: str
    reason: str
    status: str
    accepted_by: str | None = None
    accepted_at: datetime | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class GuidelineIn(BaseModel):
    title: str
    category: str
    content: str


class GuidelineOut(GuidelineIn):
    id: uuid.UUID
    created_at: datetime
    model_config = {"from_attributes": True}