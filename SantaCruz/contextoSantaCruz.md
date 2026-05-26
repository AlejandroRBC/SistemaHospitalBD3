# INSTRUCCIONES PARA DESARROLLAR EL NODO SANTA CRUZ (STCZ)

# Rol del sistema STCZ

Santa Cruz funcionará como:

- hospital regional autónomo
- nodo con fragmentos propios
- servidor de datos remotos
- cliente del nodo mediador LPZ

STCZ NO será mediador.

STCZ:

- almacena sus propios pacientes
- responde consultas remotas
- consulta a LPZ cuando necesita datos externos
- mantiene réplicas críticas

---

# Tecnologías obligatorias

## Backend

Python + Flask

## Base de datos

SQL Server

## Librerías Python

Instalar:

```bash id="4ym6x8"
pip install flask pyodbc requests
```

---

# Estructura recomendada del proyecto

```text id="71r4o7"
stcz_node/
│
├── app.py
├── config.py
├── db.py
├── hospital_ips.py
├── replication.py
│
├── routes/
│   ├── pacientes.py
│   ├── historial.py
│   ├── consultas.py
│   ├── replica.py
│   └── estado.py
│
├── services/
│   ├── patient_service.py
│   ├── lpz_service.py
│   └── replication_service.py
│
├── utils/
│   ├── response.py
│   └── validators.py
│
└── sql/
    ├── schema.sql
    └── seed.sql
```

---

# Objetivo principal del nodo STCZ

El sistema debe poder:

- almacenar pacientes propios
- responder consultas locales
- responder consultas remotas desde LPZ
- consultar a LPZ cuando necesita datos externos
- almacenar réplicas críticas
- demostrar comunicación distribuida

---

# CONFIGURACIONES GLOBALES IMPORTANTES

---

# Archivo: config.py

```python id="qmqg44"
DEBUG = True

PORT = 5000

LOCAL_HOSPITAL = "STCZ"

SQL_SERVER = {
    "server": "localhost",
    "database": "hospital_stcz",
    "username": "sa",
    "password": "1234"
}
```

---

# Archivo: hospital_ips.py

```python id="3g4bxy"
HOSPITALS = {
    "LPZ": "http://26.10.1.5:5000",
    "CBBA": "http://26.10.1.6:5000",
    "STCZ": "http://26.10.1.7:5000"
}
```

Todas las IPs deben centralizarse aquí.

Nunca hardcodear IPs en otros archivos.

---

# Archivo: db.py

Debe centralizar:

- conexión SQL Server
- cursor
- ejecución de queries

Ejemplo:

```python id="w9xcmn"
def get_connection():
    return pyodbc.connect(...)
```

---

# BASE DE DATOS STCZ

# SQL Server local

Nombre recomendado:

```text id="gjm0r7"
hospital_stcz
```

---

# Tablas mínimas necesarias

## paciente

```sql id="hwnm28"
CREATE TABLE paciente (
    id_paciente INT PRIMARY KEY IDENTITY(1,1),
    nombre VARCHAR(100),
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT,
    id_hospital INT
);
```

---

## historial_clinico

```sql id="a0dwyj"
CREATE TABLE historial_clinico (
    id_historial INT PRIMARY KEY IDENTITY(1,1),
    id_paciente INT,
    observaciones TEXT,
    fecha DATETIME
);
```

---

## replica_critica

```sql id="hmp7q0"
CREATE TABLE replica_critica (
    id_paciente INT,
    hospital_origen VARCHAR(10),
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT
);
```

---

# ENDPOINTS IMPORTANTES

# 1. Estado del nodo

```http id="et7pxq"
GET /estado
```

Respuesta:

```json id="l8g3lo"
{
  "hospital": "STCZ",
  "status": "activo"
}
```

---

# 2. Buscar paciente LOCAL

```http id="5f3aq2"
GET /paciente/<id>
```

Debe buscar SOLO en SQL Server local.

Nunca consultar otras sedes aquí.

---

# 3. Consulta nacional mediante LPZ

```http id="78n9p6"
GET /buscar_nacional/<id>
```

Este endpoint NO consulta directamente a CBBA.

Debe:

1. enviar solicitud a LPZ
2. LPZ decide dónde buscar
3. LPZ devuelve respuesta

Ejemplo:

```python id="v6m3xp"
requests.get(f"{LPZ_URL}/buscar_paciente/{id}")
```

---

# 4. Endpoint de réplica

```http id="5o3exr"
POST /replica
```

Debe guardar:

- tipo sangre
- alergias
- enfermedades crónicas

en:

- replica_critica

---

# SERVICIO DE COMUNICACIÓN CON LPZ

# Archivo:

lpz_service.py

Debe contener funciones reutilizables para consultar al mediador.

Ejemplo:

```python id="g4f5m2"
def buscar_paciente_nacional(patient_id):
```

Este archivo será el único autorizado para:

- requests.get()
- requests.post()

hacia LPZ.

---

# REGLAS DEL NODO STCZ

# Regla 1

STCZ solo almacena pacientes propios.

---

# Regla 2

STCZ NO consulta directamente a CBBA.

Siempre debe pasar por LPZ.

---

# Regla 3

STCZ debe responder consultas remotas enviadas por LPZ.

---

# Regla 4

STCZ puede almacenar réplicas críticas de otras sedes.

---

# Regla 5

Si LPZ cae:

- STCZ sigue funcionando localmente

---

# Regla 6

Las consultas distribuidas deben usar JSON.

---

# Regla 7

STCZ nunca debe modificar pacientes que pertenezcan a otra sede.

---

# REPLICACIÓN

STCZ debe almacenar réplicas críticas provenientes de:

- LPZ
- CBBA

Solo:

- alergias
- tipo sangre
- enfermedades crónicas

NO replicar:

- observaciones largas
- historiales completos
- archivos

---

# FLUJO ESPERADO DEL SISTEMA

Caso:
STCZ necesita datos de paciente de CBBA.

Flujo:

1.

STCZ hace:

```http id="m6r9eu"
GET /buscar_nacional/10
```

2.

STCZ envía solicitud a LPZ.

3.

LPZ identifica:

- paciente pertenece a CBBA

4.

LPZ consulta CBBA.

5.

CBBA devuelve JSON.

6.

LPZ reenvía respuesta a STCZ.

---

# OBJETIVO FINAL DE LA DEMO

STCZ debe demostrar:

- conexión real con LPZ
- almacenamiento fragmentado
- consultas distribuidas
- SQL Server funcionando
- recepción de réplicas
- comunicación HTTP mediante RadminVPN

STCZ es un nodo regional autónomo dentro del sistema distribuido.
