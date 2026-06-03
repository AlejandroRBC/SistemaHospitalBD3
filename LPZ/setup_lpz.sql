-- ================================================================
-- SETUP NODO LPZ  |  SQL Server  |  Nodo Mediador Central
-- ================================================================
-- Cada nodo fragmenta SOLO sus propios datos.
-- LPZ usa sus fragmentos como tablas de trabajo en la app.
-- La reconstruccion nacional se hace en /recoleccion_datos
-- via UNION ALL entre frag_paciente_lpz + cbba + stcz.
--
-- Fragmentos que crea este script:
--   frag_paciente_lpz   : horizontal primaria (id_hospital = 1)
--   frag_doctor_lpz     : horizontal primaria (id_hospital = 1)
--   historial_clinico_v1: vertical — columnas criticas
--   historial_clinico_v2: vertical — columnas pesadas (solo LPZ)
--   frag_consulta_lpz   : horizontal derivada (hereda de paciente LPZ)
--   frag_emergencia_lpz : horizontal derivada
--   frag_transferencia_lpz: horizontal derivada
--
-- Catalogos sin fragmentar (replica completa en los 3 nodos):
--   hospital, medicamento
--
-- Tablas exclusivas del mediador:
--   historial_replica, fragment_catalog, distributed_logs
-- ================================================================

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'hospital_lpz')
    CREATE DATABASE hospital_lpz;
GO
USE hospital_lpz;
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
-- FRAGMENTO HORIZONTAL PRIMARIO: frag_paciente_lpz
-- Criterio: id_hospital = 1  |  IDs: 1 – 9 999
-- La app usa esta tabla en lugar de una tabla 'paciente' global.
-- IDENTITY(1,1) para que nuevos pacientes obtengan ID automatico.
-- ================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='frag_paciente_lpz' AND xtype='U')
CREATE TABLE frag_paciente_lpz (
    id_paciente      INT           IDENTITY(1,1) PRIMARY KEY,
    nombre           VARCHAR(100)  NOT NULL,
    apellido         VARCHAR(100)  NOT NULL,
    ci               VARCHAR(20)   UNIQUE,
    fecha_nacimiento DATE,
    sexo             VARCHAR(15),
    direccion        VARCHAR(250),
    telefono         VARCHAR(20),
    tipo_sangre      VARCHAR(5),
    alergias         NVARCHAR(MAX) DEFAULT '',
    id_hospital      INT           DEFAULT 1
);
GO

-- ================================================================
-- FRAGMENTO HORIZONTAL PRIMARIO: frag_doctor_lpz
-- Criterio: id_hospital = 1
-- ================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='frag_doctor_lpz' AND xtype='U')
CREATE TABLE frag_doctor_lpz (
    id_doctor    INT          IDENTITY(1,1) PRIMARY KEY,
    nombre       VARCHAR(100) NOT NULL,
    apellido     VARCHAR(100) NOT NULL,
    especialidad VARCHAR(120),
    telefono     VARCHAR(20),
    correo       VARCHAR(120),
    id_hospital  INT          DEFAULT 1
);
GO

-- ================================================================
-- FRAGMENTACION VERTICAL: historial_clinico  →  V1 + V2
--
-- historial_clinico_v1  (columnas criticas — se replican entre nodos)
--   Contiene: tipo_sangre, alergias, enfermedades_cronicas
--
-- historial_clinico_v2  (columnas pesadas — quedan SOLO en LPZ)
--   Contiene: fecha_apertura, antecedentes, observaciones
-- ================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='historial_clinico_v1' AND xtype='U')
CREATE TABLE historial_clinico_v1 (
    id_historial          INT          IDENTITY(1,1) PRIMARY KEY,
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
-- FRAGMENTO HORIZONTAL DERIVADO: frag_consulta_lpz
-- Hereda la fragmentacion de frag_paciente_lpz (id_hospital = 1)
-- ================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='frag_consulta_lpz' AND xtype='U')
CREATE TABLE frag_consulta_lpz (
    id_consulta INT          IDENTITY(1,1) PRIMARY KEY,
    fecha       DATE         DEFAULT CAST(GETDATE() AS DATE),
    hora        TIME         DEFAULT CAST(GETDATE() AS TIME),
    motivo      NVARCHAR(MAX),
    diagnostico NVARCHAR(MAX),
    id_paciente INT,
    id_doctor   INT,
    id_hospital INT          DEFAULT 1
);
GO

