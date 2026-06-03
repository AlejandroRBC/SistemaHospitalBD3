-- ================================================================
-- SETUP NODO STCZ  |  SQL Server
-- ================================================================
-- Cada nodo fragmenta SOLO sus propios datos.
-- STCZ usa sus fragmentos como tablas de trabajo en la app.
--
-- Fragmentos que crea este script:
--   frag_paciente_stcz   : horizontal primaria (id_hospital = 3)
--   frag_doctor_stcz     : horizontal primaria (id_hospital = 3)
--   historial_clinico_v1 : vertical — columnas criticas
--   historial_clinico_v2 : vertical — columnas pesadas (solo STCZ)
--   frag_consulta_stcz   : horizontal derivada
--   frag_emergencia_stcz : horizontal derivada
--   frag_transferencia_stcz: horizontal derivada
--
-- Catalogos sin fragmentar (replica identica en los 3 nodos):
--   hospital, medicamento
--
-- Ejecutar:
--   sqlcmd -S localhost -U sa -P 123456 -i setup_stcz.sql
-- ================================================================

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'hospital_stcz')
    CREATE DATABASE hospital_stcz;
GO
USE hospital_stcz;
GO

-- ================================================================
-- CATALOGOS NACIONALES  (replica identica en LPZ, CBBA y STCZ)
-- ================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='hospital' AND xtype='U')
CREATE TABLE hospital (
    id_hospital  INT          PRIMARY KEY,
    nombre       VARCHAR(150) NOT NULL,
    ciudad       VARCHAR(80),
    direccion    VARCHAR(250),
    telefono     VARCHAR(20)
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

-- ================================================================
-- FRAGMENTO HORIZONTAL PRIMARIO: frag_paciente_stcz
-- Criterio: id_hospital = 3  |  IDs: 20000 – 29 999
-- IDENTITY(20000,1) garantiza que IDs no colisionen con
-- LPZ (1-9999) ni CBBA (10000-19999).
-- ================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='frag_paciente_stcz' AND xtype='U')
CREATE TABLE frag_paciente_stcz (
    id_paciente      INT           IDENTITY(20000,1) PRIMARY KEY,
    nombre           VARCHAR(100)  NOT NULL,
    apellido         VARCHAR(100)  NOT NULL,
    ci               VARCHAR(20)   UNIQUE,
    fecha_nacimiento DATE,
    sexo             VARCHAR(15),
    direccion        VARCHAR(250),
    telefono         VARCHAR(20),
    tipo_sangre      VARCHAR(5),
    alergias         NVARCHAR(MAX) DEFAULT '',
    id_hospital      INT           DEFAULT 3
);
GO

-- ================================================================
-- FRAGMENTO HORIZONTAL PRIMARIO: frag_doctor_stcz
-- ================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='frag_doctor_stcz' AND xtype='U')
CREATE TABLE frag_doctor_stcz (
    id_doctor    INT          IDENTITY(20000,1) PRIMARY KEY,
    nombre       VARCHAR(100) NOT NULL,
    apellido     VARCHAR(100) NOT NULL,
    especialidad VARCHAR(120),
    telefono     VARCHAR(20),
    correo       VARCHAR(120),
    id_hospital  INT          DEFAULT 3
);
GO

-- ================================================================
-- FRAGMENTACION VERTICAL: historial_clinico  →  V1 + V2
-- ================================================================

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

