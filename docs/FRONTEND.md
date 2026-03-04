# Frontend Architecture

## Overview

The frontend is a React + TypeScript single-page application built with Vite. It provides a UI for submitting build tasks and tracking their progress against the helping_hands API.

## Stack

- **React 18** with TypeScript
- **Vite** for dev server and bundling
- **Vitest** for testing with coverage

## Key Files

| File | Purpose |
|------|---------|
| `frontend/src/App.tsx` | Main application component — task form, status display, world dashboard |
| `frontend/src/main.tsx` | Entry point, renders App into DOM |
| `frontend/src/styles.css` | Global styles |
| `frontend/src/test/setup.ts` | Test configuration |

## API Integration

The frontend communicates with the FastAPI backend through these endpoints:

- `POST /build` — submit a new build task
- `GET /tasks/{task_id}` — poll task status
- `GET /tasks/current` — get active task info

In development, Vite proxies API requests to `http://127.0.0.1:8000` (configurable via `VITE_PROXY_TARGET`).

## Dual UI Constraint

The server also embeds an inline HTML UI in `server/app.py`. Both UIs must stay functionally equivalent — changes to one should be mirrored in the other.

## Development

```bash
cd frontend
npm install
npm run dev         # dev server with hot reload
npm run lint        # ESLint
npm run typecheck   # tsc --noEmit
npm run test        # Vitest
npm run coverage    # Vitest with coverage reports
```

## CI

The root GitHub Actions workflow runs a `frontend-check` job: install, lint, typecheck, coverage. Coverage uploads to Codecov under a frontend flag.
