/** @import { GenerateRequest, GenerateResponse } from './types.js' */

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * POST /generate
 * @param {GenerateRequest} payload
 * @returns {Promise<GenerateResponse>}
 */
export async function generate(payload) {
  const res = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    return {
      results: [],
      error: body?.error ?? { code: 'INTERNAL_ERROR', message: `HTTP ${res.status}` },
    }
  }

  return res.json()
}