-- ================================================================
-- FRAGMENTOS HORIZONTALES DERIVADOS
-- ================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='frag_consulta_stcz' AND xtype='U')
CREATE TABLE frag_consulta_stcz (
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

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='frag_emergencia_stcz' AND xtype='U')
CREATE TABLE frag_emergencia_stcz (
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

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='frag_transferencia_stcz' AND xtype='U')
CREATE TABLE frag_transferencia_stcz (
    id_transferencia    INT          IDENTITY(20000,1) PRIMARY KEY,
    fecha_transferencia DATE         DEFAULT CAST(GETDATE() AS DATE),
    motivo              NVARCHAR(MAX),
    estado              VARCHAR(50)  DEFAULT 'Pendiente',
    id_paciente         INT,
    id_hospital_origen  INT          DEFAULT 3,
    id_hospital_destino INT
);
GO

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

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='historial_replica' AND xtype='U')
CREATE TABLE historial_replica (
    id_replica            INT          IDENTITY(1,1) PRIMARY KEY,
    id_paciente           INT          NOT NULL,
    hospital_origen       VARCHAR(10)  NOT NULL,
    tipo_sangre           VARCHAR(5),
    alergias              NVARCHAR(MAX) DEFAULT '',
    enfermedades_cronicas NVARCHAR(MAX) DEFAULT '',
    fecha_actualizacion   DATETIME     DEFAULT GETDATE(),
    UNIQUE(id_paciente, hospital_origen)
);
GO

-- ================================================================
-- DATOS INICIALES — CATALOGO NACIONAL (igual en los 3 nodos)
-- ================================================================

IF NOT EXISTS (SELECT 1 FROM hospital WHERE id_hospital=1) INSERT INTO hospital VALUES(1,'Hospital Central de La Paz','La Paz','Av. Saavedra 2000, Miraflores','+591-2-2224444');
IF NOT EXISTS (SELECT 1 FROM hospital WHERE id_hospital=2) INSERT INTO hospital VALUES(2,'Hospital Regional de Cochabamba','Cochabamba','Av. Aniceto Arce 456, Centro','+591-4-4221122');
IF NOT EXISTS (SELECT 1 FROM hospital WHERE id_hospital=3) INSERT INTO hospital VALUES(3,'Hospital del Oriente','Santa Cruz','Av. Cañoto 789, Equipetrol','+591-3-3334455');
GO

IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento=1)  INSERT INTO medicamento VALUES(1,'Paracetamol','Analgésico y antipirético','500mg cada 8h','Bagó Bolivia');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento=2)  INSERT INTO medicamento VALUES(2,'Ibuprofeno','Antiinflamatorio no esteroideo','400mg cada 8h','Roemmers');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento=3)  INSERT INTO medicamento VALUES(3,'Amoxicilina','Antibiótico de amplio espectro','500mg cada 8h x7d','INTI');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento=4)  INSERT INTO medicamento VALUES(4,'Metformina','Antidiabético oral','850mg con comidas','Bagó Bolivia');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento=5)  INSERT INTO medicamento VALUES(5,'Enalapril','Antihipertensivo IECA','10mg una vez al día','Roemmers');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento=6)  INSERT INTO medicamento VALUES(6,'Omeprazol','Inhibidor bomba de protones','20mg antes desayuno','INTI');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento=7)  INSERT INTO medicamento VALUES(7,'Aspirina','Antiagregante plaquetario','100mg una vez al día','Bayer');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento=8)  INSERT INTO medicamento VALUES(8,'Loratadina','Antihistamínico','10mg una vez al día','Bagó Bolivia');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento=9)  INSERT INTO medicamento VALUES(9,'Captopril','Antihipertensivo de rescate','25mg sublingual','Roemmers');
IF NOT EXISTS (SELECT 1 FROM medicamento WHERE id_medicamento=10) INSERT INTO medicamento VALUES(10,'Diclofenaco','Antiinflamatorio dolor agudo','75mg cada 12h','Bagó Bolivia');
GO

-- ================================================================
-- DATOS INICIALES — FRAGMENTO STCZ  (solo id_hospital = 3)
-- ================================================================

