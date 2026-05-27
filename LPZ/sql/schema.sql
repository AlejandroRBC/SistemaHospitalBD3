-- PostgreSQL - Esquema del nodo La Paz (LPZ)
-- Basado en BD_LP.txt

CREATE TABLE IF NOT EXISTS hospital (
    id_hospital INTEGER PRIMARY KEY,
    nombre VARCHAR(100),
    ciudad VARCHAR(100),
    ip_radmin VARCHAR(50),
    puerto INTEGER,
    motor_bd VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS paciente (
    id_paciente SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100),
    fecha_nacimiento DATE,
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT,
    telefono VARCHAR(20),
    direccion TEXT,
    id_hospital INTEGER REFERENCES hospital(id_hospital)
);

CREATE TABLE IF NOT EXISTS historial_clinico (
    id_historial SERIAL PRIMARY KEY,
    id_paciente INTEGER NOT NULL REFERENCES paciente(id_paciente),
    observaciones TEXT,
    fecha TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS consulta (
    id_consulta SERIAL PRIMARY KEY,
    id_paciente INTEGER NOT NULL REFERENCES paciente(id_paciente),
    diagnostico TEXT,
    tratamiento TEXT,
    fecha TIMESTAMP DEFAULT NOW(),
    id_hospital INTEGER REFERENCES hospital(id_hospital)
);

CREATE TABLE IF NOT EXISTS replica_critica (
    id_replica SERIAL PRIMARY KEY,
    id_paciente INTEGER NOT NULL,
    hospital_origen VARCHAR(10) NOT NULL,
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT,
    fecha_actualizacion TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fragment_catalog (
    id_fragmento SERIAL PRIMARY KEY,
    tabla VARCHAR(50),
    hospital VARCHAR(10),
    ip_servidor VARCHAR(50),
    puerto INTEGER,
    motor_bd VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS distributed_logs (
    id_log SERIAL PRIMARY KEY,
    hospital_solicitante VARCHAR(10),
    hospital_destino VARCHAR(10),
    endpoint VARCHAR(100),
    estado VARCHAR(20),
    fecha TIMESTAMP DEFAULT NOW()
);
