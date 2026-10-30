
CREATE TABLE IF NOT EXISTS users (
    user_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username       VARCHAR(80)  NOT NULL UNIQUE,
    password_hash  TEXT         NOT NULL,
    full_name      VARCHAR(150) NOT NULL,
    role           VARCHAR(40)  NOT NULL CHECK (role IN ('CommunityHealthWorker','MedicalOfficer','SystemAdmin')),
    facility_name  VARCHAR(150) NOT NULL,
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS patients (
    patient_id       VARCHAR(50) PRIMARY KEY,
    national_id      VARCHAR(50) UNIQUE,
    first_name       VARCHAR(100) NOT NULL,
    last_name        VARCHAR(100) NOT NULL,
    date_of_birth    DATE         NOT NULL,
    gender           VARCHAR(10)  NOT NULL,
    home_province    VARCHAR(50)  NOT NULL,
    blood_type       VARCHAR(3)   NOT NULL,
    severe_allergies TEXT         NOT NULL DEFAULT 'NONE',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_patients_allergies
    ON patients (patient_id) WHERE severe_allergies <> 'NONE';

CREATE TABLE IF NOT EXISTS encounters (
    encounter_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id            VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE RESTRICT,
    facility_name         VARCHAR(150) NOT NULL,
    health_worker_id      VARCHAR(80)  NOT NULL,
    symptoms              TEXT NOT NULL,
    diagnosis             TEXT NOT NULL,
    medications_prescribed TEXT NOT NULL,
    is_synced             BOOLEAN NOT NULL DEFAULT TRUE,
    client_event_id       VARCHAR(80) UNIQUE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_encounters_patient_time
    ON encounters (patient_id, created_at DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
    log_id          BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type      VARCHAR(40) NOT NULL,
    operator_id     VARCHAR(80) NOT NULL,
    target_patient  VARCHAR(50),
    facility        VARCHAR(150),
    channel         VARCHAR(40) NOT NULL,
    payload_hash    CHAR(64) NOT NULL,
    prev_hash       CHAR(64) NOT NULL,
    chain_hash      CHAR(64) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_patient ON audit_logs (target_patient);