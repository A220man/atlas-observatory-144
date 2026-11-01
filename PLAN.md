# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

observer-pipeline

## Roadmap

### core-infrastructure — Core Infrastructure: FastAPI backend + React frontend skeleton with SQLite storage

Status: done

Acceptance:
- FastAPI server starts on port 8000 with /health endpoint
- React dev server starts on port 3000 and proxies API calls
- SQLite database initializes with sessions, observations, and projects tables
- One end-to-end workflow: create session -> add observation -> retrieve context

Implementation: `backend/main.py`, `frontend/src/App.tsx`, `frontend/vite.config.ts`

Tests: `backend/test_main.py`, `test_backend.py`

### observer-pipeline — Observer Response Pipeline: classify outputs, preserve batches on failure, bound history

Status: done

Acceptance:
- Output classifier distinguishes valid, skip, idle, auth, overflow, xml_drift, prose_salvageable, prose
- Policy table maps each class to {preserve|confirm|abort} batch decision
- Token budget enforced on conversation history with truncation

Implementation: `backend/observer_pipeline.py`

Tests: `backend/test_observer_pipeline.py`

### session-management — Session Management: create, resume, complete sessions with context injection

Status: planned

Acceptance:
- Session CRUD API with project association
- Context injection retrieves relevant observations for a query
- Session completion marks status and triggers summarization

### hook-integration — Hook Integration: thin, fail-open Claude Code hooks

Status: planned

Acceptance:
- Hook wrapper adds <60ms overhead on Unix, <300ms on Windows
- Worker unavailable returns {continue:true} exit 0, never exit 2
- No login shell spawn in common path

