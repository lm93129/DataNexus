# Repository Guidelines

## Project Structure & Module Organization

DataNexus is a dual-output enterprise data gateway. `backend/` contains FastAPI, shared logic, MCP adapter, REST routes, models, schemas, migrations, and pytest suites. Key paths are `backend/app/services/`, `backend/app/api/`, `backend/app/mcp/`, and `backend/tests/`.

`frontend/` contains the Vue 3 console. Source lives in `frontend/src/`: API wrappers in `src/api/`, stores in `src/stores/`, routes in `src/router/`, components in `src/components/`, and pages in `src/views/`. Static files are in `frontend/public/`; docs in `docs/`.

## Build, Test, and Development Commands

Use Docker Compose for local startup:

```bash
docker compose up -d
```

Backend setup and local service. Backend uses `uv`; run commands through `uv` to avoid mismatched interpreters or missing test dependencies:

```bash
cd backend
uv venv
uv pip install -e ".[dev]"
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Frontend setup and checks:

```bash
cd frontend
pnpm install
pnpm dev
pnpm build
pnpm preview
```

Run backend tests with `cd backend && uv run pytest -v`. Do not use global `pytest` or system Python. Before handoff, also run `uv run python -m compileall app tests` and `uv run alembic heads`.

## Coding Style & Naming Conventions

Backend targets Python 3.11+, FastAPI, async SQLAlchemy 2.0, and Pydantic V2. Keep adapters thin; shared behavior belongs in `app/services/`. Use snake_case for modules, functions, and variables, and PascalCase for schemas and ORM classes.

Frontend uses Vue 3, TypeScript, Vite, Pinia, and Naive UI. Use PascalCase for components, camelCase for TypeScript values, and colocate view-specific helpers unless reused.

## Testing Guidelines

Backend tests use pytest and pytest-asyncio from `uv`. Place tests under `backend/tests/`, following `test_<feature>.py` inside folders such as `test_services/`, `test_api/`, and `test_mcp/`. Cover authorization, SQL safety, masking, auditing, and MCP/REST parity.

Frontend has no dedicated test runner configured; use `pnpm build` as the required type-check and production-build gate.

## Commit & Pull Request Guidelines

Git history uses Conventional Commit-style prefixes, mainly `feat:` followed by a concise Chinese summary. Continue that pattern, for example `feat: 增强查询审计能力` or `fix: 修复登录态刷新问题`.

Pull requests should include scope, rationale, verification commands, linked issues or docs, and screenshots for UI changes. Note migrations, env changes, security impacts, and MCP/REST differences.

## Security & Configuration Tips

Never commit real `.env` files, API keys, database passwords, or production secrets. Replace default `DATANEXUS_SECRET_KEY` and `DATANEXUS_AES_KEY` outside local development. Data source accounts should be read-only, and external data paths must preserve permission checks, risk control, masking, and auditing.
