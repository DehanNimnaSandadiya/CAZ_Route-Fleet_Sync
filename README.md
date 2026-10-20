# CAZ-Route & Fleet Sync (Bristol)

Hyper-local B2B SaaS for Bristol SME fleets: hill- and Clean-Air-Zone-aware routing, cargo-bike micro-hub
handshakes, a CAZ compliance ledger with PCN risk predictor, and a pool-sharing marketplace for drop nodes.

## Contents
| Path | What it is |
|---|---|
| `docs/01-PRD-and-Proposal.md` | Full proposal + PRD (vision, personas, features, architecture, stack, monetisation, GTM, 3-phase roadmap, risks) |
| `backend/` | FastAPI prototype: routing engine, compliance ledger, hubs, marketplace, 8 automated tests |
| `frontend/` | Next.js 14 demo UI (route planner + PCN risk) |
| `db/schema.sql` | PostgreSQL + PostGIS + pgRouting reference schema |
| `docker-compose.yml` | db + api + web |

## Run the backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q                                    # 8 tests
uvicorn app.main:app --reload                          # http://localhost:8000/docs
```

## Run the frontend
```bash
cd frontend
npm install
npm run dev                                            # http://localhost:3000 (API on :8000)
```

## Run both together
```bash
chmod +x start.sh
./start.sh                                             # starts API + web app together
```

## Or everything via Docker
```bash
cp .env.example .env && docker compose up --build
```

## Important limitations (please read)
- **Seed data is illustrative.** `backend/app/seed.py` uses approximate coordinates, rough elevations and
  placeholder `in_caz` flags. It is not survey or official data. Production must import OSM, a terrain model and the
  official CAZ polygon (see PRD section 4.3).
- **CAZ constants** (£9 / £100, Euro 4 petrol / Euro 6 diesel, 6-day payment window, PCN £120 / £60) were checked
  against Bristol City Council / GOV.UK material in Oct 2026 but must be re-verified before launch (`backend/app/config.py`).
- The API stores data **in memory** (prototype). The SQL schema is the intended persistence layer; it has not been
  executed against a live PostgreSQL in this build, and Docker has not been run.
- Pricing, targets and financials in the PRD are planning hypotheses to validate, not market data.
- The tool supports compliance; users pay via the official GOV.UK service. Not affiliated with Bristol City Council.