-- Doctores STCZ
SET IDENTITY_INSERT frag_doctor_stcz ON;
IF NOT EXISTS (SELECT 1 FROM frag_doctor_stcz WHERE id_doctor=20001) INSERT INTO frag_doctor_stcz(id_doctor,nombre,apellido,especialidad,telefono,correo,id_hospital) VALUES(20001,'Luis','Justiniano Vaca','Medicina General','30011111','ljustiniano@horiente.bo',3);
IF NOT EXISTS (SELECT 1 FROM frag_doctor_stcz WHERE id_doctor=20002) INSERT INTO frag_doctor_stcz(id_doctor,nombre,apellido,especialidad,telefono,correo,id_hospital) VALUES(20002,'Carmen','Suárez Montero','Traumatología','30022222','csuarez@horiente.bo',3);
IF NOT EXISTS (SELECT 1 FROM frag_doctor_stcz WHERE id_doctor=20003) INSERT INTO frag_doctor_stcz(id_doctor,nombre,apellido,especialidad,telefono,correo,id_hospital) VALUES(20003,'Fernando','Parada Cruz','Emergenciología','30033333','fparada@horiente.bo',3);
SET IDENTITY_INSERT frag_doctor_stcz OFF;
DBCC CHECKIDENT ('frag_doctor_stcz', RESEED, 20003);
GO

-- Pacientes STCZ
SET IDENTITY_INSERT frag_paciente_stcz ON;
IF NOT EXISTS (SELECT 1 FROM frag_paciente_stcz WHERE ci='6789012') INSERT INTO frag_paciente_stcz(id_paciente,nombre,apellido,ci,fecha_nacimiento,sexo,direccion,telefono,tipo_sangre,alergias,id_hospital) VALUES(20001,'Luis','Rodríguez Suárez','6789012','1975-12-03','M','Av. San Martín 890, Santa Cruz','31111111','O-','Ibuprofeno',3);
IF NOT EXISTS (SELECT 1 FROM frag_paciente_stcz WHERE ci='7890123') INSERT INTO frag_paciente_stcz(id_paciente,nombre,apellido,ci,fecha_nacimiento,sexo,direccion,telefono,tipo_sangre,alergias,id_hospital) VALUES(20002,'Sofía','Torrico Méndez','7890123','2000-04-25','F','Calle Independencia 321, Sta. Cruz','32222222','A+','Ninguna',3);
IF NOT EXISTS (SELECT 1 FROM frag_paciente_stcz WHERE ci='8901234') INSERT INTO frag_paciente_stcz(id_paciente,nombre,apellido,ci,fecha_nacimiento,sexo,direccion,telefono,tipo_sangre,alergias,id_hospital) VALUES(20003,'Diego','Morales Vaca','8901234','1993-08-17','M','Av. Cristo Redentor 456, Sta. Cruz','33333333','B-','Latex',3);
SET IDENTITY_INSERT frag_paciente_stcz OFF;
DBCC CHECKIDENT ('frag_paciente_stcz', RESEED, 20003);
GO

-- Historial V1 (fragmento vertical critico — pacientes STCZ)
SET IDENTITY_INSERT historial_clinico_v1 ON;
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v1 WHERE id_paciente=20001) INSERT INTO historial_clinico_v1(id_historial,id_paciente,tipo_sangre,alergias,enfermedades_cronicas) VALUES(20001,20001,'O-','Ibuprofeno','');
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v1 WHERE id_paciente=20002) INSERT INTO historial_clinico_v1(id_historial,id_paciente,tipo_sangre,alergias,enfermedades_cronicas) VALUES(20002,20002,'A+','Ninguna','');
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v1 WHERE id_paciente=20003) INSERT INTO historial_clinico_v1(id_historial,id_paciente,tipo_sangre,alergias,enfermedades_cronicas) VALUES(20003,20003,'B-','Latex','');
SET IDENTITY_INSERT historial_clinico_v1 OFF;
DBCC CHECKIDENT ('historial_clinico_v1', RESEED, 20003);
GO

