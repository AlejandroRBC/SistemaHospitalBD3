# INSTRUCCIONES PARA DESARROLLAR EL NODO LA PAZ (LPZ)

# Rol del sistema LPZ

La Paz será el nodo más importante del sistema distribuido.

Cumplirá dos funciones simultáneamente:

1. Hospital local

- almacena pacientes propios de LPZ
- consultas locales
- historiales locales

2. Nodo mediador nacional

- recibe consultas distribuidas
- identifica dónde está cada fragmento
- consulta otras sedes
- unifica respuestas
- devuelve resultados

---

# Tecnologías obligatorias

## Backend

Python + Flask

## Base de datos

PostgreSQL

## Librerías Python

Instalar:

```bash
pip install flask psycopg2 requests
```

## guardalo en requirements.txt

# Estructura recomendada del proyecto

```text
lpz_node/
│
├── app.py
├── config.py
├── db.py
├── fragment_catalog.py
├── hospital_ips.py
├── replication.py
├── mediator.py
├── routes/
│   ├── pacientes.py
│   ├── historial.py
│   ├── mediador.py
│   └── estado.py
│
├── services/
│   ├── patient_service.py
│   ├── distributed_service.py
│   └── remote_query_service.py
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

# Objetivo principal del nodo LPZ

El sistema debe poder:

- almacenar pacientes locales
- responder consultas locales
- recibir consultas de otros hospitales
- reenviar consultas distribuidas
- consultar remotamente CBBA y STCZ
- devolver resultados unificados

---

# CONFIGURACIONES GLOBALES IMPORTANTES

Estas configuraciones deben centralizarse para evitar modificar código manualmente en múltiples archivos.

---

# Archivo: config.py

Debe contener:

```python
DEBUG = True

PORT = 5000

LOCAL_HOSPITAL = "LPZ"

POSTGRES = {
    "host": "localhost",
    "database": "hospital_lpz",
    "user": "postgres",
    "password": "1234"
}
```

Todo el proyecto debe leer configuración desde aquí.

---

# Archivo: hospital_ips.py

IMPORTANTE:
Aquí estarán TODAS las IPs de RadminVPN.

Ejemplo:

```python
HOSPITALS = {
    "LPZ": "http://26.10.1.5:5000",
    "CBBA": "http://26.10.1.6:5000",
    "STCZ": "http://26.10.1.7:5000"
}
```

Cuando cambien IPs:

- solo se modifica este archivo.

NO poner IPs hardcodeadas en otras partes.

---

# Archivo: fragment_catalog.py

Este archivo define dónde vive cada fragmento.

Ejemplo:

```python
FRAGMENTS = {
    1: "LPZ",
    2: "CBBA",
    3: "STCZ"
}
```

Uso:

- identificar rápidamente a qué sede pertenece un paciente.

---

# Archivo: db.py

Debe contener:

- conexión PostgreSQL
- cursor global
- función helper para queries

Ejemplo:

```python
def get_connection():
    return psycopg2.connect(...)
```

Toda la app debe reutilizar esta conexión.

---

# BASE DE DATOS LPZ

# PostgreSQL local

Nombre recomendado:

```text
hospital_lpz
```

---

# Tablas mínimas necesarias

## paciente

```sql
CREATE TABLE paciente (
    id_paciente SERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT,
    id_hospital INTEGER
);
```

---

## historial_clinico

```sql
CREATE TABLE historial_clinico (
    id_historial SERIAL PRIMARY KEY,
    id_paciente INTEGER,
    observaciones TEXT,
    fecha TIMESTAMP
);
```

---

## replica_critica

Aquí se guardarán réplicas parciales.

```sql
CREATE TABLE replica_critica (
    id_paciente INTEGER,
    hospital_origen VARCHAR(10),
    tipo_sangre VARCHAR(5),
    alergias TEXT,
    enfermedades_cronicas TEXT
);
```

---

# ENDPOINTS IMPORTANTES

# 1. Estado del nodo

```http
GET /estado
```

Debe responder:

```json
{
  "hospital": "LPZ",
  "status": "activo"
}
```

Sirve para probar conectividad.

---

# 2. Buscar paciente local

```http
GET /paciente/<id>
```

Debe buscar SOLO en PostgreSQL local.

---

# 3. Consulta distribuida

```http
GET /buscar_paciente/<id>
```

Este endpoint es el más importante.

Debe:

1. revisar fragment_catalog
2. identificar hospital dueño
3. si es LPZ:

   - consultar local

4. si es remoto:

   - hacer requests.get()

5. devolver JSON unificado

---

# Ejemplo de lógica del mediador

```python
if hospital == "LPZ":
    buscar_local()

elif hospital == "CBBA":
    requests.get(CBBA_URL)

elif hospital == "STCZ":
    requests.get(STCZ_URL)
```

---

# 4. Endpoint de réplica

```http
POST /replica
```

Debe recibir:

```json
{
  "id_paciente": 10,
  "tipo_sangre": "O+",
  "alergias": "Penicilina"
}
```

Y guardar en:

- replica_critica

---

# SERVICIO DE CONSULTAS REMOTAS

# Archivo:

remote_query_service.py

Debe contener funciones reutilizables.

Ejemplo:

```python
def get_remote_patient(hospital, patient_id):
```

Este archivo será el único autorizado para hacer:

- requests.get()
- requests.post()

Así todo queda centralizado.

---

# REGLAS DEL NODO MEDIADOR

# Regla 1

LPZ NO almacena todos los pacientes nacionales.

Solo:

- sus pacientes
- réplicas críticas

---

# Regla 2

Toda consulta nacional pasa por LPZ.

---

# Regla 3

LPZ decide dónde buscar cada paciente.

---

# Regla 4

LPZ unifica respuestas distribuidas.

---

# Regla 5

LPZ debe seguir funcionando aunque otra sede se desconecte.

---

# Regla 6

Si una sede no responde:

- devolver mensaje de error controlado
- NO romper el servidor Flask

---

# Regla 7

Las consultas distribuidas usarán JSON.

---

# REPLICACIÓN

LPZ debe almacenar:

- réplicas críticas de CBBA
- réplicas críticas de STCZ

Solo:

- alergias
- tipo sangre
- enfermedades crónicas

NO replicar:

- observaciones largas
- historiales completos

---

# FLUJO ESPERADO DEL SISTEMA

Caso:
CBBA necesita datos de paciente de STCZ.

Flujo:

1.

CBBA llama:

```http
GET /buscar_paciente/10
```

2.

LPZ revisa fragment_catalog.

3.

LPZ detecta:

- paciente pertenece a STCZ

4.

LPZ hace:

```python
requests.get(STCZ_URL)
```

5.

STCZ devuelve JSON.

6.

LPZ reenvía respuesta a CBBA.

---

# OBJETIVO FINAL DE LA DEMO

La demo debe demostrar:

- 3 PCs conectadas
- PostgreSQL + SQL Server funcionando juntos
- consultas distribuidas reales
- fragmentación horizontal
- nodo mediador
- replicación parcial
- comunicación HTTP real mediante RadminVPN

El objetivo NO es producción real.
El objetivo es visualizar arquitectura distribuida funcionando correctamente.
