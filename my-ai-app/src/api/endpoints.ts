export const apiBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export function websocketUrl(path: string): URL {
  const url = new URL(`${apiBase}${path}`, window.location.href)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url
}
