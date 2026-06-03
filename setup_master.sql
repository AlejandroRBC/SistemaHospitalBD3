-- =============================================================
-- BASE DE DATOS MAESTRA NACIONAL — HOSPITAL NACIONAL BOLIVIA
-- Sistema Hospitalario Distribuido BD3 - UMSA 2026
-- Motor: PostgreSQL (base de referencia conceptual)
-- Ejecutar: psql -U postgres -f setup_master.sql
-- =============================================================
--
-- PROPOSITO ACADEMICO:
--   Este script representa la base de datos CENTRALIZADA original,
--   antes de aplicar cualquier fragmentacion.
--   Contiene TODOS los datos de los 3 hospitales en una sola BD.
--
--   A partir de esta base se derivan las 3 bases fragmentadas:
--     hospital_lpz   -> fragmento WHERE id_hospital = 1 (La Paz)
--     hospital_cbba  -> fragmento WHERE id_hospital = 2 (Cochabamba)
--     hospital_stcz  -> fragmento WHERE id_hospital = 3 (Santa Cruz)
--
--   Ver setup_lpz.sql, setup_cbba.sql, setup_stcz.sql para ver
--   como se aplica la fragmentacion en cada nodo.
-- =============================================================

DROP DATABASE IF EXISTS hospital_nacional;
CREATE DATABASE hospital_nacional;
\c hospital_nacional

-- =============================================================
-- ESQUEMA — IDENTICO EN LOS 3 NODOS DISTRIBUIDOS
-- =============================================================

CREATE TABLE hospital (
    id_hospital INT         PRIMARY KEY,
    nombre      VARCHAR(150) NOT NULL,
    ciudad      VARCHAR(80),
    direccion   VARCHAR(250),
    telefono    VARCHAR(20)
);

CREATE TABLE medicamento (
    id_medicamento INT         PRIMARY KEY,
    nombre         VARCHAR(120) NOT NULL,
    descripcion    TEXT,
    dosis          VARCHAR(80),
    fabricante     VARCHAR(120)
);

CREATE TABLE paciente (
    id_paciente      SERIAL PRIMARY KEY,
    nombre           VARCHAR(100) NOT NULL,
    apellido         VARCHAR(100) NOT NULL,
    ci               VARCHAR(20)  UNIQUE,
    fecha_nacimiento DATE,
    sexo             VARCHAR(15),
    direccion        VARCHAR(250),
    telefono         VARCHAR(20),
    tipo_sangre      VARCHAR(5),
    alergias         TEXT DEFAULT '',
    id_hospital      INT  REFERENCES hospital(id_hospital)
);

CREATE TABLE doctor (
    id_doctor    SERIAL PRIMARY KEY,
    nombre       VARCHAR(100) NOT NULL,
    apellido     VARCHAR(100) NOT NULL,
    especialidad VARCHAR(120),
    telefono     VARCHAR(20),
    correo       VARCHAR(120),
    id_hospital  INT REFERENCES hospital(id_hospital)
);

CREATE TABLE consulta (
    id_consulta SERIAL PRIMARY KEY,
    fecha       DATE DEFAULT CURRENT_DATE,
    hora        TIME DEFAULT CURRENT_TIME,
    motivo      TEXT,
    diagnostico TEXT,
    id_paciente INT REFERENCES paciente(id_paciente),
    id_doctor   INT REFERENCES doctor(id_doctor),
    id_hospital INT REFERENCES hospital(id_hospital)
);

CREATE TABLE historial_clinico_v1 (
    id_historial          SERIAL PRIMARY KEY,
    id_paciente           INT  UNIQUE REFERENCES paciente(id_paciente),
    tipo_sangre           VARCHAR(5),
    alergias              TEXT DEFAULT '',
    enfermedades_cronicas TEXT DEFAULT ''
);

CREATE TABLE historial_clinico_v2 (
    id_historial  INT PRIMARY KEY REFERENCES historial_clinico_v1(id_historial),
    id_paciente   INT REFERENCES paciente(id_paciente),
    fecha_apertura DATE DEFAULT CURRENT_DATE,
    antecedentes  TEXT DEFAULT '',
    observaciones TEXT DEFAULT ''
);

CREATE TABLE emergencia (
    id_emergencia   SERIAL PRIMARY KEY,
    fecha           DATE DEFAULT CURRENT_DATE,
    hora            TIME DEFAULT CURRENT_TIME,
    tipo_emergencia VARCHAR(120),
    estado_paciente VARCHAR(120),
    observaciones   TEXT,
    id_paciente     INT REFERENCES paciente(id_paciente),
    id_hospital     INT REFERENCES hospital(id_hospital)
);

