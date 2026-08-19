/**
 * API istemcisi / API client.
 *
 * - JWT erişim jetonunu otomatik ekler
 * - 401 durumunda yenileme (refresh) akışını bir kez dener
 * - Backend'in yerelleştirilmiş hata biçimini normalize eder
 */
import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios'

export const API_BASE = '/api/v1'

const ACCESS_TOKEN_KEY = 'sws-access-token'
const REFRESH_TOKEN_KEY = 'sws-refresh-token'
const LANGUAGE_KEY = 'sws-language'

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_TOKEN_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_TOKEN_KEY, access)
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  },
}

/** Backend hata biçimi: { error: { code, message, details? } } */
export interface ApiErrorPayload {
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

export class ApiError extends Error {
  code: string
  status: number
  details?: Record<string, unknown>

  constructor(message: string, code: string, status: number, details?: Record<string, unknown>) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }

  /** Ders planlama çakışmalarını çıkarır (varsa) */
  get conflicts(): Array<Record<string, unknown>> {
    const raw = this.details?.conflicts
    return Array.isArray(raw) ? (raw as Array<Record<string, unknown>>) : []
  }
}

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.access
  if (token) config.headers.Authorization = `Bearer ${token}`
  config.headers['Accept-Language'] = localStorage.getItem(LANGUAGE_KEY) ?? 'tr'
  return config
})

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStore.refresh
  if (!refresh) return null
  try {
    const response = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refresh })
    const { access_token, refresh_token } = response.data
    tokenStore.set(access_token, refresh_token)
    return access_token
  } catch {
    tokenStore.clear()
    return null
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorPayload>) => {
    const original = error.config as (AxiosRequestConfig & { _retried?: boolean }) | undefined
    const status = error.response?.status ?? 0

    // Süresi dolan jetonu bir kez yenilemeyi dene
    if (status === 401 && original && !original._retried && !original.url?.includes('/auth/')) {
      original._retried = true
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null
      })
      const token = await refreshPromise
      if (token) {
        original.headers = { ...original.headers, Authorization: `Bearer ${token}` }
        return api.request(original)
      }
      // Yenileme başarısız: oturumu kapat
      window.dispatchEvent(new CustomEvent('sws:session-expired'))
    }

    const payload = error.response?.data
    throw new ApiError(
      payload?.error?.message ?? error.message ?? 'Beklenmeyen bir hata oluştu.',
      payload?.error?.code ?? 'network_error',
      status,
      payload?.error?.details,
    )
  },
)

// --- Kısayollar ---
export async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const { data } = await api.get<T>(url, { params })
  return data
}

export async function post<T>(url: string, body?: unknown, params?: Record<string, unknown>): Promise<T> {
  const { data } = await api.post<T>(url, body, { params })
  return data
}

export async function put<T>(url: string, body?: unknown): Promise<T> {
  const { data } = await api.put<T>(url, body)
  return data
}

export async function patch<T>(url: string, body?: unknown): Promise<T> {
  const { data } = await api.patch<T>(url, body)
  return data
}

export async function del<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const { data } = await api.delete<T>(url, { params })
  return data
}

/** Dosya indirir (PDF/Excel/CSV dışa aktarma) */
export async function download(
  url: string,
  body: unknown,
  fallbackName = 'rapor',
): Promise<void> {
  const response = await api.post(url, body, { responseType: 'blob' })
  const disposition = String(response.headers['content-disposition'] ?? '')
  let filename = fallbackName

  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i)
  if (utf8Match) filename = decodeURIComponent(utf8Match[1])
  else if (plainMatch) filename = plainMatch[1]

  const blobUrl = URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(blobUrl)
}
