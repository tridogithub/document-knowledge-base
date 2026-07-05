import { useEffect, useState } from 'react'
import { api, type Project } from './api'
import { ProjectPanel } from './components/ProjectPanel'
import { McpModal } from './components/McpModal'
import './styles.css'

export default function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [error, setError] = useState('')
  const [showMcp, setShowMcp] = useState(false)

  const refresh = () =>
    api
      .listProjects()
      .then((ps) => {
        setProjects(ps)
        setSelected((cur) => (cur && ps.some((p) => p.id === cur) ? cur : (ps[0]?.id ?? null)))
      })
      .catch((e) => setError((e as Error).message))

  useEffect(() => {
    refresh()
  }, [])

  const create = async () => {
    const name = newName.trim()
    if (!name) return
    setError('')
    try {
      const p = await api.createProject(name)
      setNewName('')
      await refresh()
      setSelected(p.id)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const remove = async (p: Project) => {
    if (!confirm(`Delete project "${p.name}" and all its indexed data?`)) return
    await api.deleteProject(p.id)
    refresh()
  }

  const current = projects.find((p) => p.id === selected)

  return (
    <div className="layout">
      <aside>
        <div className="brand">📚 Doc KB</div>
        <div className="new-project">
          <input
            value={newName}
            maxLength={64}
            placeholder="New project name"
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && create()}
          />
          <button onClick={create}>+</button>
        </div>
        {error && <p className="error">{error}</p>}
        <nav>
          {projects.map((p) => (
            <div
              key={p.id}
              className={`project-item ${p.id === selected ? 'active' : ''}`}
              onClick={() => setSelected(p.id)}
            >
              <span>
                {p.name} <small>({p.file_count})</small>
              </span>
              <button
                className="danger ghost"
                onClick={(e) => {
                  e.stopPropagation()
                  remove(p)
                }}
              >
                ×
              </button>
            </div>
          ))}
        </nav>
        <button className="mcp-btn" onClick={() => setShowMcp(true)}>
          MCP Server
        </button>
      </aside>
      <main>
        {current ? (
          <ProjectPanel key={current.id} project={current} />
        ) : (
          <div className="panel muted">Create a project to get started.</div>
        )}
      </main>
      {showMcp && <McpModal onClose={() => setShowMcp(false)} />}
    </div>
  )
}
