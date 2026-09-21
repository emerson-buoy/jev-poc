// Server-side only: configures the generated client against the FastAPI base URL.
import { client } from '@/lib/api/generated/client.gen'
import { env } from '@/server/env'

client.setConfig({ baseUrl: env.apiUrl })

interface ApiResult<T> {
  data?: T
  error?: unknown
  response?: Response
}

/** Turns a generated-client result into data, or throws an Error carrying FastAPI's detail. */
export function unwrap<T>(result: ApiResult<T>): T {
  if (result.error !== undefined || !result.response?.ok) {
    throw new Error(errorMessage(result.error, result.response))
  }
  return result.data as T
}

function errorMessage(error: unknown, response: Response | undefined): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (d && typeof d === 'object' && 'msg' in d ? String(d.msg) : String(d)))
        .join('; ')
    }
  }
  return `API request failed${response ? ` with status ${response.status}` : ''}`
}
