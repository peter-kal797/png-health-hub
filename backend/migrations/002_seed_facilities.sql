INSERT INTO facilities (name, province, type) VALUES
('Port Moresby General Hospital', 'National Capital District', 'Hospital'),
('Angau General Hospital', 'Morobe', 'Hospital'),
('Mt Hagen General Hospital', 'Western Highlands', 'Hospital'),
('Goroka General Hospital', 'Eastern Highlands', 'Hospital'),
('Nonga General Hospital', 'East New Britain', 'Hospital'),
('Modilon General Hospital', 'Madang', 'Hospital'),
('Boram General Hospital', 'East Sepik', 'Hospital'),
('Kundiawa District Hospital', 'Chimbu', 'Hospital'),
('Alotau Provincial Hospital', 'Milne Bay', 'Hospital'),
('Tari CHP', 'Hela', 'Community Health Post')
ON CONFLICT DO NOTHING;