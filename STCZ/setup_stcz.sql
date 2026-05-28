-- =============================================================
-- SETUP NODO STCZ (Santa Cruz) - SQL Server
-- Ejecutar: sqlcmd -S localhost -U sa -P Admin1234! -i setup_stcz.sql
-- =============================================================

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'hospital_stcz')
    CREATE DATABASE hospital_stcz;
GO

USE hospital_stcz;
GO

-- =============================================================
-- CATALOGOS NACIONALES (replicas recibidas desde LPZ)
-- =============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='hospital' AND xtype='U')
CREATE TABLE hospital (
    id_hospital INT          PRIMARY KEY,
    nombre      VARCHAR(150) NOT NULL,
    ciudad      VARCHAR(80),
    direccion   VARCHAR(250),
    telefono    VARCHAR(20)
);
GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='medicamento' AND xtype='U')
CREATE TABLE medicamento (
    id_medicamento INT          PRIMARY KEY,
    nombre         VARCHAR(120) NOT NULL,
    descripcion    NVARCHAR(MAX),
    dosis          VARCHAR(80),
    fabricante     VARCHAR(120)
);
GO

-- =============================================================
-- FRAGMENTO HORIZONTAL PRIMARIO: Paciente (id_hospital = 3)
-- IDs inician en 20000 para evitar colision con LPZ (1-9999) y CBBA (10000-19999)
-- =============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='paciente' AND xtype='U')
CREATE TABLE paciente (
    id_paciente      INT          IDENTITY(20000,1) PRIMARY KEY,
    nombre           VARCHAR(100) NOT NULL,
    apellido         VARCHAR(100) NOT NULL,
    ci               VARCHAR(20)  UNIQUE,
    fecha_nacimiento DATE,
    sexo             VARCHAR(15),
    direccion        VARCHAR(250),
    telefono         VARCHAR(20),
    tipo_sangre      VARCHAR(5),
    alergias         NVARCHAR(MAX) DEFAULT '',
    id_hospital      INT           DEFAULT 3
);
GO

-- =============================================================
-- FRAGMENTO HORIZONTAL PRIMARIO: Doctor (id_hospital = 3)
-- =============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='doctor' AND xtype='U')
CREATE TABLE doctor (
    id_doctor    INT          IDENTITY(20000,1) PRIMARY KEY,
    nombre       VARCHAR(100) NOT NULL,
    apellido     VARCHAR(100) NOT NULL,
    especialidad VARCHAR(120),
    telefono     VARCHAR(20),
    correo       VARCHAR(120),
    id_hospital  INT          DEFAULT 3
);
GO

-- =============================================================
-- FRAGMENTO HORIZONTAL DERIVADO: Consulta (hereda de Paciente)
-- =============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='consulta' AND xtype='U')
CREATE TABLE consulta (
    id_consulta INT          IDENTITY(20000,1) PRIMARY KEY,
    fecha       DATE         DEFAULT CAST(GETDATE() AS DATE),
    hora        TIME         DEFAULT CAST(GETDATE() AS TIME),
    motivo      NVARCHAR(MAX),
    diagnostico NVARCHAR(MAX),
    id_paciente INT,
    id_doctor   INT,
    id_hospital INT          DEFAULT 3
);
GO

-- =============================================================
-- FRAGMENTACION HIBRIDA: Historial Clinico
-- =============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='historial_clinico_v1' AND xtype='U')
CREATE TABLE historial_clinico_v1 (
    id_historial          INT          IDENTITY(20000,1) PRIMARY KEY,
    id_paciente           INT          UNIQUE,
    tipo_sangre           VARCHAR(5),
    alergias              NVARCHAR(MAX) DEFAULT '',
    enfermedades_cronicas NVARCHAR(MAX) DEFAULT ''
);
GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='historial_clinico_v2' AND xtype='U')
CREATE TABLE historial_clinico_v2 (
    id_historial   INT          PRIMARY KEY,
    id_paciente    INT,
    fecha_apertura DATE         DEFAULT CAST(GETDATE() AS DATE),
    antecedentes   NVARCHAR(MAX) DEFAULT '',
    observaciones  NVARCHAR(MAX) DEFAULT ''
);
GO

-- =============================================================
-- FRAGMENTO HORIZONTAL DERIVADO: Emergencia
-- =============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='emergencia' AND xtype='U')
CREATE TABLE emergencia (
    id_emergencia   INT          IDENTITY(20000,1) PRIMARY KEY,
    fecha           DATE         DEFAULT CAST(GETDATE() AS DATE),
    hora            TIME         DEFAULT CAST(GETDATE() AS TIME),
    tipo_emergencia VARCHAR(120),
    estado_paciente VARCHAR(120),
    observaciones   NVARCHAR(MAX),
    id_paciente     INT,
    id_hospital     INT          DEFAULT 3
);
GO

