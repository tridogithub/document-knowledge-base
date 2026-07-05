import { useState } from 'react'
import { api, MAX_QUERY_LENGTH, type SearchResult, type Match } from '../api'

function locationLabel(loc: Match['location']): string {
  const parts: string[] = []
  if (loc.page != null) parts.push(`page ${loc.page}`)
  if (loc.slide != null) parts.push(`slide ${loc.slide}`)
  if (loc.sheet != null) parts.push(`sheet "${loc.sheet}"`)
  if (loc.line_start != null) parts.push(`lines ${loc.line_start}–${loc.line_end}`)
  if (loc.section) parts.push(loc.section)
  return parts.join(' · ') || 'whole document'
}

export function SearchBar({ projectId }: { projectId: string }) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<SearchResult[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    const query = q.trim()
    if (!query) return
    setLoading(true)
    setError('')
    try {
      const res = await api.search(projectId, query)
      setResults(res.results)
    } catch (e) {
      setError((e as Error).message)
      setResults(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="search">
      <div className="search-row">
        <input
          value={q}
          maxLength={MAX_QUERY_LENGTH}
          placeholder="Search documents… (keyword + semantic)"
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && run()}
        />
        <button onClick={run} disabled={loading || !q.trim()}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {results !== null &&
        (results.length === 0 ? (
          <p className="muted">No matching documents.</p>
        ) : (
          <div className="results">
            {results.map((r, i) => (
              <div className="card" key={r.file_id}>
                <div className="card-head">
                  <span className="rank">#{i + 1}</span>
                  <span className="badge">{r.file_type}</span>
                  <strong>{r.file_name}</strong>
                  <span className="score">score {r.score.toFixed(3)}</span>
                </div>
                {r.matches.map((m) => (
                  <div className="match" key={m.chunk_id}>
                    <div className="loc">{locationLabel(m.location)}</div>
                    <div className="snippet">{m.snippet}</div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        ))}
    </section>
  )
}
