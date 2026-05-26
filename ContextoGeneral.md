# CONTEXTO GENERAL DEL SISTEMA DISTRIBUIDO HOSPITALARIO

## Objetivo del proyecto

El proyecto consiste en desarrollar un prototipo académico de un Sistema Hospitalario Distribuido utilizando 3 computadoras conectadas mediante RadminVPN. Cada computadora representa una sede hospitalaria distinta:

- La Paz (LPZ)
- Cochabamba (CBBA)
- Santa Cruz (STCZ)

El objetivo principal NO es crear un sistema hospitalario real de producción, sino demostrar conceptos de:

- bases de datos distribuidas
- fragmentación horizontal
- consultas distribuidas
- nodo mediador
- replicación parcial
- comunicación entre máquinas
- tolerancia básica a fallos

Todo el sistema funcionará únicamente en entorno local entre las máquinas conectadas por RadminVPN.

---

# Arquitectura general

Cada sede tendrá:

- una base de datos local
- un servidor Flask local
- fragmentos propios de información
- endpoints HTTP para comunicación entre nodos

Las máquinas se comunicarán usando las IPs de RadminVPN.

Ejemplo:

- LPZ → 26.x.x.x:5000
- CBBA → 26.x.x.x:5000
- STCZ → 26.x.x.x:5000

No se utilizará:

- nube
- docker
- kubernetes
- autenticación avanzada
- microservicios complejos
- API Gateway empresarial

Todo se ejecutará localmente.

---

# Distribución de tecnologías

## La Paz (Nodo Mediador + Hospital)

- Motor BD: PostgreSQL
- Backend: Flask
- Rol:

  - hospital local
  - nodo mediador nacional
  - coordinador de consultas distribuidas

## Cochabamba

- Motor BD: SQL Server
- Backend: Flask
- Rol:

  - hospital regional
  - almacenamiento de sus propios fragmentos

## Santa Cruz

- Motor BD: SQL Server
- Backend: Flask
- Rol:

  - hospital regional
  - almacenamiento de sus propios fragmentos

---

# Fragmentación de datos

La base de datos utiliza fragmentación horizontal.

Cada hospital almacena únicamente sus propios datos.

Ejemplo:

- Pacientes registrados en LPZ → se guardan en LPZ
- Pacientes registrados en CBBA → se guardan en CBBA
- Pacientes registrados en STCZ → se guardan en STCZ

Lo mismo aplica para:

- consultas
- emergencias
- historiales
- recetas

---

# Nodo mediador (La Paz)

La Paz NO almacena todos los datos nacionales completos.

La Paz funciona como:

- coordinador
- intermediario
- router de consultas

El nodo mediador:

- recibe consultas nacionales
- identifica dónde está el fragmento correcto
- consulta remotamente a otra sede
- recibe respuestas
- devuelve resultados unificados

Ejemplo:

1. CBBA necesita historial de un paciente de STCZ
2. CBBA consulta a LPZ
3. LPZ identifica que el paciente pertenece a STCZ
4. LPZ envía solicitud a STCZ
5. STCZ responde
6. LPZ devuelve el resultado a CBBA

---

# Replicación parcial

Cada nodo tendrá una réplica parcial de datos críticos:

- tipo de sangre
- alergias
- enfermedades crónicas

Esto permitirá demostrar:

- redundancia
- acceso rápido
- tolerancia básica a desconexiones

Los datos pesados NO se replican:

- observaciones largas
- notas médicas extensas
- archivos
- imágenes

---

# Comunicación entre nodos

La comunicación será mediante:

- Flask
- HTTP
- requests
- JSON

Cada sede expondrá endpoints simples.

Ejemplo:

GET /paciente/<id>
GET /historial/<id>
GET /estado

El nodo mediador consumirá esos endpoints remotamente usando requests.

---

# Objetivos técnicos del prototipo

El sistema debe demostrar:

1. Comunicación real entre 3 computadoras
2. Consultas distribuidas
3. Fragmentación horizontal
4. Replicación parcial
5. Nodo mediador funcional
6. Uso de PostgreSQL y SQL Server simultáneamente
7. Intercambio de datos JSON
8. Manejo básico de fallos

---

# Reglas de negocio simplificadas

## Regla 1

Cada paciente pertenece a una sede origen.

## Regla 2

Solo la sede origen puede modificar datos principales del paciente.

## Regla 3

Las otras sedes pueden consultar datos mediante el nodo mediador.

## Regla 4

Toda consulta nacional pasa por La Paz.

## Regla 5

Cada sede almacena únicamente sus fragmentos locales.

## Regla 6

Los datos críticos pueden replicarse parcialmente.

## Regla 7

Los datos pesados permanecen únicamente en su sede origen.

## Regla 8

Si una sede se desconecta, las demás deben seguir funcionando localmente.

---

# Tecnologías permitidas

## Backend

- Python
- Flask

## Librerías

- requests
- psycopg2
- pyodbc

## Bases de datos

- PostgreSQL
- SQL Server

## Red

- RadminVPN

---

# Alcance del proyecto

El proyecto es únicamente académico y demostrativo.

No se busca:

- seguridad avanzada
- escalabilidad empresarial
- alta concurrencia
- despliegue cloud
- producción real

El objetivo es demostrar visual y funcionalmente una arquitectura distribuida funcionando entre varias máquinas físicas.
