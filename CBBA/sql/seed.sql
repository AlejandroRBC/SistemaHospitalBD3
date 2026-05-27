-- Datos de ejemplo - Hospital Cochabamba (CBBA)

INSERT INTO paciente_cbba (nombre, apellido, fecha_nacimiento, tipo_sangre, alergias, enfermedades_cronicas, telefono, direccion, id_hospital)
VALUES
    ('Rosa',    'Mamani',    '1992-04-18', 'A-',  'Sulfa',            'Ninguna',       '72345678', 'Av. Heroinas #123, Cochabamba',  2),
    ('Luis',    'Fernandez', '1980-09-25', 'O+',  'Ninguna',          'Colesterol',    '71456789', 'Calle Baptista #456, Cochabamba',2),
    ('Sofia',   'Rojas',     '1995-12-02', 'AB+', 'Penicilina',       'Migrana',       '74567890', 'Av. America #789, Cochabamba',   2),
    ('Diego',   'Alarcon',   '1988-07-14', 'B-',  'Frutos secos',     'Ninguna',       '75678901', 'Calle Ecuador #321, Cochabamba', 2),
    ('Gabriela','Soliz',     '1975-03-30', 'O+',  'Ninguna',          'Hipotiroidismo','76789012', 'Zona Norte #654, Cochabamba',    2);

INSERT INTO historial_cbba (id_paciente, observaciones, fecha)
VALUES
    (1, 'Control general. Presion arterial normal.',          '2025-03-10 09:30:00'),
    (1, 'Analisis de sangre. Resultados estables.',           '2025-05-12 10:00:00'),
    (2, 'Examen de colesterol. Nivel elevado.',               '2025-02-18 11:00:00'),
    (3, 'Crisis de migrana. Medicacion recetada.',            '2025-04-22 15:00:00'),
    (4, 'Revision alergologica sin novedades.',               '2025-01-30 08:30:00'),
    (5, 'Control de hormona tiroidea. Ajuste de dosis.',      '2025-03-25 14:00:00');

INSERT INTO consulta_cbba (id_paciente, diagnostico, tratamiento, fecha)
VALUES
    (1, 'Paciente estable. Control de rutina.',              'Sin novedades. Proximo control en 6 meses.',          '2025-05-12 10:00:00'),
    (2, 'Hipercolesterolemia',                               'Atorvastatina 20mg/dia. Dieta baja en grasas.',       '2025-02-18 11:00:00'),
    (3, 'Migrana cronica',                                   'Sumatriptan 50mg en crisis. Evitar desencadenantes.', '2025-04-22 15:00:00'),
    (4, 'Paciente sano. Control alergologico.',              'Sin sintomas. Continuar evitando alergenos.',         '2025-01-30 08:30:00'),
    (5, 'Hipotiroidismo controlado',                         'Levotiroxina 75mcg/dia. Control en 3 meses.',         '2025-03-25 14:00:00');
