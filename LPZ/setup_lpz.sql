-- =============================================================
-- SETUP NODO LPZ (La Paz) - PostgreSQL
-- Ejecutar: psql -U postgres -f setup_lpz.sql
-- =============================================================

-- Crear base de datos
-- psql -U postgres -c "CREATE DATABASE hospital_lpz;"
-- \c hospital_lpz

-- =============================================================
-- CATALOGOS NACIONALES (replicados en los 3 nodos)
-- =============================================================

CREATE TABLE IF NOT EXISTS hospital (
    id_hospital   SERIAL PRIMARY KEY,
    nombre        VARCHAR(150) NOT NULL,
    ciudad        VARCHAR(80),
    direccion     VARCHAR(250),
    telefono      VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS medicamento (
    id_medicamento SERIAL PRIMARY KEY,
    nombre         VARCHAR(120) NOT NULL,
    descripcion    TEXT,
    dosis          VARCHAR(80),
    fabricante     VARCHAR(120)
);

-- =============================================================
-- FRAGMENTO HORIZONTAL PRIMARIO: Paciente (id_hospital = 1)
-- =============================================================

CREATE TABLE IF NOT EXISTS paciente (
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
    id_hospital      INT  REFERENCES hospital(id_hospital) DEFAULT 1
);

-- =============================================================
-- FRAGMENTO HORIZONTAL PRIMARIO: Doctor (id_hospital = 1)
-- =============================================================

CREATE TABLE IF NOT EXISTS doctor (
    id_doctor   SERIAL PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    apellido    VARCHAR(100) NOT NULL,
    especialidad VARCHAR(120),
    telefono    VARCHAR(20),
    correo      VARCHAR(120),
    id_hospital INT REFERENCES hospital(id_hospital) DEFAULT 1
);

-- =============================================================
-- FRAGMENTO HORIZONTAL DERIVADO: Consulta (hereda de Paciente)
-- =============================================================

CREATE TABLE IF NOT EXISTS consulta (
    id_consulta SERIAL PRIMARY KEY,
    fecha       DATE    DEFAULT CURRENT_DATE,
    hora        TIME    DEFAULT CURRENT_TIME,
    motivo      TEXT,
    diagnostico TEXT,
    id_paciente INT REFERENCES paciente(id_paciente),
    id_doctor   INT REFERENCES doctor(id_doctor),
    id_hospital INT REFERENCES hospital(id_hospital) DEFAULT 1
);

-- =============================================================
-- FRAGMENTACION HIBRIDA: Historial Clinico
--   V1 = datos criticos (liviano, se replica)
--   V2 = notas pesadas (queda solo en el nodo origen)
-- =============================================================

CREATE TABLE IF NOT EXISTS historial_clinico_v1 (
    id_historial        SERIAL PRIMARY KEY,
    id_paciente         INT  REFERENCES paciente(id_paciente) UNIQUE,
    tipo_sangre         VARCHAR(5),
    alergias            TEXT DEFAULT '',
    enfermedades_cronicas TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS historial_clinico_v2 (
    id_historial  INT  PRIMARY KEY REFERENCES historial_clinico_v1(id_historial),
    id_paciente   INT  REFERENCES paciente(id_paciente),
    fecha_apertura DATE DEFAULT CURRENT_DATE,
    antecedentes  TEXT DEFAULT '',
    observaciones TEXT DEFAULT ''
);

-- =============================================================
-- FRAGMENTO HORIZONTAL DERIVADO: Emergencia (hereda de Hospital)
-- =============================================================

CREATE TABLE IF NOT EXISTS emergencia (
    id_emergencia   SERIAL PRIMARY KEY,
    fecha           DATE    DEFAULT CURRENT_DATE,
    hora            TIME    DEFAULT CURRENT_TIME,
    tipo_emergencia VARCHAR(120),
    estado_paciente VARCHAR(120),
    observaciones   TEXT,
    id_paciente     INT REFERENCES paciente(id_paciente),
    id_hospital     INT REFERENCES hospital(id_hospital) DEFAULT 1
);

-- =============================================================
-- FRAGMENTO HORIZONTAL DERIVADO: Receta (hereda de Consulta)
-- =============================================================

CREATE TABLE IF NOT EXISTS receta (
    id_receta   SERIAL PRIMARY KEY,
    fecha       DATE DEFAULT CURRENT_DATE,
    indicaciones TEXT,
    id_consulta INT REFERENCES consulta(id_consulta)
);

CREATE TABLE IF NOT EXISTS receta_medicamento (
    id_receta      INT REFERENCES receta(id_receta),
    id_medicamento INT REFERENCES medicamento(id_medicamento),
    cantidad       INT DEFAULT 1,
    PRIMARY KEY (id_receta, id_medicamento)
);

-- =============================================================
-- FRAGMENTO HORIZONTAL DERIVADO: Transferencias (hereda de Hospital_Origen)
-- =============================================================

CREATE TABLE IF NOT EXISTS transferencias_hospitalarias (
    id_transferencia    SERIAL PRIMARY KEY,
    fecha_transferencia DATE DEFAULT CURRENT_DATE,
    motivo              TEXT,
    estado              VARCHAR(50) DEFAULT 'Pendiente',
    id_paciente         INT,
    id_hospital_origen  INT REFERENCES hospital(id_hospital) DEFAULT 1,
    id_hospital_destino INT REFERENCES hospital(id_hospital)
);

-- =============================================================
-- REPLICA PARCIAL ASINCRONA: Fragmento critico V1 de otros nodos
-- Permite atender emergencias cuando CBBA o STCZ no estan disponibles
-- =============================================================

CREATE TABLE IF NOT EXISTS historial_replica (
    id_replica            SERIAL PRIMARY KEY,
    id_paciente           INT    NOT NULL,
    hospital_origen       VARCHAR(10) NOT NULL,  -- 'CBBA' o 'STCZ'
    tipo_sangre           VARCHAR(5),
    alergias              TEXT DEFAULT '',
    enfermedades_cronicas TEXT DEFAULT '',
    fecha_actualizacion   TIMESTAMP DEFAULT NOW(),
    UNIQUE(id_paciente, hospital_origen)
);

-- =============================================================
-- CATALOGO DE FRAGMENTACION (solo en el nodo mediador LPZ)
-- Mapa: id_paciente -> nodo donde reside el dato original
-- =============================================================

CREATE TABLE IF NOT EXISTS fragment_catalog (
    id_paciente   INT  PRIMARY KEY,
    nodo          VARCHAR(10) NOT NULL,  -- 'LPZ', 'CBBA', 'STCZ'
    id_hospital   INT,
    fecha_registro TIMESTAMP DEFAULT NOW()
);

-- =============================================================
-- LOGS DE OPERACIONES DISTRIBUIDAS (solo en mediador LPZ)
-- =============================================================

CREATE TABLE IF NOT EXISTS distributed_logs (
    id_log       SERIAL PRIMARY KEY,
    accion       VARCHAR(120),
    nodo_origen  VARCHAR(10),
    nodo_destino VARCHAR(10),
    id_paciente  INT,
    detalles     TEXT,
    estado       VARCHAR(20) DEFAULT 'OK',
    timestamp    TIMESTAMP   DEFAULT NOW()
);

-- =============================================================
-- DATOS INICIALES
-- =============================================================

INSERT INTO hospital (nombre, ciudad, direccion, telefono) VALUES
    ('Hospital Central de La Paz',       'La Paz',      'Av. Saavedra 2000, Miraflores',  '+591-2-2224444'),
    ('Hospital Regional de Cochabamba',  'Cochabamba',  'Av. Aniceto Arce 456, Centro',   '+591-4-4221122'),
    ('Hospital del Oriente',             'Santa Cruz',  'Av. Cañoto 789, Equipetrol', '+591-3-3334455')
ON CONFLICT DO NOTHING;

INSERT INTO medicamento (nombre, descripcion, dosis, fabricante) VALUES
    ('Paracetamol',   'Analgésico y antipirético',           '500mg cada 8 horas',            'Bagó Bolivia'),
    ('Ibuprofeno',    'Antiinflamatorio no esteroideo',                '400mg cada 8 horas',            'Roemmers'),
    ('Amoxicilina',   'Antibiótico de amplio espectro',           '500mg cada 8 horas por 7 dias', 'INTI'),
    ('Metformina',    'Antidiabético oral',                       '850mg con las comidas',         'Bagó Bolivia'),
    ('Enalapril',     'Antihipertensivo IECA',                         '10mg una vez al dia',           'Roemmers'),
    ('Omeprazol',     'Inhibidor de bomba de protones',                '20mg antes del desayuno',       'INTI'),
    ('Aspirina',      'Antiagregante plaquetario',                     '100mg una vez al dia',          'Bayer'),
    ('Loratadina',    'Antihistamínico',                          '10mg una vez al dia',           'Bagó Bolivia'),
    ('Captopril',     'Antihipertensivo de rescate',                   '25mg sublingual si necesario',  'Roemmers'),
    ('Diclofenaco',   'Antiinflamatorio para dolor agudo',             '75mg cada 12 horas',            'Bagó Bolivia')
ON CONFLICT DO NOTHING;

INSERT INTO doctor (nombre, apellido, especialidad, telefono, correo, id_hospital) VALUES
    ('Carlos',   'Mamani Quispe',  'Medicina General',    '70011111', 'cmamani@hclpz.bo',  1),
    ('Ana',      'Quispe Flores',  'Cardiología',    '70022222', 'aquispe@hclpz.bo',  1),
    ('Roberto',  'Flores Condori', 'Emergenciología','70033333', 'rflores@hclpz.bo',  1),
    ('María','Choque Lima',   'Pediatría',      '70044444', 'mchoque@hclpz.bo',  1),
    ('Jorge',    'Vargas Vidal',   'Neurología',     '70055555', 'jvargas@hclpz.bo',  1)
ON CONFLICT DO NOTHING;

INSERT INTO paciente (nombre, apellido, ci, fecha_nacimiento, sexo, direccion, telefono, tipo_sangre, alergias, id_hospital) VALUES
    ('Juan',   'Pérez Mamani',   '1234567',  '1985-03-15', 'M', 'Calle Murillo 123, La Paz',    '71111111', 'O+',  'Penicilina', 1),
    ('María', 'Gómez Choque', '2345678', '1990-07-22', 'F', 'Av. 6 de Agosto 456, La Paz', '72222222', 'A-',  'Ninguna',    1),
    ('Pedro',  'Ticona Apaza',       '3456789',  '1978-11-08', 'M', 'Plaza Murillo 78, La Paz',     '73333333', 'B+',  'Ibuprofeno', 1)
ON CONFLICT DO NOTHING;

INSERT INTO historial_clinico_v1 (id_paciente, tipo_sangre, alergias, enfermedades_cronicas)
SELECT id_paciente, tipo_sangre, alergias, ''
FROM paciente
WHERE id_hospital = 1
ON CONFLICT DO NOTHING;

INSERT INTO historial_clinico_v2 (id_historial, id_paciente, fecha_apertura, antecedentes, observaciones)
SELECT v1.id_historial, v1.id_paciente, CURRENT_DATE, 'Antecedentes familiares por registrar.', 'Paciente registrado en sistema distribuido.'
FROM historial_clinico_v1 v1
ON CONFLICT DO NOTHING;

INSERT INTO fragment_catalog (id_paciente, nodo, id_hospital)
SELECT id_paciente, 'LPZ', 1 FROM paciente WHERE id_hospital = 1
ON CONFLICT DO NOTHING;

-- =============================================================
-- VERIFICACION
-- =============================================================
SELECT 'hospital'           AS tabla, COUNT(*) FROM hospital
UNION ALL
SELECT 'medicamento',                  COUNT(*) FROM medicamento
UNION ALL
SELECT 'paciente (LPZ)',               COUNT(*) FROM paciente
UNION ALL
SELECT 'doctor (LPZ)',                 COUNT(*) FROM doctor
UNION ALL
SELECT 'fragment_catalog',             COUNT(*) FROM fragment_catalog;
