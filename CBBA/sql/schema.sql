-- SQL Server - Esquema del nodo Cochabamba (CBBA)
-- Basado en BD_CBBA.txt

CREATE TABLE paciente_cbba (
    id_paciente INT PRIMARY KEY IDENTITY(1,1),
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100),
    fecha_nacimiento DATE,
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT,
    telefono VARCHAR(20),
    direccion TEXT,
    id_hospital INTEGER DEFAULT 2
);

CREATE TABLE historial_cbba (
    id_historial INT PRIMARY KEY IDENTITY(1,1),
    id_paciente INT NOT NULL REFERENCES paciente_cbba(id_paciente),
    observaciones TEXT,
    fecha DATETIME DEFAULT GETDATE()
);

CREATE TABLE consulta_cbba (
    id_consulta INT PRIMARY KEY IDENTITY(1,1),
    id_paciente INT NOT NULL REFERENCES paciente_cbba(id_paciente),
    diagnostico TEXT,
    tratamiento TEXT,
    fecha DATETIME DEFAULT GETDATE()
);

CREATE TABLE replica_critica_cbba (
    id_replica INT PRIMARY KEY IDENTITY(1,1),
    id_paciente INT NOT NULL,
    hospital_origen VARCHAR(10) NOT NULL,
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT,
    fecha_actualizacion DATETIME DEFAULT GETDATE()
);
