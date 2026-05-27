# AGENTS.md — Sistema Hospitalario Distribuido

## Project status

Active prototype development. **LPZ node fully implemented** (Flask + PostgreSQL). **CBBA node fully implemented** (Flask + SQL Server). STCZ remains as a design doc. The goal is academic: demonstrate distributed DB concepts (horizontal fragmentation, mediator node, partial replication) across 3 machines connected via RadminVPN.

## Repo layout

```
SistemaHospitalario/
├── ContextoGeneral.md          # Architecture overview (start here)
├── LPZ/                        # La Paz node — mediator + local hospital (IMPLEMENTED)
│   ├── contextoLPZ.md          # Original design doc
│   ├── app.py                  # Flask entrypoint
│   ├── config.py               # PostgreSQL credentials, port
│   ├── db.py                   # psycopg2 connection helper
│   ├── hospital_ips.py         # RadminVPN IPs for all nodes
│   ├── fragment_catalog.py     # Patient-to-hospital mapping
│   ├── mediator.py             # Distributed query resolution
│   ├── replication.py          # Partial replication logic
│   ├── requirements.txt
│   ├── creacion_postgresql.txt # Full DB creation script
│   ├── routes/                 # Flask blueprints
│   ├── services/               # Business logic layer
│   ├── utils/                  # Response helpers, validators
│   ├── sql/                    # schema.sql + seed.sql
│   ├── templates/              # HTML status page (LPZ colors)
│   └── static/                 # CSS (verde/rojo)
├── CBBA/                       # Cochabamba node — regional (IMPLEMENTED)
│   ├── contextoCBBA.md          # Original design doc
│   ├── app.py                  # Flask entrypoint
│   ├── config.py               # SQL Server credentials, port
│   ├── db.py                   # pyodbc connection helper
│   ├── hospital_ips.py         # RadminVPN IPs for all nodes
│   ├── replication.py          # Partial replication logic
│   ├── requirements.txt        # flask, pyodbc, requests
│   ├── creacion_sqlserver.txt  # Full DB creation script for SSMS
│   ├── routes/                 # Flask blueprints (5 routes)
│   ├── services/               # Business logic + LPZ communication
│   ├── utils/                  # Response helpers, validators
│   ├── sql/                    # schema.sql + seed.sql (SQL Server syntax)
│   ├── templates/              # HTML status page (CBBA colors)
│   └── static/                 # CSS (celeste/blanco)
├── STCZ/contextoSTCZ.md        # Santa Cruz design doc (not yet coded)
└── AGENTS.md
```

## Three nodes

| Node | DB | Role | Port |
|------|----|------|------|
| **LPZ** (La Paz) | PostgreSQL | hospital local + **mediator** for all distributed queries | 5000 |
| **CBBA** (Cochabamba) | SQL Server | regional node, own fragments only | 5000 |
| **STCZ** (Santa Cruz) | SQL Server | regional node, own fragments only | 5000 |

## Key rules

- **All distributed queries go through LPZ** — CBBA/STCZ never talk directly to each other.
- Horizontal fragmentation: each hospital stores only its own patients/histories/prescriptions.
- Only critical data replicated (blood type, allergies, chronic diseases) — no full records.
- If a node disconnects, the others continue functioning locally.
- RadminVPN IPs (e.g. `26.x.x.x`), ports, and DB credentials are centralized in `hospital_ips.py` and `config.py` per node — never hardcoded elsewhere.

## LPZ node structure (mediator — reference for STCZ)

```
LPZ/
├── app.py                  # Flask entrypoint (registers blueprints, runs on port 5000)
├── config.py               # DB credentials, port, hospital name
├── db.py                   # psycopg2 connection + execute_query helper
├── hospital_ips.py         # RadminVPN IPs dict — only place IPs are defined
├── fragment_catalog.py     # FRAGMENTS dict: patient_id → hospital
├── mediator.py             # resolve_patient(): routes query to local or remote
├── replication.py          # replicate_to_nodes(): sends critical data to CBBA/STCZ
├── requirements.txt        # flask, psycopg2, requests
├── creacion_postgresql.txt # Copy-paste SQL script for pgAdmin
├── routes/
│   ├── estado.py           # GET /estado
│   ├── pacientes.py        # GET /paciente/<id>, GET /pacientes, POST /paciente
│   ├── historial.py        # GET /historial/<id>, POST /historial
│   └── mediador.py         # GET /buscar_paciente/<id>, POST /replica
├── services/
│   ├── patient_service.py       # Local DB queries (paciente + historial_clinico)
│   ├── distributed_service.py   # Distributed lookup orchestration
│   └── remote_query_service.py  # HTTP client to CBBA/STCZ (requests.get/post)
├── utils/
│   ├── response.py         # success_response() / error_response()
│   └── validators.py       # Field & ID validation
├── sql/
│   ├── schema.sql          # PostgreSQL DDL
│   └── seed.sql            # 5 sample patients + 6 clinical histories
├── templates/
│   └── index.html          # Status page with green/red LPZ colors
└── static/
    └── style.css           # LPZ color palette (verde #007A3E, rojo #CE1126)
```

## Dependencies

```
LPZ:  pip install flask psycopg2 requests
CBBA: pip install flask pyodbc requests
STCZ: pip install flask pyodbc requests
```

## Endpoints (each node)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/estado` | Health check |
| GET | `/paciente/<id>` | **Local** patient lookup only |
| GET | `/buscar_paciente/<id>` | LPZ only — distributed lookup (mediator logic) |
| GET | `/buscar_nacional/<id>` | CBBA/STCZ only — forwards to LPZ |
| POST | `/replica` | Receive partial replica (blood type, allergies, chronic diseases) |

## Tables (per node)

- `paciente` — local patients only
- `historial_clinico` — local histories only
- `replica_critica` — partial replicas from other nodes

## No tests / no CI / no build

This is a pure Flask prototype with no test suite, no CI, no linter, no type checker. Run each node with `python app.py` and test manually via HTTP or browser on `localhost:5000`.
