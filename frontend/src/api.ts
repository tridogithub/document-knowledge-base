export interface Project {
  id: string
  name: string
  created_at: string
  file_count: number
}

export interface KbFile {
  id: string
  file_name: string
  file_type: string
  status: 'pending' | 'indexing' | 'indexed' | 'failed'
  chunk_count: number
  error: string | null
  created_at: string
}

export interface Match {
  chunk_id: string
  score: number
  location: Record<string, unknown> & { section?: string }
  snippet: string
}

export interface SearchResult {
  file_id: string
  file_name: string
  file_path: string
  file_type: string
  score: number
  matches: Match[]
}

export interface McpInfo {
  url: string
  config_json: string
}

export const MAX_QUERY_LENGTH = 512

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* keep statusText */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  listProjects: () => fetch('/api/projects').then((r) => handle<Project[]>(r)),
  createProject: (name: string) =>
    fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    }).then((r) => handle<{ id: string; name: string }>(r)),
  deleteProject: (id: string) =>
    fetch(`/api/projects/${id}`, { method: 'DELETE' }).then((r) => handle<void>(r)),
  listFiles: (projectId: string) =>
    fetch(`/api/projects/${projectId}/files`).then((r) => handle<KbFile[]>(r)),
  uploadFiles: (projectId: string, files: File[]) => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    return fetch(`/api/projects/${projectId}/files`, { method: 'POST', body: form }).then((r) =>
      handle<{ id: string }[]>(r),
    )
  },
  deleteFile: (projectId: string, fileId: string) =>
    fetch(`/api/projects/${projectId}/files/${fileId}`, { method: 'DELETE' }).then((r) =>
      handle<void>(r),
    ),
  search: (projectId: string, q: string) =>
    fetch(`/api/projects/${projectId}/search?q=${encodeURIComponent(q)}`).then((r) =>
      handle<{ query: string; results: SearchResult[] }>(r),
    ),
  mcpInfo: () => fetch('/api/mcp-info').then((r) => handle<McpInfo>(r)),
  health: () => fetch('/api/health').then((r) => r.ok),
}
