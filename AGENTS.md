# AGENTS.md — Sistema Hospitalario Distribuido

## Project status

Prototype in planning phase. **No code written yet** — only design docs exist. The goal is academic: demonstrate distributed DB concepts (horizontal fragmentation, mediator node, partial replication) across 3 machines connected via RadminVPN.

## Repo layout

```
SistemaHospitalario/
├── ContextoGeneral.md          # Architecture overview (start here)
├── LaPaz/contextoLaPaz.md      # LPZ = mediator node + local hospital
├── Cochabamba/contextoCBBA.md  # CBBA = regional node
├── SantaCruz/contextoSantaCruz.md  # STCZ = regional node
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

## Per-node structure (recommended in docs)

Each node follows the same pattern:

```
{node}_node/
├── app.py              # Flask entrypoint
├── config.py           # DB credentials, port, local hospital name
├── db.py               # Connection helper
├── hospital_ips.py     # RadminVPN IPs for all nodes
├── routes/
├── services/           # lpz_service.py (for CBBA/STCZ) or remote_query_service.py (for LPZ)
├── utils/
└── sql/                # schema.sql + seed.sql
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
