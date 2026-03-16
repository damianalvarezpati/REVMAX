/**
 * API base URL para el backend RevMax.
 * En desarrollo: frontend en localhost:3000, backend en localhost:8001.
 * Usar NEXT_PUBLIC_ para que esté disponible en el cliente.
 */
export const API_BASE_URL =
  typeof process.env.NEXT_PUBLIC_REVMAX_API_URL === 'string' &&
  process.env.NEXT_PUBLIC_REVMAX_API_URL
    ? process.env.NEXT_PUBLIC_REVMAX_API_URL.replace(/\/$/, '')
    : '';

export function getApiUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`;
  return API_BASE_URL ? `${API_BASE_URL}${p}` : p;
}
