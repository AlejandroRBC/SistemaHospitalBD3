╔══════════════════════════════════════════════════════════════════════╗
║         NODO LPZ  —  Hospital Central de La Paz                     ║
║         SISTEMA HOSPITALARIO DISTRIBUIDO  ·  BD3 UMSA 2026          ║
╚══════════════════════════════════════════════════════════════════════╝

  Motor local : SQL Server          Puerto app : 5000
  Rol         : NODO MEDIADOR CENTRAL (coordinador de toda la red)
  IP RadminVPN: 26.91.247.115

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ÍNDICE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Arquitectura del nodo
  2. Requisitos de software
  3. Configuración rápida (paso a paso)
  4. Estructura de archivos
  5. Base de datos — tablas y fragmentación
  6. Conexiones entre nodos
  7. Rutas de la aplicación Flask
  8. API REST (endpoints para otros nodos)
  9. Vista Recolección de Datos
  10. Linked Servers en SQL Server
  11. Troubleshooting
  12. Notas de diseño

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. ARQUITECTURA DEL NODO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LPZ actúa como NODO MEDIADOR bajo el esquema Mediador-Envoltorio
(Mediator/Wrapper). No es solo un nodo de almacenamiento: es el cerebro
que coordina todas las operaciones distribuidas del sistema.

Sus 3 funciones principales:

  ┌─────────────────────────────────────────────────────────────┐
  │  CATÁLOGO DE FRAGMENTACIÓN                                  │
  │  Sabe exactamente en qué nodo vive cada paciente.           │
  │  Tabla: fragment_catalog  →  id_paciente : nodo             │
  ├─────────────────────────────────────────────────────────────┤
  │  PROCESADOR DE CONSULTAS DISTRIBUIDAS                       │
  │  Recibe una búsqueda, la divide en 3 sub-consultas y        │
  │  une los resultados de LPZ + CBBA + STCZ.                   │
  │  Archivo: mediator.py                                       │
  ├─────────────────────────────────────────────────────────────┤
  │  ENVOLVEDORES (WRAPPERS)                                    │
  │  Traduce entre SQL Server (local/STCZ) y PostgreSQL (CBBA). │
  │  pyodbc ──► SQL Server (local y STCZ)                       │
  │  psycopg2 ─► PostgreSQL (CBBA)                              │
  └─────────────────────────────────────────────────────────────┘

