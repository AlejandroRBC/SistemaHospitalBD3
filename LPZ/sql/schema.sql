-- PostgreSQL - Esquema del nodo La Paz (LPZ)

CREATE TABLE IF NOT EXISTS paciente (
    id_paciente SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT,
    id_hospital INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS historial_clinico (
    id_historial SERIAL PRIMARY KEY,
    id_paciente INTEGER NOT NULL REFERENCES paciente(id_paciente),
    observaciones TEXT,
    fecha TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS replica_critica (
    id_replica SERIAL PRIMARY KEY,
    id_paciente INTEGER NOT NULL,
    hospital_origen VARCHAR(10) NOT NULL,
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT
);
