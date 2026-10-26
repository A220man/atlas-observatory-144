import { useState, useEffect } from 'react'

interface Project {
  id: string
  name: string
  path: string
  created_at: string
}

interface Session {
  id: string
  project_id: string
  title: string | null
  status: string
  created_at: string
  completed_at: string | null
}

interface Observation {
  id: string
  session_id: string
  type: string
  title: string
  narrative: string
  metadata: Record<string, any> | null
  created_at: string
}

function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [observations, setObservations] = useState<Observation[]>([])
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectPath, setNewProjectPath] = useState('')
  const [newSessionTitle, setNewSessionTitle] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)

  const API_BASE = ''

  async function fetchProjects() {
    const res = await fetch(`${API_BASE}/projects`)
    const data = await res.json()
    setProjects(data)
  }

  async function createProject() {
    const res = await fetch(`${API_BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newProjectName, path: newProjectPath })
    })
    if (res.ok) {
      setNewProjectName('')
      setNewProjectPath('')
      fetchProjects()
    }
  }

  async function fetchSessions(projectId: string) {
    const res = await fetch(`${API_BASE}/sessions?project_id=${projectId}`)
    const data = await res.json()
    setSessions(data)
  }

  async function createSession(projectId: string) {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, title: newSessionTitle })
    })
    if (res.ok) {
      setNewSessionTitle('')
      fetchSessions(projectId)
    }
  }

  async function completeSession(sessionId: string) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/complete`, {
      method: 'POST'
    })
    if (res.ok) {
      fetchSessions(selectedProject!.id)
    }
  }

  async function fetchObservations(sessionId: string) {
    const res = await fetch(`${API_BASE}/observations?session_id=${sessionId}`)
    const data = await res.json()
    setObservations(data)
  }

  async function searchContext() {
    if (!selectedProject || !searchQuery.trim()) return
    setLoading(true)
    const res = await fetch(`${API_BASE}/context`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: selectedProject.id, query: searchQuery, limit: 10 })
    })
    const data = await res.json()
    setObservations(data)
    setLoading(false)
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  useEffect(() => {
    if (selectedProject) {
      fetchSessions(selectedProject.id)
    }
  }, [selectedProject])

  useEffect(() => {
    if (sessions.length > 0) {
      fetchObservations(sessions[0].id)
    }
  }, [sessions])

  return (
    <div style={{ padding: '20px', fontFamily: 'system-ui, sans-serif', maxWidth: '1000px', margin: '0 auto' }}>
      <h1>Atlas Observatory</h1>
      
      <section style={{ marginBottom: '30px', padding: '20px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h2>Projects</h2>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '10px', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Project name"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            style={{ flex: 1, minWidth: '200px', padding: '8px' }}
          />
          <input
            type="text"
            placeholder="Project path"
            value={newProjectPath}
            onChange={(e) => setNewProjectPath(e.target.value)}
            style={{ flex: 1, minWidth: '200px', padding: '8px' }}
          />
          <button onClick={createProject} style={{ padding: '8px 16px' }}>Create Project</button>
        </div>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {projects.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedProject(p)}
              style={{
                padding: '10px 16px',
                background: selectedProject?.id === p.id ? '#007bff' : '#f0f0f0',
                color: selectedProject?.id === p.id ? 'white' : 'black',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              {p.name} ({p.path})
            </button>
          ))}
        </div>
      </section>

      {selectedProject && (
        <section style={{ marginBottom: '30px', padding: '20px', border: '1px solid #ddd', borderRadius: '8px' }}>
          <h2>Sessions - {selectedProject.name}</h2>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
            <input
              type="text"
              placeholder="Session title (optional)"
              value={newSessionTitle}
              onChange={(e) => setNewSessionTitle(e.target.value)}
              style={{ flex: 1, minWidth: '300px', padding: '8px' }}
            />
            <button onClick={() => createSession(selectedProject.id)} style={{ padding: '8px 16px' }}>Create Session</button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {sessions.map(s => (
              <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px', background: '#f9f9f9', borderRadius: '4px' }}>
                <span style={{ flex: 1 }}>{s.title || 'Untitled'} - {s.status}</span>
                <small>{new Date(s.created_at).toLocaleString()}</small>
                {s.status === 'active' && (
                  <button onClick={() => completeSession(s.id)} style={{ padding: '4px 12px' }}>Complete</button>
                )}
              </div>
            ))}
            {sessions.length === 0 && <p>No sessions yet. Create one above.</p>}
          </div>
        </section>
      )}

      <section style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h2>Context Search</h2>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
          <input
            type="text"
            placeholder="Search observations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchContext()}
            style={{ flex: 1, minWidth: '300px', padding: '8px' }}
          />
          <button onClick={searchContext} disabled={loading} style={{ padding: '8px 16px' }}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {observations.map(o => (
            <div key={o.id} style={{ padding: '12px', background: '#f9f9f9', borderRadius: '4px', borderLeft: '4px solid #007bff' }}>
              <div style={{ display: 'flex', justifyContent: 'spaceBetween', marginBottom: '8px' }}>
                <strong>{o.title}</strong>
                <span style={{ fontSize: '12px', color: '#666', textTransform: 'capitalize' }}>{o.type}</span>
              </div>
              <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{o.narrative}</p>
              {o.metadata && (
                <div style={{ marginTop: '8px', fontSize: '12px', color: '#666' }}>
                  {JSON.stringify(o.metadata)}
                </div>
              )}
              <small style={{ color: '#999' }}>{new Date(o.created_at).toLocaleString()}</small>
            </div>
          ))}
          {observations.length === 0 && <p>No observations found. Create a session and add observations via API.</p>}
        </div>
      </section>
    </div>
  )
}

export default App
