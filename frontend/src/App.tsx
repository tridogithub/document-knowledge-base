import { useEffect, useState } from 'react'
import { api, type Project } from './api'
import { Sidebar } from './components/Sidebar'
import { FilesPanel } from './components/FilesPanel'
import { SearchMain } from './components/SearchMain'
import { McpModal } from './components/McpModal'
import './styles.css'

export default function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selected, setSelected] = useState<string | null>(null)
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

  const create = async (name: string) => {
    const p = await api.createProject(name)
    await refresh()
    setSelected(p.id)
  }

  const remove = async (p: Project) => {
    if (!confirm(`Delete project "${p.name}" and all its indexed data?`)) return
    await api.deleteProject(p.id)
    refresh()
  }

  const current = projects.find((p) => p.id === selected)

  return (
    <div className="app">
      <header>
        <div className="logo">📚 RAG System</div>
        <div className="toolbar">
          <button onClick={() => setShowMcp(true)}>🖥 MCP Servers</button>
          <button
            onClick={() =>
              alert(
                'Upload pdf, docx, pptx, xlsx, md or txt files to a project, then search or connect an AI agent via MCP Servers.',
              )
            }
          >
            ❓ Help
          </button>
        </div>
      </header>

      <div className="content">
        <Sidebar
          projects={projects}
          selectedId={selected}
          onSelect={setSelected}
          onCreate={create}
          onDelete={remove}
        />

        {current ? (
          <>
            <FilesPanel key={current.id} project={current} />
            <SearchMain key={`${current.id}-search`} projectId={current.id} />
          </>
        ) : (
          <div className="main">
            <div className="search-panel centered">
              <h1>No projects yet</h1>
              <p className="subtitle">Create a project in the sidebar to get started.</p>
            </div>
          </div>
        )}
      </div>

      {error && <p className="error" style={{ padding: '0 28px' }}>{error}</p>}
      {showMcp && <McpModal onClose={() => setShowMcp(false)} />}
    </div>
  )
}
