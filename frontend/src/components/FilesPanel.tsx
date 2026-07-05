import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, type KbFile, type Project } from '../api'
import { toFileUrl } from '../fileLink'

const STATUS_LABEL: Record<KbFile['status'], string> = {
  pending: 'Pending',
  indexing: 'Indexing…',
  indexed: 'Indexed',
  failed: 'Failed',
}

export function FilesPanel({ project }: { project: Project }) {
  const [files, setFiles] = useState<KbFile[]>([])
  const [filter, setFilter] = useState('')
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  const [sourceDir, setSourceDir] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const refresh = useCallback(
    () => api.listFiles(project.id).then(setFiles).catch(console.error),
    [project.id],
  )

  useEffect(() => {
    setFiles([])
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
      await api.uploadFiles(project.id, Array.from(list), sourceDir)
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

  const visible = useMemo(
    () => files.filter((f) => f.file_name.toLowerCase().includes(filter.trim().toLowerCase())),
    [files, filter],
  )

  return (
    <div
      className="files"
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
    >
      <div className="files-header">
        <h3>Uploaded Files</h3>

        <input
          className="search-input"
          placeholder="Search files"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />

        <input
          className="search-input"
          placeholder="Source folder (optional, e.g. /Users/me/Documents)"
          title="The folder these files live in on your machine — stored as metadata so search results can point back to it."
          value={sourceDir}
          onChange={(e) => setSourceDir(e.target.value)}
        />

        <button
          className={`upload ${dragging ? 'dragging' : ''}`}
          onClick={() => inputRef.current?.click()}
        >
          Upload Files
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept=".pdf,.docx,.pptx,.xlsx,.xls,.md,.markdown,.txt"
          onChange={(e) => e.target.files && upload(e.target.files)}
        />
        {error && <p className="error">{error}</p>}
      </div>

      <div className="file-list">
        {visible.map((f) => (
          <div className="file" key={f.id}>
            <div className="file-info">
              <div className="file-name">{f.file_name}</div>
              <small title={f.error ?? ''}>
                {f.file_type.toUpperCase()}
                {f.status === 'indexed' ? ` · ${f.chunk_count} chunks` : ''}
              </small>
              {f.source_path !== f.file_name && (
                <a
                  className="source-path"
                  href={toFileUrl(f.source_path)}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={`Open ${f.source_path}`}
                >
                  {f.source_path}
                </a>
              )}
            </div>
            <span className={`status ${f.status}`}>{STATUS_LABEL[f.status]}</span>
            <button className="file-remove" title="Remove file" onClick={() => removeFile(f)}>
              ×
            </button>
          </div>
        ))}
        {visible.length === 0 && (
          <p className="empty-hint">{files.length === 0 ? 'No files yet — upload one to get started.' : 'No files match your search.'}</p>
        )}
      </div>
    </div>
  )
}
