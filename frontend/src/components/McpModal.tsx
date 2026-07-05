import { useEffect, useState } from 'react'
import { api, type McpInfo } from '../api'

export function McpModal({ onClose }: { onClose: () => void }) {
  const [info, setInfo] = useState<McpInfo | null>(null)
  const [connected, setConnected] = useState<boolean | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.mcpInfo().then(setInfo).catch(console.error)
    api.health().then(setConnected).catch(() => setConnected(false))
  }, [])

  const copy = async () => {
    if (!info) return
    await navigator.clipboard.writeText(info.config_json)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>MCP Servers</h2>

        <table>
          <tbody>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>URL</th>
            </tr>
            <tr>
              <td>doc-kb</td>
              <td>
                {connected === null ? (
                  <span className="status pending">Checking…</span>
                ) : (
                  <span className={`status ${connected ? 'indexed' : 'failed'}`}>
                    {connected ? 'Connected' : 'Disconnected'}
                  </span>
                )}
              </td>
              <td>{info ? info.url : '…'}</td>
            </tr>
          </tbody>
        </table>

        <div className="modal-json">
          <p>Add this to the MCP configuration of your AI coding agent:</p>
          <pre>{info ? info.config_json : 'Loading…'}</pre>
        </div>

        <div className="modal-footer">
          <button className="copy" onClick={copy} disabled={!info}>
            {copied ? 'Copied!' : 'Copy JSON'}
          </button>
          <button className="close" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
