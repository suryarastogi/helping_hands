# helping_hands frontend

Simple React + TypeScript UI for task submission and tracking against the
`helping_hands` app API (`/build`, `/tasks/{task_id}`, and `/tasks/current`).

## Run locally

```bash
cd frontend
npm install
npm run dev
```

By default, Vite proxies API requests to `http://127.0.0.1:8000`.

## Quality checks

```bash
cd frontend

# Lint TypeScript/React code
npm run lint

# Type-check frontend sources
npm run typecheck

# Run tests
npm run test

# Run tests with coverage (text + lcov + cobertura)
npm run coverage
```

Coverage reports are written to `frontend/coverage/`.

## CI integration

The root CI workflow runs a dedicated `frontend-check` job that executes:

1. `npm install`
2. `npm run lint`
3. `npm run typecheck`
4. `npm run coverage`

`frontend/coverage/lcov.info` is uploaded to Codecov under a frontend flag.

## Configuration

- `VITE_PROXY_TARGET` (dev-only): proxy target for `/build`, `/tasks`, `/monitor`, `/health`
- `VITE_API_BASE_URL` (optional): absolute API base URL for direct fetches

Example:

```bash
VITE_PROXY_TARGET=http://localhost:8000 npm run dev
```