-- Historial V2 (fragmento vertical notas pesadas — quedan SOLO en STCZ)
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v2 WHERE id_historial=20001) INSERT INTO historial_clinico_v2(id_historial,id_paciente,fecha_apertura,antecedentes,observaciones) VALUES(20001,20001,'2026-03-01','Sin antecedentes relevantes.','Paciente STCZ registrado.');
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v2 WHERE id_historial=20002) INSERT INTO historial_clinico_v2(id_historial,id_paciente,fecha_apertura,antecedentes,observaciones) VALUES(20002,20002,'2026-03-10','Sin antecedentes relevantes.','Paciente STCZ registrado.');
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v2 WHERE id_historial=20003) INSERT INTO historial_clinico_v2(id_historial,id_paciente,fecha_apertura,antecedentes,observaciones) VALUES(20003,20003,'2026-01-05','Alergia a latex confirmada 2020.','Evitar guantes y materiales de latex.');
GO

-- Consultas STCZ
SET IDENTITY_INSERT frag_consulta_stcz ON;
IF NOT EXISTS (SELECT 1 FROM frag_consulta_stcz WHERE id_consulta=20001) INSERT INTO frag_consulta_stcz(id_consulta,fecha,hora,motivo,diagnostico,id_paciente,id_doctor,id_hospital) VALUES(20001,'2026-05-07','08:45','Fiebre alta y malestar','Influenza estacional.',20001,20001,3);
IF NOT EXISTS (SELECT 1 FROM frag_consulta_stcz WHERE id_consulta=20002) INSERT INTO frag_consulta_stcz(id_consulta,fecha,hora,motivo,diagnostico,id_paciente,id_doctor,id_hospital) VALUES(20002,'2026-05-12','15:30','Consulta ginecologica','Sin hallazgos patologicos.',20002,20003,3);
SET IDENTITY_INSERT frag_consulta_stcz OFF;
DBCC CHECKIDENT ('frag_consulta_stcz', RESEED, 20002);
GO

-- Emergencias STCZ
SET IDENTITY_INSERT frag_emergencia_stcz ON;
IF NOT EXISTS (SELECT 1 FROM frag_emergencia_stcz WHERE id_emergencia=20001) INSERT INTO frag_emergencia_stcz(id_emergencia,fecha,hora,tipo_emergencia,estado_paciente,observaciones,id_paciente,id_hospital) VALUES(20001,'2026-05-15','17:05','Reaccion alergica severa','Grave','Anafilaxia por latex.',20003,3);
SET IDENTITY_INSERT frag_emergencia_stcz OFF;
DBCC CHECKIDENT ('frag_emergencia_stcz', RESEED, 20001);
GO

-- ================================================================
-- LINKED SERVER: STCZ → LPZ  (SQL Server a SQL Server, muy simple)
-- ================================================================
/*
EXEC sp_addlinkedserver @server=N'LPZ_LINK',@srvproduct=N'',
    @provider=N'SQLNCLI',@datasrc=N'26.91.247.115,1433',@catalog=N'hospital_lpz';
EXEC sp_addlinkedsrvlogin @rmtsrvname=N'LPZ_LINK',@useself=N'FALSE',@rmtuser=N'sa',@rmtpassword=N'123456';
-- Prueba reconstruccion parcial (LPZ desde STCZ):
SELECT TOP 3 * FROM LPZ_LINK.hospital_lpz.dbo.frag_paciente_lpz;
*/

-- ================================================================
-- VERIFICACION
-- ================================================================
SELECT 'frag_paciente_stcz'   AS fragmento, COUNT(*) AS n FROM frag_paciente_stcz
UNION ALL SELECT 'frag_doctor_stcz',         COUNT(*) FROM frag_doctor_stcz
UNION ALL SELECT 'historial_clinico_v1',     COUNT(*) FROM historial_clinico_v1
UNION ALL SELECT 'historial_clinico_v2',     COUNT(*) FROM historial_clinico_v2
UNION ALL SELECT 'frag_consulta_stcz',       COUNT(*) FROM frag_consulta_stcz
UNION ALL SELECT 'frag_emergencia_stcz',     COUNT(*) FROM frag_emergencia_stcz
UNION ALL SELECT 'hospital (catalogo)',       COUNT(*) FROM hospital
UNION ALL SELECT 'medicamento (catalogo)',    COUNT(*) FROM medicamento;
GO
