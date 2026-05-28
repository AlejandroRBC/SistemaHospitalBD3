# AGENTS.md — Sistema Hospitalario Distribuido

**Status:** All 3 nodes implemented (prototype). Academic project for distributed DB concepts.

## Three nodes

| Node | DB | Port | Role |
|------|----|------|------|
| **LPZ** (La Paz, mediator) | PostgreSQL 16 | **5000** | Hospital local + **mediator** of all distributed queries |
| **CBBA** (Cochabamba) | SQL Server | **5001** | Regional node, own fragments only |
| **STCZ** (Santa Cruz) | SQL Server | **5002** | Regional node, own fragments only |

## Repo structure (flat — no `routes/services/utils/`)

```
SISTEMA_GENERAL.txt     # Architecture docs (start here)
contexto.txt            # Original assignment UML & fragmentation specs
LPZ/ CBBA/ STCZ/
  app.py                # Flask entrypoint (all routes inline)
  config.py             # DB creds, RadminVPN IPs, colors, port
  db.py                 # fetchall/fetchone/execute helpers (+ remote via pyodbc for LPZ)
  mediator.py           # LPZ-only: fragment catalog, distributed queries, replication
  setup_*.sql           # Schema + seed data (run ONCE to init DB)
  README_*.txt          # Per-node setup guide
  requirements.txt
  templates/            # Jinja2 (13 pages per node)
```

## Key architecture rules

- **Star topology:** All distributed queries go through LPZ. CBBA/STCZ never talk directly.
- **Hybrid fragmentation:** `historial_clinico_v1` (critical — blood type, allergies, chronic diseases) replicates to all nodes as `historial_replica`; `historial_clinico_v2` (heavy notes) stays in origin only.
- **Patient ID ranges:** LPZ 1-9999, CBBA 10000-19999, STCZ 20000+ (enforced by `SERIAL`/`IDENTITY`).
- **Replication triggers:** On patient create or history update, LPZ pushes via pyodbc to CBBA+STCZ; CBBA/STCZ HTTP POST to LPZ `/api/replica`, LPZ propagates to the third node.
- **Medication catalog:** Managed from LPZ, pushed synchronously to CBBA+STCZ via pyodbc.
- **CBBA/STCZ → LPZ queries:** Priority = Linked Server (OPENQUERY via PostgreSQL ODBC), fallback = HTTP to LPZ `/api/buscar`.

## DB passwords (different per node — update in `config.py`)

```
LPZ  DB: postgres / admin
CBBA DB: sa       / Admin1234!
STCZ DB: sa       / Admin1234!
```

## Boot order

```
1. LPZ   (cd LPZ   && pip install -r requirements.txt && python app.py)   # port 5000
2. CBBA  (cd CBBA  && pip install -r requirements.txt && python app.py)   # port 5001
3. STCZ  (cd STCZ  && pip install -r requirements.txt && python app.py)   # port 5002
```

**LPZ must start first** — it receives replica registrations on boot.

## Setup per node

```
LPZ:  psql -U postgres -c "CREATE DATABASE hospital_lpz;"
      psql -U postgres -d hospital_lpz -f setup_lpz.sql
CBBA: sqlcmd -S localhost -U sa -P Admin1234! -Q "CREATE DATABASE hospital_cbba;"
      sqlcmd -S localhost -U sa -P Admin1234! -i setup_cbba.sql
STCZ: sqlcmd -S localhost -U sa -P Admin1234! -Q "CREATE DATABASE hospital_stcz;"
      sqlcmd -S localhost -U sa -P Admin1234! -i setup_stcz.sql
```

## Dependencies

```
LPZ:  pip install flask psycopg2-binary pyodbc requests
CBBA: pip install flask pyodbc requests
STCZ: pip install flask pyodbc requests
```

## RadminVPN IPs (update in each `config.py` before running)

```
LPZ  Config: LPZ_DB['host']=localhost, CBBA_SQL['server']=26.8.33.47, STCZ_SQL['server']=26.116.149.11
CBBA Config: LPZ_URL=http://26.91.247.115:5000
STCZ Config: LPZ_URL=http://26.91.247.115:5000
```

## All endpoints

| Method | Path | Scope |
|--------|------|-------|
| GET | `/` | Dashboard (stats: patients, consults, emergencies, doctors, replicas, logs) |
| GET | `/pacientes` / `/paciente/<id>` | Local patient list/detail |
| GET+POST | `/paciente/nuevo` | Register patient (auto-replicates V1 to other nodes) |
| POST | `/historial/actualizar` | Update history (re-triggers replication) |
| GET | `/consultas` / `/consulta/nueva` | Consultations |
| GET | `/emergencias` / `/emergencia/nueva` | Emergencies |
| GET | `/transferencias` / `/transferencia/nueva` | Inter-hospital transfers |
| GET | `/medicamentos` / `/medicamento/nuevo` | **LPZ only** — adds + replicates to all nodes |
| GET | `/buscar_nacional?q=...` | Web UI: distributed search (LPZ searches all 3; CBBA/STCZ via LS→HTTP) |
| GET | `/emergencia_cruzada/<id>` | Critical data for emergency (local replica → remote fallback) |
| GET | `/logs` | **LPZ only** — distributed operation audit trail |
| GET | `/api/health` | JSON health check |
| GET | `/api/paciente/<id>` | JSON patient lookup (catalog-resolved) |
| GET | `/api/buscar?q=...` | JSON distributed search |
| GET | `/api/historial_critico/<id>` | JSON critical history (with replica fallback) |
| POST | `/api/replica` | Receive critical replica from another node |
| POST | `/api/catalogo/registro` | Register a patient in LPZ's fragmentation catalog |

## Tables per node

All nodes: `paciente`, `doctor`, `consulta`, `emergencia`, `receta`, `receta_medicamento`, `transferencias_hospitalarias`, `historial_clinico_v1`, `historial_clinico_v2`, `hospital`, `medicamento`, `historial_replica`
LPZ only: `fragment_catalog`, `distributed_logs`

## Color palette per node (flag colors)

```
LPZ  → Primary=#B22222 (firebrick), Secondary=#FFD700 (gold),    BG=#FFF8DC
CBBA → Primary=#2E7D32 (green),      Secondary=#A5D6A7 (lime),   BG=#F1F8E9
STCZ → Primary=#1B5E20 (dark green), Secondary=#80CBC4 (teal),   BG=#E8F5E9
```

## SQL dialect quirks (LPZ wrapper handles translation)

| Feature | PostgreSQL (LPZ) | SQL Server (CBBA/STCZ) |
|---------|------------------|------------------------|
| Params | `%s` | `?` |
| Auto-inc | `SERIAL` | `IDENTITY(10000,1)` or `IDENTITY(20000,1)` |
| Date | `CURRENT_DATE`, `NOW()` | `CAST(GETDATE() AS DATE)`, `GETDATE()` |
| Case-insensitive | `ILIKE '%x%'` | `LIKE '%x%'` (default) |
| Concat | `\|\|` | `+` |
| Upsert | `INSERT ... ON CONFLICT DO UPDATE` | `IF EXISTS(...) UPDATE ELSE INSERT` |
| String quote | single quotes | single quotes |

## No tests / no CI / no linter / no typechecker

Pure Flask prototype. Test manually via `localhost:5000/5001/5002` or HTTP. No test framework, no CI, no build step.

## Node README files (per-node detail)

`LPZ/README_LPZ.txt`, `CBBA/README_CBBA.txt`, `STCZ/README_STCZ.txt` — contain full setup, Linked Server config, and operation flows.

## .gitignore

`venv/`, `__pycache__/`, `*.pyc`, `.env`
