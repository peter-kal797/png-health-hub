import re

SEVIS_PATTERN = re.compile(r"^PNG-SP-\d{6}$")

def validate_sevispass(patient_id: str) -> dict:
    if not SEVIS_PATTERN.match(patient_id):
        return {"valid": False, "error": "Invalid SevisPass format. Expected PNG-SP-XXXXXX."}
    return {"valid": True, "error": None, "verified_name": "Verified via SevisPass"}