-- ================================================================
-- FRAGMENTO HORIZONTAL DERIVADO: frag_emergencia_lpz
-- Hereda de hospital LPZ (id_hospital = 1)
-- Nota: emergencia de paciente LPZ ocurrida en STCZ queda en STCZ.
-- ================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='frag_emergencia_lpz' AND xtype='U')
CREATE TABLE frag_emergencia_lpz (
    id_emergencia   INT          IDENTITY(1,1) PRIMARY KEY,
    fecha           DATE         DEFAULT CAST(GETDATE() AS DATE),
    hora            TIME         DEFAULT CAST(GETDATE() AS TIME),
    tipo_emergencia VARCHAR(120),
    estado_paciente VARCHAR(120),
    observaciones   NVARCHAR(MAX),
    id_paciente     INT,
    id_hospital     INT          DEFAULT 1
);
GO

-- ================================================================
-- FRAGMENTO HORIZONTAL DERIVADO: frag_transferencia_lpz
-- Transferencias cuyo hospital_origen = 1 (LPZ)
-- ================================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='frag_transferencia_lpz' AND xtype='U')
CREATE TABLE frag_transferencia_lpz (
    id_transferencia    INT          IDENTITY(1,1) PRIMARY KEY,
    fecha_transferencia DATE         DEFAULT CAST(GETDATE() AS DATE),
    motivo              NVARCHAR(MAX),
    estado              VARCHAR(50)  DEFAULT 'Pendiente',
    id_paciente         INT,
    id_hospital_origen  INT          DEFAULT 1,
    id_hospital_destino INT
);
GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='receta' AND xtype='U')
CREATE TABLE receta (
    id_receta    INT          IDENTITY(1,1) PRIMARY KEY,
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

-- ================================================================
-- TABLAS EXCLUSIVAS DEL MEDIADOR LPZ
-- ================================================================

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

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='fragment_catalog' AND xtype='U')
CREATE TABLE fragment_catalog (
    id_paciente    INT         PRIMARY KEY,
    nodo           VARCHAR(10) NOT NULL,
    id_hospital    INT,
    fecha_registro DATETIME    DEFAULT GETDATE()
);
GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='distributed_logs' AND xtype='U')
CREATE TABLE distributed_logs (
    id_log       INT          IDENTITY(1,1) PRIMARY KEY,
    accion       VARCHAR(120),
    nodo_origen  VARCHAR(10),
    nodo_destino VARCHAR(10),
    id_paciente  INT,
    detalles     NVARCHAR(MAX),
    estado       VARCHAR(20)  DEFAULT 'OK',
    timestamp    DATETIME     DEFAULT GETDATE()
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
-- DATOS INICIALES — FRAGMENTO LPZ  (solo id_hospital = 1)
-- ================================================================

-- Doctores LPZ
SET IDENTITY_INSERT frag_doctor_lpz ON;
IF NOT EXISTS (SELECT 1 FROM frag_doctor_lpz WHERE id_doctor=1) INSERT INTO frag_doctor_lpz(id_doctor,nombre,apellido,especialidad,telefono,correo,id_hospital) VALUES(1,'Carlos','Mamani Quispe','Medicina General','70011111','cmamani@hclpz.bo',1);
IF NOT EXISTS (SELECT 1 FROM frag_doctor_lpz WHERE id_doctor=2) INSERT INTO frag_doctor_lpz(id_doctor,nombre,apellido,especialidad,telefono,correo,id_hospital) VALUES(2,'Ana','Quispe Flores','Cardiología','70022222','aquispe@hclpz.bo',1);
IF NOT EXISTS (SELECT 1 FROM frag_doctor_lpz WHERE id_doctor=3) INSERT INTO frag_doctor_lpz(id_doctor,nombre,apellido,especialidad,telefono,correo,id_hospital) VALUES(3,'Roberto','Flores Condori','Emergenciología','70033333','rflores@hclpz.bo',1);
IF NOT EXISTS (SELECT 1 FROM frag_doctor_lpz WHERE id_doctor=4) INSERT INTO frag_doctor_lpz(id_doctor,nombre,apellido,especialidad,telefono,correo,id_hospital) VALUES(4,'María','Choque Lima','Pediatría','70044444','mchoque@hclpz.bo',1);
IF NOT EXISTS (SELECT 1 FROM frag_doctor_lpz WHERE id_doctor=5) INSERT INTO frag_doctor_lpz(id_doctor,nombre,apellido,especialidad,telefono,correo,id_hospital) VALUES(5,'Jorge','Vargas Vidal','Neurología','70055555','jvargas@hclpz.bo',1);
SET IDENTITY_INSERT frag_doctor_lpz OFF;
DBCC CHECKIDENT ('frag_doctor_lpz', RESEED, 5);
GO

-- Pacientes LPZ
SET IDENTITY_INSERT frag_paciente_lpz ON;
IF NOT EXISTS (SELECT 1 FROM frag_paciente_lpz WHERE ci='1234567') INSERT INTO frag_paciente_lpz(id_paciente,nombre,apellido,ci,fecha_nacimiento,sexo,direccion,telefono,tipo_sangre,alergias,id_hospital) VALUES(1,'Juan','Pérez Mamani','1234567','1985-03-15','M','Calle Murillo 123, La Paz','71111111','O+','Penicilina',1);
IF NOT EXISTS (SELECT 1 FROM frag_paciente_lpz WHERE ci='2345678') INSERT INTO frag_paciente_lpz(id_paciente,nombre,apellido,ci,fecha_nacimiento,sexo,direccion,telefono,tipo_sangre,alergias,id_hospital) VALUES(2,'María','Gómez Choque','2345678','1990-07-22','F','Av. 6 de Agosto 456, La Paz','72222222','A-','Ninguna',1);
IF NOT EXISTS (SELECT 1 FROM frag_paciente_lpz WHERE ci='3456789') INSERT INTO frag_paciente_lpz(id_paciente,nombre,apellido,ci,fecha_nacimiento,sexo,direccion,telefono,tipo_sangre,alergias,id_hospital) VALUES(3,'Pedro','Ticona Apaza','3456789','1978-11-08','M','Plaza Murillo 78, La Paz','73333333','B+','Ibuprofeno',1);
SET IDENTITY_INSERT frag_paciente_lpz OFF;
DBCC CHECKIDENT ('frag_paciente_lpz', RESEED, 3);
GO

-- Historial V1 (fragmento vertical critico — pacientes LPZ)
SET IDENTITY_INSERT historial_clinico_v1 ON;
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v1 WHERE id_paciente=1) INSERT INTO historial_clinico_v1(id_historial,id_paciente,tipo_sangre,alergias,enfermedades_cronicas) VALUES(1,1,'O+','Penicilina','');
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v1 WHERE id_paciente=2) INSERT INTO historial_clinico_v1(id_historial,id_paciente,tipo_sangre,alergias,enfermedades_cronicas) VALUES(2,2,'A-','Ninguna','Hipertension leve');
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v1 WHERE id_paciente=3) INSERT INTO historial_clinico_v1(id_historial,id_paciente,tipo_sangre,alergias,enfermedades_cronicas) VALUES(3,3,'B+','Ibuprofeno','');
SET IDENTITY_INSERT historial_clinico_v1 OFF;
DBCC CHECKIDENT ('historial_clinico_v1', RESEED, 3);
GO

