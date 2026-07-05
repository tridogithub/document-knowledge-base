import { useMemo, useState } from 'react'
import type { Project } from '../api'

export function Sidebar({
  projects,
  selectedId,
  onSelect,
  onCreate,
  onDelete,
}: {
  projects: Project[]
  selectedId: string | null
  onSelect: (id: string) => void
  onCreate: (name: string) => Promise<void>
  onDelete: (project: Project) => void
}) {
  const [filter, setFilter] = useState('')
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  const visible = useMemo(
    () => projects.filter((p) => p.name.toLowerCase().includes(filter.trim().toLowerCase())),
    [projects, filter],
  )

  const submit = async () => {
    const trimmed = name.trim()
    if (!trimmed) return
    setError('')
    try {
      await onCreate(trimmed)
      setName('')
      setCreating(false)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Projects</h2>

        {creating ? (
          <div className="new-project-form">
            <div className="row">
              <input
                autoFocus
                value={name}
                maxLength={64}
                placeholder="Project name"
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') submit()
                  if (e.key === 'Escape') setCreating(false)
                }}
              />
              <button className="new-project" style={{ width: 'auto', padding: '10px 16px' }} onClick={submit}>
                Add
              </button>
            </div>
            {error && <p className="error">{error}</p>}
          </div>
        ) : (
          <button className="new-project" onClick={() => setCreating(true)}>
            + New Project
          </button>
        )}

        <input
          className="search-input"
          placeholder="Search project..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="projects">
        {visible.map((p) => (
          <div
            key={p.id}
            className={`project ${p.id === selectedId ? 'active' : ''}`}
            onClick={() => onSelect(p.id)}
          >
            <div>
              <div className="project-title">{p.name}</div>
              <small>{p.file_count} files</small>
            </div>
            <button
              className="project-delete"
              title="Delete project"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(p)
              }}
            >
              ×
            </button>
          </div>
        ))}
        {visible.length === 0 && <p className="empty-hint">No projects found.</p>}
      </div>
    </div>
  )
}
