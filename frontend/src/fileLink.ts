/** Builds a file:// URL from an absolute source path so the browser can open it
 * locally when the user clicks (works for both /unix/paths and C:\windows\paths). */
export function toFileUrl(path: string): string {
  const normalized = path.replace(/\\/g, '/')
  const withLeadingSlash = normalized.startsWith('/') ? normalized : `/${normalized}`
  return `file://${withLeadingSlash.split('/').map(encodeURIComponent).join('/')}`
}
