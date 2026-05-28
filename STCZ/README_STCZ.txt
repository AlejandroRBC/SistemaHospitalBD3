==============================================================
NODO STCZ — Hospital del Oriente (Santa Cruz)
SISTEMA HOSPITALARIO DISTRIBUIDO - BD3 UMSA 2026
==============================================================

ROL DEL NODO
------------
STCZ es un nodo periferico del sistema distribuido.
Gestiona de forma autonoma los pacientes de Santa Cruz.
Para busquedas nacionales se comunica con el mediador LPZ.
Escenario principal: medico de STCZ atiende paciente de LPZ
en emergencia y necesita sus datos criticos.

MOTOR DE BASE DE DATOS
----------------------
Motor    : Microsoft SQL Server (cualquier version 2016+)
BD local : hospital_stcz
Puerto   : 1433
Usuario  : sa

TECNOLOGIA DE APLICACION
------------------------
Framework : Flask 3.0
Puerto    : 5002
Host      : 0.0.0.0
Arranque  : python app.py

IP RADMINVPN
------------
IP STCZ : 26.116.149.11  (configurar segun la maquina real)
IP LPZ  : 26.91.247.115 (mediador central)
IP CBBA : 26.8.33.47

COLORES (Bandera Departamento Santa Cruz)
------------------------------------------
Verde oscuro: #1B5E20  (franjas verdes 1, 3 y 5)
Blanco      : #FFFFFF  (franjas blancas 2 y 4)
Patron      : 5 franjas horizontales verde-blanco-verde-blanco-verde

==============================================================
COMO LEVANTAR EL NODO STCZ
==============================================================

1. INSTALAR DEPENDENCIAS
   pip install -r requirements.txt

2. CREAR LA BASE DE DATOS EN SQL SERVER
   CREATE DATABASE hospital_stcz;

3. EJECUTAR EL SCRIPT DE SETUP
   sqlcmd -S localhost -U sa -P Admin1234! -i setup_stcz.sql

4. CONFIGURAR LINKED SERVER (para OPENQUERY a LPZ):
   Ver bloque comentado al final de setup_stcz.sql.
   Requiere:
   a) Instalar PostgreSQL ODBC Driver 16 (psqlODBC) en esta maquina
   b) Crear DSN del sistema:
      Panel de Control -> ODBC -> DSN del sistema -> Agregar
      -> PostgreSQL Unicode(x64)
      -> DSN Name: LPZ_POSTGRES
      -> Server: 26.91.247.115  Port: 5432  Database: hospital_lpz
   c) Ejecutar sp_addlinkedserver del setup_stcz.sql en SSMS

5. VERIFICAR IP EN config.py
   IP ya configurada: 26.116.149.11 (RadminVPN STCZ)
   STCZ_URL = 'http://26.116.149.11:5002'
   Si la IP cambia, actualizar en config.py de CBBA y LPZ tambien.

6. LEVANTAR LA APLICACION
   python app.py
   -> Acceso local: http://localhost:5002
   -> Acceso red  : http://26.116.149.11:5002

==============================================================
TABLAS QUE MANEJA ESTE NODO
==============================================================

TABLAS PROPIAS (fragmento STCZ, id_hospital = 3):
  paciente           - Pacientes de Santa Cruz (IDs desde 20000)
  doctor             - Medicos del Hospital del Oriente STCZ
  consulta           - Consultas medicas atendidas en STCZ
  historial_clinico_v1 - Datos criticos: tipo_sangre, alergias, enf_cronicas
  historial_clinico_v2 - Notas pesadas (quedan solo en STCZ)
  emergencia         - Emergencias atendidas en STCZ
                       NOTA: si un paciente de LPZ tiene emergencia en STCZ,
                       la emergencia se registra en STCZ (co-ubicacion)
  receta             - Recetas emitidas en STCZ
  receta_medicamento - Relacion receta-medicamento
  transferencias_hospitalarias - Transferencias con origen en STCZ

TABLAS DE CATALOGO NACIONAL (replicas recibidas de LPZ):
  hospital           - Los 3 hospitales (replica de LPZ)
  medicamento        - Catalogo de farmacos (replica de LPZ)

TABLA DE REPLICA CRITICA:
  historial_replica  - Copias del fragmento V1 critico de LPZ y CBBA
                       Si LPZ cae, STCZ puede atender emergencias de
                       pacientes de LPZ con datos pre-almacenados

