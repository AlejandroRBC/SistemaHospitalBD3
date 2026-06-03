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
Motor    : Microsoft SQL Server (sin cambios)
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
IP LPZ  : 26.91.247.115 (mediador central - ahora SQL Server)
IP CBBA : 26.8.33.47    (ahora PostgreSQL)

COLORES (Bandera Departamento Santa Cruz)
------------------------------------------
Verde oscuro: #1B5E20  (franjas verdes 1, 3 y 5)
Blanco      : #FFFFFF  (franjas blancas 2 y 4)

==============================================================
COMO LEVANTAR EL NODO STCZ
==============================================================

1. INSTALAR DEPENDENCIAS
   pip install -r requirements.txt

2. CREAR LA BASE DE DATOS EN SQL SERVER
   sqlcmd -S localhost -U sa -P 123456 -i setup_stcz.sql

3. CONFIGURAR LINKED SERVER (para OPENQUERY a LPZ SQL Server):
   Ver bloque comentado en setup_stcz.sql.
   LPZ es ahora SQL Server — enlace MUCHO MAS SIMPLE que antes!
   Ya no necesita driver PostgreSQL ODBC, es SQL Server a SQL Server estandar:

   EXEC sp_addlinkedserver
       @server = N'LPZ_LINK',
       @provider = N'SQLNCLI',
       @datasrc = N'26.91.247.115,1433',
       @catalog = N'hospital_lpz';

4. VERIFICAR IP EN config.py
   Si la IP de STCZ cambia, actualizar tambien en config.py de CBBA y LPZ.

5. LEVANTAR LA APLICACION
   python app.py
   -> Acceso local: http://localhost:5002
   -> Acceso red  : http://26.116.149.11:5002

==============================================================
CAMBIOS RESPECTO A LA VERSION ANTERIOR
==============================================================

STCZ mantiene SQL Server. Los cambios relevantes son:

1. LINKED SERVER a LPZ:
   ANTES: LPZ era PostgreSQL. El Linked Server necesitaba psqlODBC driver
          y el SQL dentro de OPENQUERY usaba sintaxis PostgreSQL (||, ILIKE).
   AHORA: LPZ es SQL Server. El Linked Server es estandar SQL Server.
          El SQL dentro de OPENQUERY usa T-SQL (+, LIKE).

2. Ejemplo OPENQUERY actualizado (T-SQL):
   SELECT * FROM OPENQUERY(LPZ_LINK,
       'SELECT id_paciente, nombre, apellido, ci
        FROM paciente WHERE ci = ''1234567''
        OR (nombre + '' '' + apellido) LIKE ''%Juan%'''
   );

3. Ya NO necesita instalar PostgreSQL ODBC Driver en la maquina STCZ.

==============================================================
PREREQUISITOS EN LA MAQUINA STCZ
==============================================================

Software requerido:
  - SQL Server (cualquier edicion, Express funciona)
  - Python 3.10+
  - ODBC Driver 17 for SQL Server
  - RadminVPN activo y conectado

(Ya NO se necesita PostgreSQL ODBC Driver — LPZ es ahora SQL Server)

Verificar conectividad antes de arrancar:
  ping 26.91.247.115   (LPZ debe responder)
  ping 26.8.33.47      (CBBA debe responder)

==============================================================
NOTAS IMPORTANTES
==============================================================

- IP RadminVPN STCZ: 26.116.149.11 (verificar en config.py)
- Si LPZ no esta disponible, STCZ opera en modo autonomo local
- Los IDs de pacientes STCZ empiezan en 20000 (IDENTITY 20000,1)
- CBBA ahora es PostgreSQL — STCZ NO conecta directamente a CBBA,
  solo a LPZ via Linked Server o HTTP.