CREATE TABLE receta (
    id_receta    SERIAL PRIMARY KEY,
    fecha        DATE DEFAULT CURRENT_DATE,
    indicaciones TEXT,
    id_consulta  INT REFERENCES consulta(id_consulta)
);

CREATE TABLE receta_medicamento (
    id_receta      INT REFERENCES receta(id_receta),
    id_medicamento INT REFERENCES medicamento(id_medicamento),
    cantidad       INT DEFAULT 1,
    PRIMARY KEY (id_receta, id_medicamento)
);

CREATE TABLE transferencias_hospitalarias (
    id_transferencia    SERIAL PRIMARY KEY,
    fecha_transferencia DATE DEFAULT CURRENT_DATE,
    motivo              TEXT,
    estado              VARCHAR(50) DEFAULT 'Pendiente',
    id_paciente         INT REFERENCES paciente(id_paciente),
    id_hospital_origen  INT REFERENCES hospital(id_hospital),
    id_hospital_destino INT REFERENCES hospital(id_hospital)
);

-- =============================================================
-- DATOS — BASE NACIONAL COMPLETA (los 3 hospitales juntos)
-- =============================================================

-- ── Hospitales ──────────────────────────────────────────────
INSERT INTO hospital VALUES
    (1, 'Hospital Central de La Paz',      'La Paz',      'Av. Saavedra 2000, Miraflores', '+591-2-2224444'),
    (2, 'Hospital Regional de Cochabamba', 'Cochabamba',  'Av. Aniceto Arce 456, Centro',  '+591-4-4221122'),
    (3, 'Hospital del Oriente',            'Santa Cruz',  'Av. Cañoto 789, Equipetrol',    '+591-3-3334455');

-- ── Medicamentos (catalogo nacional) ────────────────────────
INSERT INTO medicamento VALUES
    (1,  'Paracetamol',  'Analgésico y antipirético',              '500mg cada 8 horas',            'Bagó Bolivia'),
    (2,  'Ibuprofeno',   'Antiinflamatorio no esteroideo',         '400mg cada 8 horas',            'Roemmers'),
    (3,  'Amoxicilina',  'Antibiótico de amplio espectro',         '500mg cada 8 horas por 7 dias', 'INTI'),
    (4,  'Metformina',   'Antidiabético oral',                     '850mg con las comidas',         'Bagó Bolivia'),
    (5,  'Enalapril',    'Antihipertensivo IECA',                  '10mg una vez al dia',           'Roemmers'),
    (6,  'Omeprazol',    'Inhibidor de bomba de protones',         '20mg antes del desayuno',       'INTI'),
    (7,  'Aspirina',     'Antiagregante plaquetario',              '100mg una vez al dia',          'Bayer'),
    (8,  'Loratadina',   'Antihistamínico',                        '10mg una vez al dia',           'Bagó Bolivia'),
    (9,  'Captopril',    'Antihipertensivo de rescate',            '25mg sublingual si necesario',  'Roemmers'),
    (10, 'Diclofenaco',  'Antiinflamatorio para dolor agudo',      '75mg cada 12 horas',            'Bagó Bolivia');

-- ── Doctores (todos los hospitales) ─────────────────────────
-- LPZ (id_hospital = 1)
INSERT INTO doctor (nombre, apellido, especialidad, telefono, correo, id_hospital) VALUES
    ('Carlos',  'Mamani Quispe',  'Medicina General',  '70011111', 'cmamani@hclpz.bo',  1),
    ('Ana',     'Quispe Flores',  'Cardiología',       '70022222', 'aquispe@hclpz.bo',  1),
    ('Roberto', 'Flores Condori', 'Emergenciología',   '70033333', 'rflores@hclpz.bo',  1),
    ('María',   'Choque Lima',    'Pediatría',         '70044444', 'mchoque@hclpz.bo',  1),
    ('Jorge',   'Vargas Vidal',   'Neurología',        '70055555', 'jvargas@hclpz.bo',  1);
