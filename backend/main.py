from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import aiosqlite
import json
import uuid
from datetime import datetime
from contextlib import asynccontextmanager

DB_PATH = "atlas.db"

class ProjectCreate(BaseModel):
    name: str
    path: str

class Project(BaseModel):
    id: str
    name: str
    path: str
    created_at: str

class SessionCreate(BaseModel):
    project_id: str
    title: Optional[str] = None

class Session(BaseModel):
    id: str
    project_id: str
    title: Optional[str]
    status: str
    created_at: str
    completed_at: Optional[str] = None

class ObservationCreate(BaseModel):
    session_id: str
    type: str
    title: str
    narrative: str
    metadata: Optional[dict] = None

class Observation(BaseModel):
    id: str
    session_id: str
    type: str
    title: str
    narrative: str
    metadata: Optional[dict]
    created_at: str

class ContextQuery(BaseModel):
    project_id: Optional[str] = None
    query: str
    limit: int = 10

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                narrative TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_observations_session ON observations(session_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_observations_created ON observations(created_at DESC)")
        await db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Atlas Observatory", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "atlas-observatory"}

@app.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate):
    async with aiosqlite.connect(DB_PATH) as db:
        pid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        await db.execute(
            "INSERT INTO projects (id, name, path, created_at) VALUES (?, ?, ?, ?)",
            (pid, project.name, project.path, now)
        )
        await db.commit()
        return Project(id=pid, name=project.name, path=project.path, created_at=now)

@app.get("/projects", response_model=List[Project])
async def list_projects():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [Project(id=r["id"], name=r["name"], path=r["path"], created_at=r["created_at"]) for r in rows]

@app.post("/sessions", response_model=Session)
async def create_session(session: SessionCreate):
    async with aiosqlite.connect(DB_PATH) as db:
        # verify project exists
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (session.project_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, "Project not found")
        sid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        await db.execute(
            "INSERT INTO sessions (id, project_id, title, status, created_at) VALUES (?, ?, ?, 'active', ?)",
            (sid, session.project_id, session.title, now)
        )
        await db.commit()
        return Session(id=sid, project_id=session.project_id, title=session.title, status="active", created_at=now)

@app.get("/sessions", response_model=List[Session])
async def list_sessions(project_id: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if project_id:
            cursor = await db.execute("SELECT * FROM sessions WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
        else:
            cursor = await db.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [Session(id=r["id"], project_id=r["project_id"], title=r["title"], status=r["status"], created_at=r["created_at"], completed_at=r["completed_at"]) for r in rows]

@app.post("/sessions/{session_id}/complete")
async def complete_session(session_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, "Session not found")
        now = datetime.utcnow().isoformat()
        await db.execute("UPDATE sessions SET status = 'completed', completed_at = ? WHERE id = ?", (now, session_id))
        await db.commit()
        return {"status": "completed", "session_id": session_id, "completed_at": now}

@app.post("/observations", response_model=Observation)
async def create_observation(obs: ObservationCreate):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM sessions WHERE id = ?", (obs.session_id,))
        if not await cursor.fetchone():
            raise HTTPException(404, "Session not found")
        oid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        await db.execute(
            "INSERT INTO observations (id, session_id, type, title, narrative, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (oid, obs.session_id, obs.type, obs.title, obs.narrative, json.dumps(obs.metadata) if obs.metadata else None, now)
        )
        await db.commit()
        return Observation(id=oid, session_id=obs.session_id, type=obs.type, title=obs.title, narrative=obs.narrative, metadata=obs.metadata, created_at=now)

@app.get("/observations", response_model=List[Observation])
async def list_observations(session_id: Optional[str] = None, limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if session_id:
            cursor = await db.execute("SELECT * FROM observations WHERE session_id = ? ORDER BY created_at DESC LIMIT ?", (session_id, limit))
        else:
            cursor = await db.execute("SELECT * FROM observations ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()
        return [Observation(id=r["id"], session_id=r["session_id"], type=r["type"], title=r["title"], narrative=r["narrative"], metadata=json.loads(r["metadata"]) if r["metadata"] else None, created_at=r["created_at"]) for r in rows]

@app.post("/context")
async def query_context(query: ContextQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if query.project_id:
            cursor = await db.execute("""
                SELECT o.* FROM observations o
                JOIN sessions s ON o.session_id = s.id
                WHERE s.project_id = ? AND (o.title LIKE ? OR o.narrative LIKE ?)
                ORDER BY o.created_at DESC LIMIT ?
            """, (query.project_id, f"%{query.query}%", f"%{query.query}%", query.limit))
        else:
            cursor = await db.execute("""
                SELECT * FROM observations
                WHERE title LIKE ? OR narrative LIKE ?
                ORDER BY created_at DESC LIMIT ?
            """, (f"%{query.query}%", f"%{query.query}%", query.limit))
        rows = await cursor.fetchall()
        return [Observation(id=r["id"], session_id=r["session_id"], type=r["type"], title=r["title"], narrative=r["narrative"], metadata=json.loads(r["metadata"]) if r["metadata"] else None, created_at=r["created_at"]) for r in rows]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
