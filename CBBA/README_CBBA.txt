==============================================================
NODO CBBA — Hospital Regional de Cochabamba
SISTEMA HOSPITALARIO DISTRIBUIDO - BD3 UMSA 2026
==============================================================

ROL DEL NODO
------------
CBBA es un nodo periferico del sistema distribuido.
Gestiona de forma autonoma los pacientes de Cochabamba.
Para busquedas nacionales se comunica con el mediador LPZ.

MOTOR DE BASE DE DATOS
----------------------
Motor    : Microsoft SQL Server (cualquier version 2016+)
BD local : hospital_cbba
Puerto   : 1433
Usuario  : sa

TECNOLOGIA DE APLICACION
------------------------
Framework : Flask 3.0
Puerto    : 5001
Host      : 0.0.0.0
Arranque  : python app.py

IP RADMINVPN
------------
IP CBBA : 26.8.33.47  (esta maquina)
IP LPZ  : 26.91.247.115 (mediador central)
IP STCZ : 26.XX.XX.XX

COLORES (Bandera Departamento Cochabamba)
------------------------------------------
Verde : #2E7D32  (banda superior de la bandera)
Blanco: #FFFFFF  (banda inferior de la bandera)

==============================================================
COMO LEVANTAR EL NODO CBBA
==============================================================

1. INSTALAR DEPENDENCIAS
   pip install -r requirements.txt

2. CREAR LA BASE DE DATOS EN SQL SERVER
   Ejecutar en SSMS o sqlcmd:
   CREATE DATABASE hospital_cbba;

3. EJECUTAR EL SCRIPT DE SETUP
   sqlcmd -S localhost -U sa -P Admin1234! -i setup_cbba.sql

4. CONFIGURAR LINKED SERVER (para OPENQUERY a LPZ):
   Ver bloque comentado al final de setup_cbba.sql.
   Requiere:
   a) Instalar PostgreSQL ODBC Driver 16 (psqlODBC) en esta maquina
   b) Crear DSN del sistema:
      Panel de Control -> Herramientas Administrativas -> Origenes de datos ODBC
      -> DSN del sistema -> Agregar -> PostgreSQL Unicode(x64)
      -> DSN Name: LPZ_POSTGRES
      -> Server: 26.91.247.115  Port: 5432  Database: hospital_lpz
      -> Username: postgres  Password: postgres
   c) Ejecutar el sp_addlinkedserver del setup_cbba.sql en SSMS

5. CONFIGURAR config.py
   - Verificar SQL_DB con la contrasena correcta del SA local
   - Verificar LPZ_URL con la IP correcta de LPZ

6. LEVANTAR LA APLICACION
   python app.py
   -> Acceso local: http://localhost:5001
   -> Acceso red  : http://26.8.33.47:5001

==============================================================
TABLAS QUE MANEJA ESTE NODO
==============================================================

TABLAS PROPIAS (fragmento CBBA, id_hospital = 2):
  paciente           - Pacientes de Cochabamba (IDs desde 10000)
  doctor             - Medicos del Hospital Regional CBBA
  consulta           - Consultas medicas atendidas en CBBA
  historial_clinico_v1 - Datos criticos: tipo_sangre, alergias, enf_cronicas
  historial_clinico_v2 - Notas pesadas (quedan solo en CBBA)
  emergencia         - Emergencias atendidas en CBBA
  receta             - Recetas emitidas en CBBA
  receta_medicamento - Relacion receta-medicamento
  transferencias_hospitalarias - Transferencias con origen en CBBA

TABLAS DE CATALOGO NACIONAL (replicas recibidas de LPZ):
  hospital           - Los 3 hospitales (replica de LPZ)
  medicamento        - Catalogo de farmacos (replica de LPZ)

TABLA DE REPLICA CRITICA (recibida de LPZ y STCZ):
  historial_replica  - Copias del fragmento V1 critico de LPZ y STCZ
                       Permite emergencias sin conexion al nodo origen

==============================================================
CONEXIONES QUE HACE ESTE NODO
==============================================================

CONEXION LOCAL:
  pyodbc -> SQL Server en localhost:1433/hospital_cbba

CONEXION A LPZ (para busquedas nacionales):
  METODO 1 (prioritario): Linked Server LPZ_LINK
    OPENQUERY(LPZ_LINK, 'SELECT ... FROM paciente ...')
    Requiere PostgreSQL ODBC 16 + DSN configurado

  METODO 2 (fallback): HTTP API
    requests.get('http://26.91.247.115:5000/api/buscar?q=...')
    Se usa cuando el Linked Server no esta disponible