-- CBBA (id_hospital = 2)
INSERT INTO doctor (nombre, apellido, especialidad, telefono, correo, id_hospital) VALUES
    ('Laura',   'Vásquez Rojas',   'Medicina General', '60011111', 'lvasquez@hrcbba.bo',  2),
    ('Miguel',  'Torrico Paz',     'Traumatología',    '60022222', 'mtorrico@hrcbba.bo',  2),
    ('Sandra',  'Lima Arce',       'Ginecología',      '60033333', 'slima@hrcbba.bo',     2);
-- STCZ (id_hospital = 3)
INSERT INTO doctor (nombre, apellido, especialidad, telefono, correo, id_hospital) VALUES
    ('Luis',     'Justiniano Vaca', 'Medicina General',  '30011111', 'ljustiniano@horiente.bo', 3),
    ('Carmen',   'Suárez Montero',  'Traumatología',     '30022222', 'csuarez@horiente.bo',     3),
    ('Fernando', 'Parada Cruz',     'Emergenciología',   '30033333', 'fparada@horiente.bo',     3);

-- ── Pacientes (todos los hospitales juntos) ──────────────────
-- LPZ (id_hospital = 1) — IDs 1-3
INSERT INTO paciente (nombre, apellido, ci, fecha_nacimiento, sexo, direccion, telefono, tipo_sangre, alergias, id_hospital) VALUES
    ('Juan',   'Pérez Mamani',  '1234567', '1985-03-15', 'M', 'Calle Murillo 123, La Paz',    '71111111', 'O+', 'Penicilina', 1),
    ('María',  'Gómez Choque',  '2345678', '1990-07-22', 'F', 'Av. 6 de Agosto 456, La Paz', '72222222', 'A-', 'Ninguna',    1),
    ('Pedro',  'Ticona Apaza',  '3456789', '1978-11-08', 'M', 'Plaza Murillo 78, La Paz',     '73333333', 'B+', 'Ibuprofeno', 1);
-- CBBA (id_hospital = 2) — IDs 4-6
INSERT INTO paciente (nombre, apellido, ci, fecha_nacimiento, sexo, direccion, telefono, tipo_sangre, alergias, id_hospital) VALUES
    ('Carlos',  'Mamani Quispe',   '4567890', '1982-05-10', 'M', 'Av. Heroinas 234, Cbba',          '61111111', 'B+',  'Polen',     2),
    ('Ana',     'Lima Torres',     '5678901', '1995-09-18', 'F', 'Calle Ecuador 567, Cbba',         '62222222', 'AB-', 'Ninguna',   2),
    ('Roberto', 'Herrera Vidal',   '5901234', '1988-02-14', 'M', 'Av. Blanco Galindo 890, Cbba',    '63333333', 'O+',  'Aspirina',  2);
-- STCZ (id_hospital = 3) — IDs 7-9
INSERT INTO paciente (nombre, apellido, ci, fecha_nacimiento, sexo, direccion, telefono, tipo_sangre, alergias, id_hospital) VALUES
    ('Luis',    'Rodríguez Suárez', '6789012', '1975-12-03', 'M', 'Av. San Martín 890, Santa Cruz',     '31111111', 'O-', 'Ibuprofeno', 3),
    ('Sofía',   'Torrico Méndez',   '7890123', '2000-04-25', 'F', 'Calle Independencia 321, Sta. Cruz', '32222222', 'A+', 'Ninguna',    3),
    ('Diego',   'Morales Vaca',     '8901234', '1993-08-17', 'M', 'Av. Cristo Redentor 456, Sta. Cruz', '33333333', 'B-', 'Latex',      3);

-- ── Historial Clinico V1 (datos criticos — todos los pacientes) ──
INSERT INTO historial_clinico_v1 (id_paciente, tipo_sangre, alergias, enfermedades_cronicas)
SELECT id_paciente, tipo_sangre, alergias, '' FROM paciente;

-- ── Historial Clinico V2 (notas detalladas — todos los pacientes) ──
INSERT INTO historial_clinico_v2 (id_historial, id_paciente, fecha_apertura, antecedentes, observaciones)
SELECT v1.id_historial, v1.id_paciente, CURRENT_DATE,
       'Antecedentes familiares por evaluar.',
       'Paciente ingresado al sistema nacional.'
FROM historial_clinico_v1 v1;

