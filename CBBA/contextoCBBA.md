# INSTRUCCIONES PARA DESARROLLAR EL NODO COCHABAMBA (CBBA)

# Rol del sistema CBBA

Cochabamba funcionará como:

- hospital regional autónomo
- nodo con fragmentos propios
- servidor de datos remotos
- cliente del nodo mediador LPZ

CBBA NO será mediador.

CBBA:

- almacena sus propios pacientes
- responde consultas remotas
- consulta al nodo LPZ cuando necesita datos externos

---

# Tecnologías obligatorias

## Backend

Python + Flask

## Base de datos

SQL Server

## Librerías Python

Instalar:

```bash id="wcv2jc"
pip install flask pyodbc requests
```

guardalo en requirements.txt

---

# Estructura recomendada del proyecto

```text id="g9o0qa"
cbba_node/
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

# Objetivo principal del nodo CBBA

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

```python id="pr8qbd"
DEBUG = True

PORT = 5000

LOCAL_HOSPITAL = "CBBA"

SQL_SERVER = {
    "server": "localhost",
    "database": "hospital_cbba",
    "username": "sa",
    "password": "1234"
}
```

---

# Archivo: hospital_ips.py

```python id="axv77l"
HOSPITALS = {
    "LPZ": "http://26.10.1.5:5000",
    "CBBA": "http://26.10.1.6:5000",
    "STCZ": "http://26.10.1.7:5000"
}
```

Las IPs deben mantenerse únicamente aquí.

---

# Archivo: db.py

Debe centralizar:

- conexión SQL Server
- cursor
- ejecución de queries

Ejemplo:

```python id="y4s6xv"
def get_connection():
    return pyodbc.connect(...)
```

---

# BASE DE DATOS CBBA

# SQL Server local

Nombre recomendado:

```text id="x6ixdo"
hospital_cbba
```

---

# Tablas mínimas necesarias

## paciente

```sql id="2tvh3u"
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

```sql id="ljr7rf"
CREATE TABLE historial_clinico (
    id_historial INT PRIMARY KEY IDENTITY(1,1),
    id_paciente INT,
    observaciones TEXT,
    fecha DATETIME
);
```

---

## replica_critica

```sql id="6s9a7t"
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

```http id="mkdr0k"
GET /estado
```

Respuesta:

```json id="u9f7ns"
{
  "hospital": "CBBA",
  "status": "activo"
}
```

---

# 2. Buscar paciente LOCAL

```http id="8ks8v0"
GET /paciente/<id>
```

IMPORTANTE:
Debe buscar SOLO en SQL Server local.

Nunca consultar otras sedes aquí.

---

# 3. Consulta nacional mediante LPZ

```http id="b2m4t7"
GET /buscar_nacional/<id>
```

Este endpoint NO busca directamente en STCZ.

Debe:

1. enviar solicitud a LPZ
2. LPZ decide dónde buscar
3. LPZ devuelve respuesta

Ejemplo:

```python id="lqzj3v"
requests.get(f"{LPZ_URL}/buscar_paciente/{id}")
```

---

# 4. Endpoint de réplica

```http id="c3hqj2"
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

```python id="9oyg4h"
def buscar_paciente_nacional(patient_id):
```

Este archivo será el único autorizado para:

- requests.get()
- requests.post()

hacia LPZ.

---

# REGLAS DEL NODO CBBA

# Regla 1

CBBA solo almacena pacientes propios.

---

# Regla 2

CBBA NO consulta directamente a STCZ.

Siempre debe pasar por LPZ.

---

# Regla 3

CBBA debe responder consultas remotas enviadas por LPZ.

---

# Regla 4

CBBA puede almacenar réplicas críticas de otras sedes.

---

# Regla 5

Si LPZ cae:

- CBBA sigue funcionando localmente

---

# Regla 6

Las consultas distribuidas deben usar JSON.

---

# Regla 7

CBBA nunca debe modificar pacientes que pertenezcan a otra sede.

---

# REPLICACIÓN

CBBA debe almacenar réplicas críticas provenientes de:

- LPZ
- STCZ

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
CBBA necesita datos de paciente de STCZ.

Flujo:

1.

CBBA hace:

```http id="zq2r5l"
GET /buscar_nacional/10
```

2.

CBBA envía solicitud a LPZ.

3.

LPZ identifica:

- paciente pertenece a STCZ

4.

LPZ consulta STCZ.

5.

STCZ devuelve JSON.

6.

LPZ reenvía respuesta a CBBA.

---

# OBJETIVO FINAL DE LA DEMO

CBBA debe demostrar:

- conexión real con LPZ
- almacenamiento fragmentado
- consultas distribuidas
- SQL Server funcionando
- recepción de réplicas
- comunicación HTTP mediante RadminVPN

CBBA es un nodo regional autónomo dentro del sistema distribuido.
