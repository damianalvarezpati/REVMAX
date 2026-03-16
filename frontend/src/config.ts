/**
 * API base URL para el backend RevMax.
 * - Desarrollo: frontend en localhost:3000, backend en localhost:8001.
 * - Con proxy de Vite no hace falta esta variable (las peticiones /api van al proxy).
 * - Si corres frontend y backend por separado sin proxy, usa VITE_API_URL=http://localhost:8001
 */
export const API_BASE_URL =
  typeof import.meta.env?.VITE_API_URL === 'string' && import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/\/$/, '')
    : ''

export function getApiUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`
  return API_BASE_URL ? `${API_BASE_URL}${p}` : p
}
