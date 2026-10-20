# CAZ Route & Fleet Sync

A fleet compliance and route planning tool for Bristol’s Clean Air Zone. It helps operators check whether a journey is compliant before a vehicle moves, reducing exposure to CAZ charges and penalty risk while improving route efficiency.

This project is designed as a practical prototype for a wider UK-based compliance platform, with scope to expand into live fleet monitoring, alerts, and operational reporting.

## Project structure

- `backend/` — FastAPI service with route planning, compliance checks, ledger logic, hub logic, and tests
- `frontend/` — Next.js dashboard for route assessment and operational summary
- `db/schema.sql` — database schema for a production-ready data layer
- `docs/01-PRD-and-Proposal.md` — product proposal and roadmap
- `docker-compose.yml` — local orchestration for services

## Quick start

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Run both together
```bash
chmod +x start.sh
./start.sh
```

## What the product does

- checks route compliance against Bristol CAZ rules
- compares the recommended route with the fastest non-compliant option
- estimates likely charge exposure and PCN risk
- gives fleet managers a clearer decision before dispatch

## Important notes

- The current data is illustrative prototype data and not official CAZ survey data.
- The project is designed for concept validation and future expansion into a broader UK transport compliance platform.
- This is not affiliated with Bristol City Council and does not replace official GOV.UK compliance information.