-- =============================================================
-- FRAGMENTO HORIZONTAL DERIVADO: Receta (hereda de Consulta)
-- =============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='receta' AND xtype='U')
CREATE TABLE receta (
    id_receta    INT          IDENTITY(20000,1) PRIMARY KEY,
    fecha        DATE         DEFAULT CAST(GETDATE() AS DATE),
    indicaciones NVARCHAR(MAX),
    id_consulta  INT
);
GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='receta_medicamento' AND xtype='U')
CREATE TABLE receta_medicamento (
    id_receta      INT,
    id_medicamento INT,
    cantidad       INT DEFAULT 1,
    PRIMARY KEY (id_receta, id_medicamento)
);
GO

-- =============================================================
-- FRAGMENTO HORIZONTAL DERIVADO: Transferencias (hospital_origen = 3)
-- =============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='transferencias_hospitalarias' AND xtype='U')
CREATE TABLE transferencias_hospitalarias (
    id_transferencia    INT          IDENTITY(20000,1) PRIMARY KEY,
    fecha_transferencia DATE         DEFAULT CAST(GETDATE() AS DATE),
    motivo              NVARCHAR(MAX),
    estado              VARCHAR(50)  DEFAULT 'Pendiente',
    id_paciente         INT,
    id_hospital_origen  INT          DEFAULT 3,
    id_hospital_destino INT
);
GO

-- =============================================================
-- REPLICA PARCIAL ASINCRONA: Fragmento critico V1 de LPZ y CBBA
-- =============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='historial_replica' AND xtype='U')
CREATE TABLE historial_replica (
    id_replica            INT          IDENTITY(1,1) PRIMARY KEY,
    id_paciente           INT          NOT NULL,
    hospital_origen       VARCHAR(10)  NOT NULL,  -- 'LPZ' o 'CBBA'
    tipo_sangre           VARCHAR(5),
    alergias              NVARCHAR(MAX) DEFAULT '',
    enfermedades_cronicas NVARCHAR(MAX) DEFAULT '',
    fecha_actualizacion   DATETIME     DEFAULT GETDATE(),
    UNIQUE(id_paciente, hospital_origen)
);
GO

-- =============================================================
-- LINKED SERVER: Conexion a LPZ PostgreSQL via ODBC 16
-- =============================================================
/*
EXEC sp_addlinkedserver
    @server     = N'LPZ_LINK',
    @srvproduct = N'PostgreSQL',
    @provider   = N'MSDASQL',
    @provstr    = N'DSN=LPZ_POSTGRES;UID=postgres;PWD=postgres;';

EXEC sp_addlinkedsrvlogin
    @rmtsrvname  = N'LPZ_LINK',
    @useself     = N'FALSE',
    @rmtuser     = N'postgres',
    @rmtpassword = N'postgres';

-- Prueba (TOP en el outer query = SQL Server; LIMIT no aplica en T-SQL):
SELECT TOP 5 * FROM OPENQUERY(LPZ_LINK, 'SELECT id_paciente, nombre, apellido, tipo_sangre, alergias FROM paciente');

-- Buscar paciente de LPZ desde STCZ (emergencia cruzada):
SELECT * FROM OPENQUERY(LPZ_LINK,
    'SELECT p.nombre, p.apellido, v1.tipo_sangre, v1.alergias, v1.enfermedades_cronicas
     FROM paciente p JOIN historial_clinico_v1 v1 ON p.id_paciente = v1.id_paciente
     WHERE p.ci = ''1234567'''
);
*/

-- =============================================================
-- DATOS INICIALES
-- =============================================================

-- hospital e id_hospital son INT simples (sin IDENTITY), se insertan directamente
IF NOT EXISTS (SELECT 1 FROM hospital WHERE id_hospital = 1)
INSERT INTO hospital VALUES (1,'Hospital Central de La Paz','La Paz','Av. Saavedra 2000, Miraflores','+591-2-2224444');
IF NOT EXISTS (SELECT 1 FROM hospital WHERE id_hospital = 2)
INSERT INTO hospital VALUES (2,'Hospital Regional de Cochabamba','Cochabamba','Av. Aniceto Arce 456, Centro','+591-4-4221122');
IF NOT EXISTS (SELECT 1 FROM hospital WHERE id_hospital = 3)
INSERT INTO hospital VALUES (3,'Hospital del Oriente','Santa Cruz','Av. Cañoto 789, Equipetrol','+591-3-3334455');
GO

