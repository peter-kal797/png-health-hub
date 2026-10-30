INSERT INTO users (username, password_hash, full_name, role, facility_name) VALUES 
('chw_demo', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK2i', 'Demo CHW', 'CommunityHealthWorker', 'Tari CHP'),
('dr_demo', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK2i', 'Demo Doctor', 'MedicalOfficer', 'Port Moresby General Hospital'),
('admin_demo', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGGa31Y2', 'System Admin', 'SystemAdmin', 'NICTA HQ')
ON CONFLICT (username) DO NOTHING;