-- ── Consultas (una por paciente de ejemplo) ──────────────────
INSERT INTO consulta (fecha, hora, motivo, diagnostico, id_paciente, id_doctor, id_hospital) VALUES
    ('2026-05-10', '09:30', 'Dolor de cabeza persistente',  'Cefalea tensional. Se receta paracetamol.',  1, 1, 1),
    ('2026-05-11', '10:00', 'Chequeo cardiaco rutinario',   'Sin anomalias cardiacas detectadas.',        2, 2, 1),
    ('2026-05-08', '11:15', 'Dolor en rodilla derecha',     'Artritis leve. Se receta ibuprofeno.',        4, 6, 2),
    ('2026-05-09', '14:00', 'Fractura de brazo izquierdo',  'Fractura radio distal. Inmovilizacion.',      5, 7, 2),
    ('2026-05-07', '08:45', 'Fiebre alta y malestar general','Influenza estacional. Reposo y liquidos.',   7, 9, 3),
    ('2026-05-12', '15:30', 'Consulta ginecologica',         'Sin hallazgos patologicos.',                  8, 11, 3);

-- ── Emergencias ──────────────────────────────────────────────
INSERT INTO emergencia (fecha, hora, tipo_emergencia, estado_paciente, observaciones, id_paciente, id_hospital) VALUES
    ('2026-05-13', '22:10', 'Accidente de transito',      'Critico',  'Politraumatismo. UCI.',                     3, 1),
    ('2026-05-14', '03:20', 'Crisis hipertensiva',        'Estable',  'PA 190/110. Se administra captopril.',      6, 2),
    ('2026-05-15', '17:05', 'Reaccion alergica severa',   'Grave',    'Anafilaxia por latex. Epinefrina aplicada.',9, 3);

-- ── Recetas ──────────────────────────────────────────────────
INSERT INTO receta (fecha, indicaciones, id_consulta) VALUES
    ('2026-05-10', 'Tomar 1 comprimido de 500mg cada 8 horas por 5 dias.', 1),
    ('2026-05-08', 'Tomar 1 capsula de 400mg cada 8 horas con alimentos.', 3);

INSERT INTO receta_medicamento (id_receta, id_medicamento, cantidad) VALUES
    (1, 1, 1),  -- Receta 1: Paracetamol
    (2, 2, 1);  -- Receta 2: Ibuprofeno

-- =============================================================
-- VERIFICACION — Vista de la base de datos maestra completa
-- =============================================================

SELECT 'TABLA'                   AS entidad,  'REGISTROS' AS cantidad
UNION ALL SELECT '──────────────────',        '──────────'
UNION ALL SELECT 'hospital',                   COUNT(*)::TEXT FROM hospital
UNION ALL SELECT 'medicamento',                COUNT(*)::TEXT FROM medicamento
UNION ALL SELECT 'paciente (TOTAL)',           COUNT(*)::TEXT FROM paciente
UNION ALL SELECT '  └─ LPZ  (id_hospital=1)', COUNT(*)::TEXT FROM paciente WHERE id_hospital=1
UNION ALL SELECT '  └─ CBBA (id_hospital=2)', COUNT(*)::TEXT FROM paciente WHERE id_hospital=2
UNION ALL SELECT '  └─ STCZ (id_hospital=3)', COUNT(*)::TEXT FROM paciente WHERE id_hospital=3
UNION ALL SELECT 'doctor (TOTAL)',             COUNT(*)::TEXT FROM doctor
UNION ALL SELECT 'consulta',                   COUNT(*)::TEXT FROM consulta
UNION ALL SELECT 'emergencia',                 COUNT(*)::TEXT FROM emergencia
UNION ALL SELECT 'historial_clinico_v1',       COUNT(*)::TEXT FROM historial_clinico_v1;

-- =============================================================
-- FRAGMENTACION HORIZONTAL — como quedaria cada nodo
-- (SOLO INFORMATIVO en este script — en los setup de nodo si se aplica)
-- =============================================================

-- Fragmento LPZ  : SELECT * FROM paciente WHERE id_hospital = 1
-- Fragmento CBBA : SELECT * FROM paciente WHERE id_hospital = 2
-- Fragmento STCZ : SELECT * FROM paciente WHERE id_hospital = 3

SELECT 'FRAGMENTO LPZ'  AS nodo, id_paciente, nombre, apellido, tipo_sangre FROM paciente WHERE id_hospital=1
UNION ALL
SELECT 'FRAGMENTO CBBA' AS nodo, id_paciente, nombre, apellido, tipo_sangre FROM paciente WHERE id_hospital=2
UNION ALL
SELECT 'FRAGMENTO STCZ' AS nodo, id_paciente, nombre, apellido, tipo_sangre FROM paciente WHERE id_hospital=3
ORDER BY nodo, id_paciente;