==============================================================
CONEXIONES QUE HACE ESTE NODO
==============================================================

CONEXION LOCAL:
  pyodbc -> SQL Server en localhost:1433/hospital_stcz

CONEXION A LPZ (busquedas nacionales y replica):
  METODO 1 (prioritario): Linked Server LPZ_LINK
    OPENQUERY(LPZ_LINK, 'SELECT ... FROM paciente ...')
    Requiere PostgreSQL ODBC 16 + DSN configurado

  METODO 2 (fallback): HTTP API
    requests.get('http://26.91.247.115:5000/api/buscar?q=...')

RECIBE LLAMADAS DE:
  LPZ -> POST /api/replica    (LPZ propaga replicas de LPZ y CBBA)
  LPZ -> GET  /api/paciente/<id> (si el catalogo indica nodo STCZ)

ENVIA A:
  LPZ -> POST /api/replica    (datos criticos al registrar paciente)
  LPZ -> POST /api/catalogo/registro (actualiza catalogo del mediador)

==============================================================
ESCENARIO PRINCIPAL: EMERGENCIA CRUZADA STCZ
==============================================================

Un paciente de La Paz (Juan Perez, CI 1234567, tipo sangre O+,
alergico a Penicilina) viaja a Santa Cruz y sufre un accidente.

1. Medico de STCZ va a "Busqueda Nacional"
2. Escribe "1234567" y busca
3. STCZ intenta OPENQUERY al Linked Server LPZ_LINK
4. Si LPZ_LINK disponible: retorna datos del paciente de LPZ
5. Si LPZ_LINK falla: HTTP GET a http://26.91.247.115:5000/api/buscar
6. Medico ve resultado con nodo "LPZ"
7. Click en "Ver datos criticos"
8. STCZ busca en historial_replica local:
   SELECT * FROM historial_replica WHERE id_paciente=1 AND hospital_origen='LPZ'
9. Si hay replica: muestra "O+, Alergico a Penicilina, ..." en < 1 segundo
   Si no hay replica: HTTP al mediador LPZ /api/historial_critico/1
10. Medico puede atender correctamente al paciente

==============================================================
USO DEL LINKED SERVER EN SQL SERVER
==============================================================

Una vez configurado LPZ_LINK en SQL Server de STCZ:

-- Obtener datos criticos de paciente de LPZ:
SELECT * FROM OPENQUERY(LPZ_LINK,
  'SELECT p.nombre, p.apellido, v1.tipo_sangre, v1.alergias, v1.enfermedades_cronicas
   FROM paciente p
   JOIN historial_clinico_v1 v1 ON p.id_paciente = v1.id_paciente
   WHERE p.ci = ''1234567'''
);

-- Ver fragmento del catalogo de LPZ (TOP en el outer query; LIMIT no es T-SQL):
SELECT TOP 10 * FROM OPENQUERY(LPZ_LINK,
  'SELECT id_paciente, nodo FROM fragment_catalog ORDER BY fecha_registro DESC'
);

-- Verificar replicas que LPZ tiene de pacientes de STCZ:
SELECT * FROM OPENQUERY(LPZ_LINK,
  'SELECT * FROM historial_replica WHERE hospital_origen = ''STCZ'''
);

==============================================================
PREREQUISITOS EN LA MAQUINA STCZ
==============================================================

Software requerido:
  - SQL Server (cualquier edicion, Express funciona)
  - Python 3.10+
  - ODBC Driver 17 for SQL Server
  - PostgreSQL ODBC Driver 16 (psqlODBC 16) para el Linked Server
  - RadminVPN activo y conectado

Verificar conectividad antes de arrancar:
  ping 26.91.247.115   (LPZ debe responder)
  ping 26.8.33.47      (CBBA debe responder)

==============================================================
NOTAS IMPORTANTES
==============================================================

- IP RadminVPN STCZ configurada: 26.116.149.11 (ya definida en config.py)
- Si LPZ no esta disponible, STCZ opera en modo autonomo local
- En emergencias cruzadas, la replica local es la primera linea
  de defensa (no necesita red si los datos ya estan replicados)
- Los IDs de pacientes STCZ empiezan en 20000 (IDENTITY 20000,1)
- La emergencia de un paciente de LPZ que ocurre en STCZ
  se REGISTRA en STCZ (fragmentacion horizontal derivada del hospital)
