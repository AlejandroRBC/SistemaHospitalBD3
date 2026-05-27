-- Datos de ejemplo - Hospital La Paz (LPZ)

INSERT INTO hospital (id_hospital, nombre, ciudad, ip_radmin, puerto, motor_bd)
VALUES
    (1, 'Hospital La Paz', 'La Paz', '26.10.1.5', 5000, 'PostgreSQL'),
    (2, 'Hospital Cochabamba', 'Cochabamba', '26.10.1.6', 5000, 'SQL Server'),
    (3, 'Hospital Santa Cruz', 'Santa Cruz', '26.10.1.7', 5000, 'SQL Server');

INSERT INTO paciente (nombre, apellido, fecha_nacimiento, tipo_sangre, alergias, enfermedades_cronicas, telefono, direccion, id_hospital)
VALUES
    ('Juan', 'Perez',     '1985-03-15', 'O+',  'Ninguna',          'Asma',        '71234567', 'Av. Arce #123, La Paz',       1),
    ('Maria', 'Luna',     '1990-07-22', 'A+',  'Penicilina',       'Diabetes',    '69876543', 'Calle Potosi #456, La Paz',   1),
    ('Carlos', 'Vargas',  '1978-11-08', 'B+',  'Polen',            'Hipertension','73456789', 'Av. 16 de Julio #789, La Paz',1),
    ('Ana', 'Condori',    '2000-01-30', 'AB-', 'Ninguna',          'Ninguna',     '75678901', 'Calle Loayza #321, La Paz',   1),
    ('Pedro', 'Quispe',   '1965-09-12', 'O-',  'Ibuprofeno',       'Artritis',    '77890123', 'Zona Sopocachi #654, La Paz', 1);

INSERT INTO historial_clinico (id_paciente, observaciones, fecha)
VALUES
    (1, 'Control de asma. Sintomas controlados.',             '2025-01-15 10:30:00'),
    (1, 'Revision trimestral. Todo estable.',                 '2025-04-15 11:00:00'),
    (2, 'Control de diabetes. Ajuste de insulina.',           '2025-02-10 09:00:00'),
    (3, 'Presion arterial elevada. Se ajusta medicacion.',    '2025-03-05 14:30:00'),
    (4, 'Examen general sin novedades.',                      '2025-01-20 08:00:00'),
    (5, 'Dolor articular. Se receta antiinflamatorio.',       '2025-02-28 16:00:00');

INSERT INTO consulta (id_paciente, diagnostico, tratamiento, fecha, id_hospital)
VALUES
    (1, 'Asma bronquial estable',       'Mantener tratamiento actual. Control en 3 meses.',     '2025-04-15 11:00:00', 1),
    (2, 'Diabetes tipo 2 controlada',   'Ajuste de insulina. Dieta baja en carbohidratos.',    '2025-02-10 09:00:00', 1),
    (3, 'Hipertension arterial',         'Enalapril 10mg/dia. Reducir sal en la dieta.',         '2025-03-05 14:30:00', 1),
    (4, 'Paciente sano. Control rutina','Sin novedades. Proximo control en 1 año.',             '2025-01-20 08:00:00', 1),
    (5, 'Artritis reumatoide',          'Ibuprofeno 400mg c/8h. Terapia fisica.',               '2025-02-28 16:00:00', 1);

INSERT INTO fragment_catalog (tabla, hospital, ip_servidor, puerto, motor_bd)
VALUES
    ('pacientes',       'LPZ',  '26.10.1.5', 5000, 'PostgreSQL'),
    ('historial_clinico','LPZ', '26.10.1.5', 5000, 'PostgreSQL'),
    ('consultas',       'LPZ',  '26.10.1.5', 5000, 'PostgreSQL'),
    ('pacientes',       'CBBA', '26.10.1.6', 5000, 'SQL Server'),
    ('historial_clinico','CBBA','26.10.1.6', 5000, 'SQL Server'),
    ('consultas',       'CBBA', '26.10.1.6', 5000, 'SQL Server'),
    ('pacientes',       'STCZ', '26.10.1.7', 5000, 'SQL Server'),
    ('historial_clinico','STCZ','26.10.1.7', 5000, 'SQL Server'),
    ('consultas',       'STCZ', '26.10.1.7', 5000, 'SQL Server');