-- medicamento e id_medicamento son INT simples (sin IDENTITY), se insertan directamente
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento = 1)
INSERT INTO medicamento VALUES (1,'Paracetamol','Analgésico y antipirético','500mg cada 8 horas','Bagó Bolivia');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento = 2)
INSERT INTO medicamento VALUES (2,'Ibuprofeno','Antiinflamatorio no esteroideo','400mg cada 8 horas','Roemmers');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento = 3)
INSERT INTO medicamento VALUES (3,'Amoxicilina','Antibiótico de amplio espectro','500mg cada 8 horas por 7 dias','INTI');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento = 4)
INSERT INTO medicamento VALUES (4,'Metformina','Antidiabético oral','850mg con las comidas','Bagó Bolivia');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento = 5)
INSERT INTO medicamento VALUES (5,'Enalapril','Antihipertensivo IECA','10mg una vez al dia','Roemmers');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento = 6)
INSERT INTO medicamento VALUES (6,'Omeprazol','Inhibidor de bomba de protones','20mg antes del desayuno','INTI');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento = 7)
INSERT INTO medicamento VALUES (7,'Aspirina','Antiagregante plaquetario','100mg una vez al dia','Bayer');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento = 8)
INSERT INTO medicamento VALUES (8,'Loratadina','Antihistamínico','10mg una vez al dia','Bagó Bolivia');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento = 9)
INSERT INTO medicamento VALUES (9,'Captopril','Antihipertensivo de rescate','25mg sublingual si necesario','Roemmers');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento = 10)
INSERT INTO medicamento VALUES (10,'Diclofenaco','Antiinflamatorio para dolor agudo','75mg cada 12 horas','Bagó Bolivia');
GO

INSERT INTO doctor (nombre, apellido, especialidad, telefono, correo, id_hospital)
SELECT 'Luis','Justiniano Vaca','Medicina General','30011111','ljustiniano@horiente.bo',3
WHERE NOT EXISTS (SELECT 1 FROM doctor WHERE correo='ljustiniano@horiente.bo');

INSERT INTO doctor (nombre, apellido, especialidad, telefono, correo, id_hospital)
SELECT 'Carmen','Suárez Montero','Traumatología','30022222','csuarez@horiente.bo',3
WHERE NOT EXISTS (SELECT 1 FROM doctor WHERE correo='csuarez@horiente.bo');

INSERT INTO doctor (nombre, apellido, especialidad, telefono, correo, id_hospital)
SELECT 'Fernando','Parada Cruz','Emergenciología','30033333','fparada@horiente.bo',3
WHERE NOT EXISTS (SELECT 1 FROM doctor WHERE correo='fparada@horiente.bo');
GO

INSERT INTO paciente (nombre, apellido, ci, fecha_nacimiento, sexo, direccion, telefono, tipo_sangre, alergias, id_hospital)
SELECT 'Luis','Rodríguez Suárez','6789012','1975-12-03','M','Av. San Martín 890, Santa Cruz','31111111','O-','Ibuprofeno',3
WHERE NOT EXISTS (SELECT 1 FROM paciente WHERE ci='6789012');

INSERT INTO paciente (nombre, apellido, ci, fecha_nacimiento, sexo, direccion, telefono, tipo_sangre, alergias, id_hospital)
SELECT 'Sofía','Torrico Méndez','7890123','2000-04-25','F','Calle Independencia 321, Santa Cruz','32222222','A+','Ninguna',3
WHERE NOT EXISTS (SELECT 1 FROM paciente WHERE ci='7890123');
GO

INSERT INTO historial_clinico_v1 (id_paciente, tipo_sangre, alergias, enfermedades_cronicas)
SELECT p.id_paciente, p.tipo_sangre, p.alergias, ''
FROM paciente p
WHERE NOT EXISTS (SELECT 1 FROM historial_clinico_v1 h WHERE h.id_paciente = p.id_paciente);
GO

INSERT INTO historial_clinico_v2 (id_historial, id_paciente, fecha_apertura, antecedentes, observaciones)
SELECT v1.id_historial, v1.id_paciente, CAST(GETDATE() AS DATE), 'Antecedentes por registrar.', 'Paciente registrado en sistema distribuido.'
FROM historial_clinico_v1 v1
WHERE NOT EXISTS (SELECT 1 FROM historial_clinico_v2 v2 WHERE v2.id_historial = v1.id_historial);
GO

SELECT 'hospital'        AS tabla, COUNT(*) AS registros FROM hospital
UNION ALL SELECT 'medicamento',     COUNT(*) FROM medicamento
UNION ALL SELECT 'paciente (STCZ)', COUNT(*) FROM paciente
UNION ALL SELECT 'doctor (STCZ)',   COUNT(*) FROM doctor;
