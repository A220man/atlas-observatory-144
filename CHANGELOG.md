# Changelog

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

### core-infrastructure (completed)
- FastAPI backend with /health, /projects, /sessions, /observations, /context endpoints
- SQLite database with projects, sessions, observations tables and indexes
- React frontend with Vite dev server (port 3000) proxying to FastAPI (port 8000)
- End-to-end workflow: create project → create session → add observation → query context
- Tests: backend/test_main.py (2 passing), test_backend.py (integration passing)

### observer-pipeline (completed)
- Output classifier (backend/observer_pipeline.py) with 8 output classes: valid, skip, idle, auth, overflow, xml_drift, prose_salvageable, prose
- Policy table mapping each class to {preserve|confirm|abort} batch decision
- Token budget enforcement with configurable limits and history truncation
- Comprehensive test coverage: backend/test_observer_pipeline.py (27 passing)

### session-management (completed)
- Session CRUD API with project association (create, list, complete sessions)
- Session completion triggers background summarization
- Session summaries stored with files_read, files_edited, relevance_count
- New endpoint: GET /sessions/{session_id}/summary
- Context injection retrieves relevant observations for a query
- Tests: backend/test_main.py (2 passing), test_backend.py (integration passing)

Partial code published for continued development. Known issues: STATUS.md.
