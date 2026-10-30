INSERT INTO guidelines (title, category, content) VALUES
('Malaria Vivax', 'Infectious Disease', 'First-line: Chloroquine 25mg/kg over 3 days + Primaquine 0.25mg/kg daily for 14 days.'),
('Malaria Falciparum', 'Infectious Disease', 'First-line: Artemether-Lumefantrine (Coartem) 6 doses over 3 days.'),
('Tuberculosis (TB)', 'Infectious Disease', 'Standard regimen: 2HRZE/4HR. Monitor liver function.'),
('Pneumonia', 'Respiratory', 'Amoxicillin 500mg TID for 7 days. Refer if severe respiratory distress.'),
('Antenatal Care (ANC)', 'Maternal Health', 'Minimum 4 visits. Tetanus toxoid, Iron/Folic acid, BP monitoring.')
ON CONFLICT (title) DO NOTHING;