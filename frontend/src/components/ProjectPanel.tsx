import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type KbFile, type Project } from '../api'
import { SearchBar } from './SearchBar'

const STATUS_LABEL: Record<KbFile['status'], string> = {
  pending: 'Pending',
  indexing: 'Indexing…',
  indexed: 'Indexed',
  failed: 'Failed',
}

export function ProjectPanel({ project }: { project: Project }) {
  const [files, setFiles] = useState<KbFile[]>([])
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const refresh = useCallback(
    () => api.listFiles(project.id).then(setFiles).catch(console.error),
    [project.id],
  )

  useEffect(() => {
    refresh()
  }, [refresh])

  const busy = files.some((f) => f.status === 'pending' || f.status === 'indexing')
  useEffect(() => {
    if (!busy) return
    const t = setInterval(refresh, 2000)
    return () => clearInterval(t)
  }, [busy, refresh])

  const upload = async (list: FileList | File[]) => {
    setError('')
    try {
      await api.uploadFiles(project.id, Array.from(list))
      refresh()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const removeFile = async (f: KbFile) => {
    if (!confirm(`Remove ${f.file_name} and its chunks from the vector DB?`)) return
    await api.deleteFile(project.id, f.id)
    refresh()
  }

  return (
    <div className="panel">
      <h1>{project.name}</h1>
      <SearchBar projectId={project.id} />

      <div
        className={`dropzone ${dragging ? 'dragging' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          upload(e.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
      >
        Drop files here or click to upload (pdf, docx, pptx, xlsx, md, txt)
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept=".pdf,.docx,.pptx,.xlsx,.xls,.md,.markdown,.txt"
          onChange={(e) => e.target.files && upload(e.target.files)}
        />
      </div>
      {error && <p className="error">{error}</p>}

      <table className="files">
        <thead>
          <tr>
            <th>File</th>
            <th>Type</th>
            <th>Status</th>
            <th>Chunks</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {files.map((f) => (
            <tr key={f.id}>
              <td>{f.file_name}</td>
              <td>
                <span className="badge">{f.file_type}</span>
              </td>
              <td>
                <span className={`status ${f.status}`} title={f.error ?? ''}>
                  {STATUS_LABEL[f.status]}
                </span>
              </td>
              <td>{f.status === 'indexed' ? f.chunk_count : '—'}</td>
              <td>
                <button className="danger" onClick={() => removeFile(f)}>
                  Remove
                </button>
              </td>
            </tr>
          ))}
          {files.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                No files yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
