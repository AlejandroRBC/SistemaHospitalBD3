==============================================================
NODO LPZ — Hospital Central de La Paz
SISTEMA HOSPITALARIO DISTRIBUIDO - BD3 UMSA 2026
==============================================================

ROL DEL NODO
------------
LPZ es el NODO MEDIADOR CENTRAL del sistema distribuido.
No es solo un hospital: es el coordinador de toda la red.
Actua bajo el esquema Mediador-Envoltorio (Wrapper/Mediator).

MOTOR DE BASE DE DATOS
----------------------
Motor    : PostgreSQL 16
BD local : hospital_lpz
Puerto   : 5432
Usuario  : postgres

TECNOLOGIA DE APLICACION
------------------------
Framework : Flask 3.0
Puerto    : 5000
Host      : 0.0.0.0 (acepta conexiones de toda la red RadminVPN)
Arranque  : python app.py

IP RADMINVPN
------------
IP LPZ  : 26.91.247.115
IP CBBA : 26.8.33.47
IP STCZ : 26.XX.XX.XX (configurar segun la maquina de Santa Cruz)

COLORES (Bandera Departamento La Paz)
--------------------------------------
Rojo  : #B22222  (banda superior de la bandera)
Dorado: #FFD700  (banda inferior de la bandera)

==============================================================
COMO LEVANTAR EL NODO LPZ
==============================================================

1. INSTALAR DEPENDENCIAS
   pip install -r requirements.txt

2. CREAR LA BASE DE DATOS EN POSTGRESQL
   psql -U postgres -c "CREATE DATABASE hospital_lpz;"

3. EJECUTAR EL SCRIPT DE SETUP
   psql -U postgres -d hospital_lpz -f setup_lpz.sql

4. CONFIGURAR LAS IPs EN config.py
   - Verificar la IP de CBBA (CBBA_SQL['server'])
   - Verificar la IP de STCZ (STCZ_SQL['server'])
   - Cambiar contrasenas si es necesario

5. LEVANTAR LA APLICACION
   python app.py
   -> Acceso local: http://localhost:5000
   -> Acceso red  : http://26.91.247.115:5000

==============================================================
TABLAS QUE MANEJA ESTE NODO
==============================================================

TABLAS PROPIAS (fragmento LPZ, id_hospital = 1):
  paciente           - Pacientes registrados en La Paz (IDs 1-9999)
  doctor             - Medicos asignados al Hospital Central de LPZ
  consulta           - Consultas medicas atendidas en LPZ
  historial_clinico_v1 - Datos criticos: tipo_sangre, alergias, enf_cronicas
  historial_clinico_v2 - Notas pesadas: antecedentes, observaciones (solo LPZ)
  emergencia         - Emergencias atendidas en el hospital LPZ
  receta             - Recetas emitidas en consultas LPZ
  receta_medicamento - Relacion receta-medicamento
  transferencias_hospitalarias - Transferencias originadas en LPZ

TABLAS DE CATALOGO NACIONAL (replicas completas):
  hospital           - Los 3 hospitales del sistema (replica sincronizacion)
  medicamento        - Catalogo de farmacos (gestionado desde LPZ, replicado)

TABLAS EXCLUSIVAS DEL MEDIADOR:
  historial_replica  - Copias criticas V1 recibidas de CBBA y STCZ
                       (permite emergencias cuando CBBA/STCZ no estan disponibles)
  fragment_catalog   - Mapa id_paciente -> nodo (LPZ/CBBA/STCZ)
                       es el "directorio" de donde esta cada paciente
  distributed_logs   - Registro de todas las operaciones entre nodos

==============================================================
CONEXIONES QUE HACE ESTE NODO
==============================================================

CONEXION LOCAL:
  psycopg2 -> PostgreSQL en localhost:5432/hospital_lpz

CONEXION A CBBA (para queries distribuidos):
  pyodbc -> SQL Server en 26.8.33.47:1433/hospital_cbba
  Driver : ODBC Driver 17 for SQL Server

CONEXION A STCZ (para queries distribuidos):
  pyodbc -> SQL Server en 26.XX.XX.XX:1433/hospital_stcz
  Driver : ODBC Driver 17 for SQL Server

RECIBE LLAMADAS DE:
  CBBA -> POST /api/replica    (replica critica de pacientes CBBA)
  CBBA -> GET  /api/buscar     (busqueda nacional)
  STCZ -> POST /api/replica    (replica critica de pacientes STCZ)
  STCZ -> GET  /api/buscar     (busqueda nacional)

==============================================================
FLUJO DE OPERACIONES CLAVE
==============================================================

1. REGISTRAR PACIENTE EN LPZ:
   - INSERT en tabla paciente (id_hospital=1)
   - INSERT en historial_clinico_v1 (datos criticos)
   - INSERT en historial_clinico_v2 (notas detalladas)
   - INSERT en fragment_catalog (id_paciente -> 'LPZ')
   - pyodbc a CBBA: INSERT en historial_replica (tipo_sangre, alergias)
   - pyodbc a STCZ: INSERT en historial_replica (tipo_sangre, alergias)

2. BUSQUEDA NACIONAL (mediador):
   - SELECT local en PostgreSQL (fragmento LPZ)
   - pyodbc a CBBA: SELECT en paciente WHERE ci/nombre
   - pyodbc a STCZ: SELECT en paciente WHERE ci/nombre
   - Union de los 3 resultados -> respuesta al solicitante

3. EMERGENCIA CRUZADA (paciente de otro nodo):
   - Consultar fragment_catalog para saber el nodo origen
   - pyodbc al nodo remoto: SELECT historial_clinico_v1
   - Si el nodo remoto falla: usar historial_replica local
   - Retornar tipo_sangre + alergias + enfermedades_cronicas

4. NUEVO MEDICAMENTO:
   - INSERT en medicamento local (PostgreSQL)
   - pyodbc a CBBA: INSERT en medicamento
   - pyodbc a STCZ: INSERT en medicamento
   (replica sincrona del catalogo nacional)

==============================================================
API ENDPOINTS (para otros nodos)
==============================================================

GET  /api/paciente/<id>       - Localiza y retorna paciente (via catalogo)
GET  /api/buscar?q=<termino>  - Busqueda nacional en los 3 nodos
GET  /api/historial_critico/<id> - Retorna V1 critico (con fallback replica)
POST /api/replica             - Recibe replica critica de CBBA o STCZ
POST /api/catalogo/registro   - Registra nuevo paciente en el catalogo
GET  /api/health              - Health check del nodo mediador

==============================================================
PREREQUISITOS EN LA MAQUINA LPZ
==============================================================

Software requerido:
  - PostgreSQL 16 instalado y corriendo
  - Python 3.10+
  - ODBC Driver 17 for SQL Server (para conectar a CBBA/STCZ)
  - RadminVPN activo y conectado con CBBA y STCZ

Verificar conectividad:
  ping 26.8.33.47   (CBBA debe responder)
  ping 26.XX.XX.XX  (STCZ debe responder)

==============================================================
NOTAS IMPORTANTES
==============================================================

- LPZ DEBE ARRANCAR PRIMERO antes que CBBA y STCZ
- Si LPZ cae, CBBA y STCZ siguen operando localmente
  pero no pueden hacer busquedas nacionales via HTTP
  (pueden intentar via Linked Server si esta configurado)
- El archivo mediator.py contiene toda la logica distribuida
- Los IDs de pacientes LPZ van de 1 a 9999
  (CBBA empieza en 10000, STCZ en 20000)
