const FETCH_TIMEOUT = 90_000;

export async function fetchWithTimeout(url: string, options: RequestInit, timeoutMs: number = FETCH_TIMEOUT): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

export const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:7860';

export function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('acacia_backend_token');
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}
