-- 1. Create missing tables
CREATE TABLE IF NOT EXISTS vaccinations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    vaccine_name VARCHAR(150) NOT NULL,
    dose_number VARCHAR(50),
    date_administered DATE NOT NULL,
    administered_by VARCHAR(150),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS maternal_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    visit_date DATE NOT NULL,
    gestational_age_weeks INTEGER,
    blood_pressure VARCHAR(20),
    weight VARCHAR(20),
    fetal_heart_rate VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    from_facility VARCHAR(150) NOT NULL,
    to_facility VARCHAR(150) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    accepted_by VARCHAR(150),
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_name VARCHAR(150) NOT NULL,
    drug_name VARCHAR(150) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    unit VARCHAR(50) NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Fix the guidelines table (rename guideline_id to id to match the Python model)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='guidelines' AND column_name='guideline_id') THEN
        ALTER TABLE guidelines RENAME COLUMN guideline_id TO id;
    END IF;
END $$;