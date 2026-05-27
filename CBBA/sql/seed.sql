-- Datos de ejemplo - Hospital Cochabamba (CBBA)

INSERT INTO paciente (nombre, tipo_sangre, alergias, enfermedades_cronicas, id_hospital)
VALUES
    ('Rosa Mamani',   'A-',  'Sulfa',            'Ninguna',      2),
    ('Luis Fernandez','O+',  'Ninguna',          'Colesterol',   2),
    ('Sofia Rojas',   'AB+', 'Penicilina',       'Migrana',      2),
    ('Diego Alarcon', 'B-',  'Frutos secos',     'Ninguna',      2),
    ('Gabriela Soliz','O+',  'Ninguna',          'Hipotiroidismo',2);

INSERT INTO historial_clinico (id_paciente, observaciones, fecha)
VALUES
    (1, 'Control general. Presion arterial normal.',          '2025-03-10 09:30:00'),
    (1, 'Analisis de sangre. Resultados estables.',           '2025-05-12 10:00:00'),
    (2, 'Examen de colesterol. Nivel elevado.',               '2025-02-18 11:00:00'),
    (3, 'Crisis de migrana. Medicacion recetada.',            '2025-04-22 15:00:00'),
    (4, 'Revision alergologica sin novedades.',               '2025-01-30 08:30:00'),
    (5, 'Control de hormona tiroidea. Ajuste de dosis.',      '2025-03-25 14:00:00');