RECIBE LLAMADAS DE:
  LPZ -> POST /api/replica    (LPZ propaga replicas de otros nodos)
  (cualquiera puede hacer GET /api/paciente/<id> para verificar)

ENVIA A:
  LPZ -> POST /api/replica    (al registrar paciente, envia datos criticos)
  LPZ -> POST /api/catalogo/registro (notifica al catalogo de LPZ)

==============================================================
FLUJO DE OPERACIONES CLAVE
==============================================================

1. REGISTRAR PACIENTE EN CBBA:
   - INSERT local en paciente (SQL Server, id_hospital=2)
   - INSERT local en historial_clinico_v1
   - INSERT local en historial_clinico_v2
   - HTTP POST a LPZ /api/replica (datos criticos)
   - HTTP POST a LPZ /api/catalogo/registro
   (LPZ propaga la replica a STCZ automaticamente)

2. BUSQUEDA NACIONAL DESDE CBBA:
   PASO 1: Intentar OPENQUERY via Linked Server a LPZ PostgreSQL
     SELECT * FROM OPENQUERY(LPZ_LINK, 'SELECT ... FROM paciente WHERE ci=...')
   PASO 2: Si falla, HTTP GET a http://26.91.247.115:5000/api/buscar?q=...
   PASO 3: LPZ retorna resultados de los 3 nodos

3. EMERGENCIA CRUZADA (paciente de LPZ o STCZ):
   PASO 1: Buscar en historial_replica local (sin red)
     SELECT * FROM historial_replica WHERE id_paciente=? AND hospital_origen=?
   PASO 2: Si no hay replica local, HTTP GET a LPZ /api/historial_critico/<id>
   RESULTADO: tipo_sangre + alergias + enfermedades_cronicas en pantalla

4. ACTUALIZAR HISTORIAL:
   - UPDATE local historial_clinico_v1 y v2
   - HTTP POST a LPZ /api/replica (datos criticos actualizados)
   (LPZ propaga a STCZ)

==============================================================
USO DEL LINKED SERVER EN SQL SERVER
==============================================================

Una vez configurado LPZ_LINK, puede usarse directamente en SSMS:

-- Buscar paciente de LPZ desde CBBA:
SELECT * FROM OPENQUERY(LPZ_LINK,
  'SELECT p.nombre, p.apellido, v1.tipo_sangre, v1.alergias
   FROM paciente p
   JOIN historial_clinico_v1 v1 ON p.id_paciente = v1.id_paciente
   WHERE p.ci = ''1234567'''
);

-- Ver todos los hospitales del sistema:
SELECT * FROM OPENQUERY(LPZ_LINK, 'SELECT * FROM hospital');

-- Consulta distribuida: pacientes criticos de LPZ registrados hoy:
SELECT * FROM OPENQUERY(LPZ_LINK,
  'SELECT p.nombre, v1.tipo_sangre, v1.alergias
   FROM paciente p JOIN historial_clinico_v1 v1 ON p.id_paciente=v1.id_paciente
   WHERE p.id_hospital = 1'
);

==============================================================
PREREQUISITOS EN LA MAQUINA CBBA
==============================================================

Software requerido:
  - SQL Server (cualquier edicion, Express funciona)
  - SQL Server Management Studio (SSMS) recomendado
  - Python 3.10+
  - ODBC Driver 17 for SQL Server
  - PostgreSQL ODBC Driver 16 (psqlODBC 16) para el Linked Server
  - RadminVPN activo y conectado

Verificar conectividad:
  ping 26.91.247.115   (LPZ debe responder)
  ping 26.XX.XX.XX     (STCZ debe responder)

==============================================================
NOTAS IMPORTANTES
==============================================================

- Si LPZ no esta disponible, CBBA opera en modo autonomo local
- Las busquedas nacionales fallaran si tanto el Linked Server
  como el HTTP a LPZ estan caidos
- En emergencia cruzada: si hay replica local, funciona sin red
- Los IDs de pacientes CBBA empiezan en 10000 (IDENTITY 10000,1)
- La tabla hospital y medicamento son de solo lectura en CBBA
  (se modifican desde LPZ y se replican hacia aca)