-- Historial V2 (fragmento vertical notas pesadas — quedan SOLO en LPZ)
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v2 WHERE id_historial=1) INSERT INTO historial_clinico_v2(id_historial,id_paciente,fecha_apertura,antecedentes,observaciones) VALUES(1,1,'2026-01-10','Antecedentes familiares por evaluar.','Paciente LPZ registrado.');
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v2 WHERE id_historial=2) INSERT INTO historial_clinico_v2(id_historial,id_paciente,fecha_apertura,antecedentes,observaciones) VALUES(2,2,'2026-01-15','Madre hipertensa.','Control mensual de presion.');
IF NOT EXISTS (SELECT 1 FROM historial_clinico_v2 WHERE id_historial=3) INSERT INTO historial_clinico_v2(id_historial,id_paciente,fecha_apertura,antecedentes,observaciones) VALUES(3,3,'2026-02-01','Sin antecedentes relevantes.','Paciente LPZ registrado.');
GO

-- Consultas LPZ
SET IDENTITY_INSERT frag_consulta_lpz ON;
IF NOT EXISTS (SELECT 1 FROM frag_consulta_lpz WHERE id_consulta=1) INSERT INTO frag_consulta_lpz(id_consulta,fecha,hora,motivo,diagnostico,id_paciente,id_doctor,id_hospital) VALUES(1,'2026-05-10','09:30','Dolor de cabeza persistente','Cefalea tensional.',1,1,1);
IF NOT EXISTS (SELECT 1 FROM frag_consulta_lpz WHERE id_consulta=2) INSERT INTO frag_consulta_lpz(id_consulta,fecha,hora,motivo,diagnostico,id_paciente,id_doctor,id_hospital) VALUES(2,'2026-05-11','10:00','Chequeo cardiaco rutinario','Sin anomalias detectadas.',2,2,1);
SET IDENTITY_INSERT frag_consulta_lpz OFF;
DBCC CHECKIDENT ('frag_consulta_lpz', RESEED, 2);
GO

