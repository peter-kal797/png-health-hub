INSERT INTO users (username, password_hash, full_name, role, facility_name) VALUES 
('chw_demo', 'YOUR_DEMO_HASH', 'Demo CHW', 'CommunityHealthWorker', 'Tari CHP'),
('dr_demo', 'YOUR_DEMO_HASH', 'Demo Doctor', 'MedicalOfficer', 'Port Moresby General Hospital'),
('admin_demo', 'YOUR_ADMIN_HASH', 'System Admin', 'SystemAdmin', 'NICTA HQ')
ON CONFLICT (username) DO NOTHING;