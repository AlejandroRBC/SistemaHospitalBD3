-- Datos de ejemplo - Hospital La Paz (LPZ)

INSERT INTO paciente (nombre, tipo_sangre, alergias, enfermedades_cronicas, id_hospital)
VALUES
    ('Juan Perez',     'O+',  'Ninguna',          'Asma',        1),
    ('Maria Luna',     'A+',  'Penicilina',       'Diabetes',    1),
    ('Carlos Vargas',  'B+',  'Polen',            'Hipertension',1),
    ('Ana Condori',    'AB-', 'Ninguna',          'Ninguna',     1),
    ('Pedro Quispe',   'O-',  'Ibuprofeno',       'Artritis',    1);

INSERT INTO historial_clinico (id_paciente, observaciones, fecha)
VALUES
    (1, 'Control de asma. Sintomas controlados.',             '2025-01-15 10:30:00'),
    (1, 'Revision trimestral. Todo estable.',                 '2025-04-15 11:00:00'),
    (2, 'Control de diabetes. Ajuste de insulina.',           '2025-02-10 09:00:00'),
    (3, 'Presion arterial elevada. Se ajusta medicacion.',    '2025-03-05 14:30:00'),
    (4, 'Examen general sin novedades.',                      '2025-01-20 08:00:00'),
    (5, 'Dolor articular. Se receta antiinflamatorio.',       '2025-02-28 16:00:00');