-- Emergencias LPZ
SET IDENTITY_INSERT frag_emergencia_lpz ON;
IF NOT EXISTS (SELECT 1 FROM frag_emergencia_lpz WHERE id_emergencia=1) INSERT INTO frag_emergencia_lpz(id_emergencia,fecha,hora,tipo_emergencia,estado_paciente,observaciones,id_paciente,id_hospital) VALUES(1,'2026-05-13','22:10','Accidente de transito','Critico','Politraumatismo. UCI.',3,1);
SET IDENTITY_INSERT frag_emergencia_lpz OFF;
DBCC CHECKIDENT ('frag_emergencia_lpz', RESEED, 1);
GO

-- Inicializar catalogo de fragmentacion (mediador LPZ)
INSERT INTO fragment_catalog(id_paciente, nodo, id_hospital)
SELECT id_paciente, 'LPZ', 1 FROM frag_paciente_lpz
WHERE NOT EXISTS (SELECT 1 FROM fragment_catalog fc WHERE fc.id_paciente = frag_paciente_lpz.id_paciente);
GO

-- ================================================================
-- RECONSTRUCCION NACIONAL  (query que usa /recoleccion_datos)
-- LPZ consulta los 3 fragmentos y los une con UNION ALL.
-- Esta query NO se ejecuta aqui, es para referencia.
-- ================================================================
/*
  SELECT id_paciente, nombre, apellido, ci, tipo_sangre, alergias, 'LPZ' AS nodo
  FROM frag_paciente_lpz                     -- local SQL Server
UNION ALL
  SELECT id_paciente, nombre, apellido, ci, tipo_sangre, alergias, 'CBBA' AS nodo
  FROM frag_paciente_cbba                    -- remoto PostgreSQL (psycopg2)
UNION ALL
  SELECT id_paciente, nombre, apellido, ci, tipo_sangre, alergias, 'STCZ' AS nodo
  FROM frag_paciente_stcz                    -- remoto SQL Server (pyodbc)
*/

-- ================================================================
-- VERIFICACION
-- ================================================================
SELECT 'frag_paciente_lpz'    AS fragmento, COUNT(*) AS n FROM frag_paciente_lpz
UNION ALL SELECT 'frag_doctor_lpz',          COUNT(*) FROM frag_doctor_lpz
UNION ALL SELECT 'historial_clinico_v1',     COUNT(*) FROM historial_clinico_v1
UNION ALL SELECT 'historial_clinico_v2',     COUNT(*) FROM historial_clinico_v2
UNION ALL SELECT 'frag_consulta_lpz',        COUNT(*) FROM frag_consulta_lpz
UNION ALL SELECT 'frag_emergencia_lpz',      COUNT(*) FROM frag_emergencia_lpz
UNION ALL SELECT 'hospital (catalogo)',       COUNT(*) FROM hospital
UNION ALL SELECT 'medicamento (catalogo)',    COUNT(*) FROM medicamento
UNION ALL SELECT 'fragment_catalog',         COUNT(*) FROM fragment_catalog;
GO

-- ================================================================
-- LINKED SERVERS (ejecutar manualmente en SSMS)
-- ================================================================
-- CBBA_LINK: LPZ SQL Server → CBBA PostgreSQL
/*
EXEC sp_addlinkedserver @server=N'CBBA_LINK', @srvproduct=N'PostgreSQL',
    @provider=N'MSDASQL', @provstr=N'DSN=CBBA_POSTGRES;UID=postgres;PWD=admin;';
EXEC sp_addlinkedsrvlogin @rmtsrvname=N'CBBA_LINK',@useself=N'FALSE',@rmtuser=N'postgres',@rmtpassword=N'admin';
SELECT TOP 3 * FROM OPENQUERY(CBBA_LINK, 'SELECT * FROM frag_paciente_cbba');
*/
-- STCZ_LINK: LPZ SQL Server → STCZ SQL Server
/*
EXEC sp_addlinkedserver @server=N'STCZ_LINK',@srvproduct=N'',
    @provider=N'SQLNCLI',@datasrc=N'26.29.199.177,1433',@catalog=N'hospital_stcz';
EXEC sp_addlinkedsrvlogin @rmtsrvname=N'STCZ_LINK',@useself=N'FALSE',@rmtuser=N'sa',@rmtpassword=N'123456';
SELECT TOP 3 * FROM STCZ_LINK.hospital_stcz.dbo.frag_paciente_stcz;
*/
GO
