import { useEffect, useState } from 'react'
import { api, type McpInfo } from '../api'

export function McpModal({ onClose }: { onClose: () => void }) {
  const [info, setInfo] = useState<McpInfo | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.mcpInfo().then(setInfo).catch(console.error)
  }, [])

  const copy = async () => {
    if (!info) return
    await navigator.clipboard.writeText(info.config_json)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>MCP Server</h2>
        {info ? (
          <>
            <p>
              Streamable HTTP endpoint: <code>{info.url}</code>
            </p>
            <p>Add this to the MCP configuration of your coding agent:</p>
            <pre>{info.config_json}</pre>
            <div className="modal-actions">
              <button onClick={copy}>{copied ? 'Copied!' : 'Copy JSON'}</button>
              <button className="secondary" onClick={onClose}>
                Close
              </button>
            </div>
          </>
        ) : (
          <p>Loading…</p>
        )}
      </div>
    </div>
  )
}