Diagrama de red:

          ┌────────────────────────────────────────────┐
          │           Red RadminVPN                    │
          │                                            │
          │   ┌───────────┐        ┌───────────┐      │
          │   │   CBBA    │        │   STCZ    │      │
          │   │PostgreSQL │        │SQL Server │      │
          │   │:5432/:5001│        │:1433/:5002│      │
          │   └─────┬─────┘        └─────┬─────┘      │
          │         │  psycopg2          │  pyodbc     │
          │         └──────────┬─────────┘             │
          │                    │                        │
          │            ┌───────▼───────┐               │
          │            │     LPZ       │               │
          │            │  SQL Server   │               │
          │            │  MEDIADOR     │               │
          │            │:1433 / :5000  │               │
          │            └───────────────┘               │
          └────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  2. REQUISITOS DE SOFTWARE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  OBLIGATORIOS
  ├── SQL Server 2016+  (Express Edition funciona)
  ├── SSMS  (SQL Server Management Studio) — recomendado
  ├── Python 3.10+
  ├── ODBC Driver 17 for SQL Server
  │     https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
  └── RadminVPN  (conectado a la misma red que CBBA y STCZ)

  PARA LINKED SERVER A CBBA (opcional, mejora rendimiento)
  └── PostgreSQL ODBC Driver 16 (psqlODBC 16.x)
        https://www.postgresql.org/ftp/odbc/versions/msi/

  CREDENCIALES SQL SERVER LOCAL
  ├── Servidor   : localhost,1433
  ├── Usuario    : sa
  └── Contraseña : 123456
      (ajustar en config.py si son diferentes)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  3. CONFIGURACIÓN RÁPIDA (PASO A PASO)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  PASO 1 — Instalar dependencias Python
  ──────────────────────────────────────
  pip install -r requirements.txt

  Librerías que instala:
    flask          → aplicación web
    pyodbc         → conexión SQL Server (local y STCZ)
    psycopg2-binary→ conexión PostgreSQL (CBBA remoto)
    requests       → llamadas HTTP entre nodos


  PASO 2 — Crear y poblar la base de datos
  ──────────────────────────────────────────
  sqlcmd -S localhost -U sa -P 123456 -i setup_lpz.sql

  El script hace 4 cosas en orden:
    1. Crea la base hospital_lpz
    2. Crea todas las tablas (esquema idéntico al de CBBA y STCZ)
    3. Inserta TODOS los datos nacionales (9 pacientes, 11 doctores…)
    4. Fragmenta con SELECT … INTO → crea las tablas frag_*

  Tablas de trabajo que usa la app quedan listas después del script.


  PASO 3 — Ajustar IPs en config.py (si cambian)
  ─────────────────────────────────────────────────
  Abrir LPZ/config.py y verificar:

    LPZ_DB['server']    → 'localhost'   (no cambiar)
    CBBA_PG['host']     → IP de CBBA    (actualmente 26.8.33.47)
    STCZ_SQL['server']  → IP de STCZ    (actualmente 26.29.199.177)
    CBBA_URL            → URL HTTP CBBA (actualmente http://26.8.33.47:5001)
    STCZ_URL            → URL HTTP STCZ (actualmente http://26.29.199.177:5002)


  PASO 4 — (Opcional) Configurar Linked Servers en SSMS
  ───────────────────────────────────────────────────────
  Ver sección 10 de este README.
  Mejora el rendimiento de búsquedas distribuidas pero NO es obligatorio.
  La app funciona con HTTP como fallback si los Linked Servers no están.


  PASO 5 — Levantar la aplicación
  ──────────────────────────────────
  python app.py

  Verificar en el navegador:
    Local : http://localhost:5000
    Red   : http://26.91.247.115:5000

  ⚠ LPZ DEBE INICIARSE PRIMERO.
    CBBA y STCZ dependen de sus APIs al arrancar.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  4. ESTRUCTURA DE ARCHIVOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  LPZ/
  ├── app.py            → Rutas Flask (endpoints web y API REST)
  ├── mediator.py       → Lógica distribuida: catálogo, búsqueda,
  │                        replicación, transferencias, wrappers
  ├── db.py             → Conexiones: pyodbc (local+STCZ), psycopg2 (CBBA)
  ├── config.py         → IPs, credenciales, colores, nombre del hospital
  ├── setup_lpz.sql     → Script SQL: schema + datos + fragmentación
  ├── requirements.txt  → Dependencias Python
  ├── README_LPZ.txt    → Este archivo
  └── templates/
      ├── base.html               → Navbar, estilos, layout general
      ├── index.html              → Dashboard con estadísticas y estado de red
      ├── pacientes.html          → Lista de pacientes LPZ
      ├── paciente_form.html      → Formulario nuevo paciente
      ├── paciente_detalle.html   → Detalle + historial + consultas
      ├── consultas.html          → Lista de consultas
      ├── consulta_form.html      → Formulario nueva consulta
      ├── emergencias.html        → Lista de emergencias
      ├── emergencia_form.html    → Formulario nueva emergencia
      ├── transferencias.html     → Lista de transferencias
      ├── transferencia_form.html → Formulario nueva transferencia
      ├── hospitales.html         → Catálogo de los 3 hospitales
      ├── medicamentos.html       → Catálogo de medicamentos
      ├── busqueda_nacional.html  → Búsqueda en los 3 nodos simultáneamente
      ├── emergencia_cruzada.html → Datos críticos de paciente de otro nodo
      ├── logs.html               → Log de operaciones distribuidas
      └── recoleccion_datos.html  → Vista reconstrucción de los 3 nodos

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  5. BASE DE DATOS — TABLAS Y FRAGMENTACIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  TIPO A — CATÁLOGOS (réplica completa en los 3 nodos)
  ──────────────────────────────────────────────────────
  hospital        Los 3 hospitales del sistema.
                  Se gestiona desde LPZ y se replica a CBBA y STCZ.
                  Columnas: id_hospital, nombre, ciudad, direccion, telefono

  medicamento     Catálogo nacional de fármacos.
                  Nuevo medicamento en LPZ → se replica automáticamente.
                  Columnas: id_medicamento, nombre, descripcion, dosis, fabricante


  TIPO B — FRAGMENTO HORIZONTAL LPZ (id_hospital = 1)
  ──────────────────────────────────────────────────────
  Contienen SOLO los datos de pacientes registrados en La Paz.

  paciente        IDs 1–9999. Cada fila pertenece a un solo nodo.
                  Columnas: id_paciente, nombre, apellido, ci,
                             fecha_nacimiento, sexo, direccion, telefono,
                             tipo_sangre, alergias, id_hospital

  doctor          Médicos del Hospital Central LPZ.
                  Columnas: id_doctor, nombre, apellido, especialidad,
                             telefono, correo, id_hospital

  consulta        Fragmento derivado: hereda de paciente/hospital.
  emergencia      Si un paciente de LPZ tiene emergencia en STCZ,
                  la emergencia queda en STCZ (co-ubicación física).
  receta          Recetas emitidas en LPZ.
  receta_medicamento
  transferencias_hospitalarias


  TIPO C — FRAGMENTACIÓN HÍBRIDA (vertical + horizontal)
  ─────────────────────────────────────────────────────────
  historial_clinico se divide en 2 partes:

  historial_clinico_v1  ← Fragmento VERTICAL crítico (liviano)
    Columnas: id_historial, id_paciente, tipo_sangre, alergias,
              enfermedades_cronicas
    → Se REPLICA parcialmente a CBBA y STCZ para emergencias sin red.

  historial_clinico_v2  ← Fragmento VERTICAL pesado (solo LPZ)
    Columnas: id_historial, id_paciente, fecha_apertura,
              antecedentes, observaciones
    → NO se replica. Notas largas que no viajan por la red.

  Luego sobre V1 se aplica fragmentación HORIZONTAL por nodo:
    frag_historial_critico_lpz   → V1 solo de pacientes LPZ
    frag_historial_critico_cbba  → V1 solo de pacientes CBBA
    frag_historial_critico_stcz  → V1 solo de pacientes STCZ


  TIPO D — TABLAS EXCLUSIVAS DEL MEDIADOR (solo en LPZ)
  ────────────────────────────────────────────────────────
  historial_replica   Réplicas parciales V1 recibidas de CBBA y STCZ.
                      Permite atender emergencias cruzadas cuando el
                      nodo remoto no está disponible.
                      Columnas: id_replica, id_paciente, hospital_origen,
                                tipo_sangre, alergias, enfermedades_cronicas,
                                fecha_actualizacion

  fragment_catalog    Directorio global: mapea cada id_paciente al nodo
                      donde vive su dato original.
                      Columnas: id_paciente, nodo, id_hospital, fecha_registro
                      Ejemplo:  1 → LPZ, 10001 → CBBA, 20001 → STCZ

  distributed_logs    Registro cronológico de todas las operaciones
                      entre nodos (réplicas, transferencias, búsquedas).
                      Columnas: id_log, accion, nodo_origen, nodo_destino,
                                id_paciente, detalles, estado, timestamp


  RANGOS DE IDs (para evitar colisiones entre nodos)
  ────────────────────────────────────────────────────
    Nodo LPZ  : pacientes 1     – 9 999   doctors 1     – 9 999
    Nodo CBBA : pacientes 10000 – 19 999  doctors 10000 – 19 999
    Nodo STCZ : pacientes 20000 – 29 999  doctors 20000 – 29 999

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  6. CONEXIONES ENTRE NODOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  LPZ → LOCAL (SQL Server)
    Driver  : pyodbc
    Cadena  : DRIVER={ODBC Driver 17 for SQL Server};
              SERVER=localhost,1433;DATABASE=hospital_lpz;
              UID=sa;PWD=123456;

  LPZ → CBBA (PostgreSQL remoto)
    Driver  : psycopg2
    Config  : config.CBBA_PG = { host: 26.8.33.47, port: 5432,
                                  database: hospital_cbba,
                                  user: postgres, password: admin }
    Nota    : Las queries a CBBA usan %s como placeholder y
              operadores PostgreSQL (||, ILIKE, NOW(), ON CONFLICT).

  LPZ → STCZ (SQL Server remoto)
    Driver  : pyodbc
    Config  : config.STCZ_SQL = { server: 26.29.199.177, port: 1433,
                                   database: hospital_stcz,
                                   user: sa, password: 123456 }
    Nota    : Las queries a STCZ usan ? como placeholder y
              operadores T-SQL (+, LIKE, GETDATE(), IF EXISTS).

  RECIBE PETICIONES DE:
    CBBA → POST /api/replica           réplica crítica de paciente CBBA
    CBBA → POST /api/catalogo/registro registra paciente CBBA en catálogo
    CBBA → POST /api/transferir_desde  orquesta transferencia desde CBBA
    CBBA → GET  /api/buscar            búsqueda nacional (fallback HTTP)
    STCZ → (mismos endpoints)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  7. RUTAS DE LA APLICACIÓN FLASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  GET  /                          Dashboard principal
  GET  /pacientes                 Lista pacientes LPZ
  GET  /paciente/nuevo            Formulario nuevo paciente
  POST /paciente/nuevo            Registra paciente + replica a CBBA/STCZ
  GET  /paciente/<id>             Detalle: datos + historial + consultas
  POST /historial/actualizar      Actualiza historial y sincroniza réplica

  GET  /consultas                 Lista consultas LPZ
  GET  /consulta/nueva            Formulario nueva consulta
  POST /consulta/nueva            Registra consulta

  GET  /emergencias               Lista emergencias LPZ
  GET  /emergencia/nueva          Formulario nueva emergencia
  POST /emergencia/nueva          Registra emergencia
  GET  /emergencia_cruzada/<id>   Consulta datos críticos de cualquier nodo

  GET  /transferencias            Lista transferencias
  GET  /transferencia/nueva       Formulario nueva transferencia
  POST /transferencia/nueva       Inicia transferencia (llama a mediator.py)

  GET  /hospitales                Catálogo hospitales
  GET  /medicamentos              Catálogo medicamentos
  POST /medicamento/nuevo         Agrega medicamento y replica a CBBA/STCZ

  GET  /buscar_nacional?q=<term>  Busca en los 3 nodos simultáneamente
  GET  /recoleccion_datos         Vista reconstrucción completa (3 nodos)
  GET  /logs                      Últimas 100 operaciones distribuidas

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  8. API REST  (endpoints consumidos por CBBA y STCZ)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  GET  /api/health
       Retorna estado del mediador.
       { nodo:"LPZ", estado:"activo", rol:"mediador", timestamp:... }

  GET  /api/estado_nodos
       Verifica conectividad con CBBA y STCZ vía HTTP.
       { cbba:{nombre:..., conectado:true/false}, stcz:{...} }

  GET  /api/paciente/<id>
       Localiza un paciente en cualquier nodo usando el catálogo.
       Retorna: { success, data:{...paciente}, nodo:"LPZ"|"CBBA"|"STCZ" }

  GET  /api/buscar?q=<termino>
       Búsqueda distribuida por CI o nombre en los 3 nodos.
       Retorna: { success, data:[lista], errores:{nodo:msg} }

  GET  /api/historial_critico/<id>
       Obtiene fragmento V1 de un paciente.
       Usa réplica local si el nodo origen no responde.
       Retorna: { success, data:{tipo_sangre,alergias,...}, fuente:... }

  POST /api/transferir         { id_paciente, nombre, ... }
       Recibe un paciente transferido de CBBA o STCZ hacia LPZ.
       Inserta en paciente + historial + actualiza catálogo.

  POST /api/transferir_desde   { nodo_origen, id_paciente, id_transferencia,
                                  id_hospital_destino }
       LPZ orquesta la transferencia: obtiene datos del origen,
       los inserta en el destino, actualiza catálogo y estado.

  POST /api/replica            { id_paciente, hospital_origen, tipo_sangre,
                                  alergias, enfermedades_cronicas }
       Almacena réplica crítica V1 recibida de CBBA o STCZ.
       Usa IF EXISTS / UPDATE ELSE INSERT en SQL Server.

  POST /api/catalogo/registro  { id_paciente, nodo, id_hospital }
       Registra la ubicación de un nuevo paciente en el catálogo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  9. VISTA RECOLECCIÓN DE DATOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  URL: http://26.91.247.115:5000/recoleccion_datos

  Función exclusiva del nodo mediador. Consulta en tiempo real los
  3 nodos y reconstruye la vista completa del sistema distribuido.

  Contenido por nodo (pestañas LPZ / CBBA / STCZ):
    - Pacientes con tipo de sangre y alergias
    - Historial clínico V1 (fragmento crítico)
    - Doctores por especialidad
    - Emergencias registradas

  Tabla unificada al final:
    - Todos los pacientes del sistema con su nodo de origen

  Indicadores de estado:
    - Verde  → nodo conectado y respondiendo
    - Rojo   → error de conexión (se muestra el mensaje de error)

  Datos consultados:
    LPZ  → pyodbc (SQL Server local)           sin red
    CBBA → psycopg2 (PostgreSQL 26.8.33.47)    depende de RadminVPN
    STCZ → pyodbc (SQL Server 26.29.199.177)   depende de RadminVPN

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  10. LINKED SERVERS EN SQL SERVER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Los Linked Servers permiten consultar otros nodos directamente
  con T-SQL desde SSMS, sin pasar por la app Python.

  ── CBBA_LINK (LPZ SQL Server → CBBA PostgreSQL) ──────────────
  Requisito previo: instalar PostgreSQL ODBC 16 y crear DSN.

    1. Panel de Control → Herramientas Administrativas
       → Orígenes de datos ODBC (64 bits)
       → Pestaña DSN de sistema → Agregar
       → Seleccionar: PostgreSQL Unicode(x64)
       → DSN Name  : CBBA_POSTGRES
       → Server    : 26.8.33.47
       → Port      : 5432
       → Database  : hospital_cbba
       → Username  : postgres

    2. En SSMS ejecutar:
       EXEC sp_addlinkedserver
           @server     = N'CBBA_LINK',
           @srvproduct = N'PostgreSQL',
           @provider   = N'MSDASQL',
           @provstr    = N'DSN=CBBA_POSTGRES;UID=postgres;PWD=admin;';
       EXEC sp_addlinkedsrvlogin
           @rmtsrvname  = N'CBBA_LINK',
           @useself     = N'FALSE',
           @rmtuser     = N'postgres',
           @rmtpassword = N'admin';

    3. Probar:
       SELECT TOP 5 * FROM OPENQUERY(CBBA_LINK,
           'SELECT id_paciente, nombre, apellido FROM paciente'
       );

  ── STCZ_LINK (LPZ SQL Server → STCZ SQL Server) ──────────────
  Enlace estándar SQL Server a SQL Server, sin drivers adicionales.

    EXEC sp_addlinkedserver
        @server     = N'STCZ_LINK',
        @srvproduct = N'',
        @provider   = N'SQLNCLI',
        @datasrc    = N'26.29.199.177,1433',
        @catalog    = N'hospital_stcz';
    EXEC sp_addlinkedsrvlogin
        @rmtsrvname  = N'STCZ_LINK',
        @useself     = N'FALSE',
        @rmtuser     = N'sa',
        @rmtpassword = N'123456';

    Probar con 4-part name:
      SELECT TOP 5 * FROM STCZ_LINK.hospital_stcz.dbo.paciente;

    O con OPENQUERY (T-SQL adentro):
      SELECT * FROM OPENQUERY(STCZ_LINK,
          'SELECT id_paciente, nombre, apellido, tipo_sangre
           FROM paciente WHERE id_hospital = 3'
      );

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  11. TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Error: "No module named 'pyodbc'"
  → pip install pyodbc

  Error: "No module named 'psycopg2'"
  → pip install psycopg2-binary

  Error: "Data source name not found" (pyodbc)
  → Verificar que "ODBC Driver 17 for SQL Server" esté instalado.
  → Panel de control → ODBC → Drivers → debe aparecer en la lista.

  Error: "Login failed for user 'sa'"
  → Verificar que SQL Server tenga autenticación mixta habilitada.
  → SSMS → clic derecho servidor → Properties → Security
    → Seleccionar "SQL Server and Windows Authentication mode"
  → Reiniciar el servicio SQL Server.

  Error: "Connection refused" al conectar a CBBA o STCZ
  → Verificar RadminVPN: ping 26.8.33.47 y ping 26.29.199.177
  → Verificar que CBBA y STCZ ya estén ejecutando su app.

  Error al ejecutar setup_lpz.sql: "Cannot insert explicit value..."
  → La tabla tiene IDENTITY activo. El script usa SET IDENTITY_INSERT ON.
  → Asegurarse de ejecutar el script completo de una sola vez con sqlcmd.

  La búsqueda nacional devuelve error en CBBA o STCZ
  → Es normal si el nodo está caído. Se muestra el error pero LPZ sigue.
  → Verificar RadminVPN y que la app del nodo remoto esté corriendo.

  Los logs no se guardan
  → La tabla distributed_logs debe existir. Re-ejecutar setup_lpz.sql.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  12. NOTAS DE DISEÑO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  SINTAXIS SQL POR NODO (importante en mediator.py)
  ────────────────────────────────────────────────────
  Nodo     Motor        Placeholder  Concat  Búsqueda  Upsert
  LPZ      SQL Server   ?            +       LIKE      IF EXISTS / UPDATE ELSE INSERT
  CBBA     PostgreSQL   %s           ||      ILIKE     ON CONFLICT DO UPDATE
  STCZ     SQL Server   ?            +       LIKE      IF EXISTS / UPDATE ELSE INSERT

  TOLERANCIA A FALLOS
  ────────────────────
  - Si CBBA o STCZ caen, LPZ sigue operando localmente.
  - Si LPZ cae, CBBA y STCZ operan en modo autónomo (sin búsqueda nacional).
  - Emergencias cruzadas: si el nodo origen no responde, se usa
    la réplica en historial_replica (datos pre-cacheados en LPZ).

  REPLICACIÓN PARCIAL ASÍNCRONA
  ──────────────────────────────
  Cada vez que se registra o actualiza un paciente en cualquier nodo,
  sus datos críticos (tipo_sangre, alergias, enfermedades_cronicas)
  se replican a los otros 2 nodos en segundo plano.
  Esto garantiza que una emergencia cruzada pueda atenderse incluso
  sin conexión de red entre ciudades.

  BD LOCAL  (hospital_lpz)
  ─────────────────────────
  Motor    : SQL Server
  BD       : hospital_lpz
  Puerto   : 1433
  Usuario  : sa / 123456
  Colores  : Rojo #B22222 (superior) / Dorado #FFD700 (inferior)
             (Bandera departamento La Paz)

╔══════════════════════════════════════════════════════════════════════╗
║  Sistema Hospitalario Distribuido  ·  BD3 UMSA 2026                 ║
║  Nodo LPZ  ·  Mediador Central  ·  SQL Server  ·  Flask 3.0         ║
╚══════════════════════════════════════════════════════════════════════╝
