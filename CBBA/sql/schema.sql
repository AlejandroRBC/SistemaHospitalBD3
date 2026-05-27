-- SQL Server - Esquema del nodo Cochabamba (CBBA)

CREATE TABLE paciente (
    id_paciente INT PRIMARY KEY IDENTITY(1,1),
    nombre VARCHAR(100) NOT NULL,
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT,
    id_hospital INTEGER DEFAULT 2
);

CREATE TABLE historial_clinico (
    id_historial INT PRIMARY KEY IDENTITY(1,1),
    id_paciente INT NOT NULL REFERENCES paciente(id_paciente),
    observaciones TEXT,
    fecha DATETIME DEFAULT GETDATE()
);

CREATE TABLE replica_critica (
    id_replica INT PRIMARY KEY IDENTITY(1,1),
    id_paciente INT NOT NULL,
    hospital_origen VARCHAR(10) NOT NULL,
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT
);
