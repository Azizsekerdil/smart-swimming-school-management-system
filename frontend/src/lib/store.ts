/** Global istemci durumu / Global client state (Zustand). */
import { create } from 'zustand'

import { get as apiGet, post, tokenStore } from './api'
import { setCurrency } from './format'
import { getStoredLanguage, setLanguage, type Language } from './i18n'
import type { CurrentUser, TokenPair } from './types'

// ---------------------------------------------------------------------------
// Kimlik doğrulama
// ---------------------------------------------------------------------------
interface AuthState {
  user: CurrentUser | null
  status: 'idle' | 'loading' | 'authenticated' | 'anonymous'
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  loadSession: () => Promise<void>
  setUser: (user: CurrentUser) => void
  can: (permission: string) => boolean
  canAny: (...permissions: string[]) => boolean
  hasRole: (...roles: string[]) => boolean
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  status: 'idle',

  async login(email, password) {
    const tokens = await post<TokenPair>('/auth/login', { email, password })
    tokenStore.set(tokens.access_token, tokens.refresh_token)
    const user = await apiGet<CurrentUser>('/auth/me')
    if (user.language) setLanguage(user.language as Language)
    set({ user, status: 'authenticated' })
  },

  async logout() {
    try {
      await post('/auth/logout')
    } catch {
      // Sunucuya ulaşılamasa da yerel oturumu kapat
    }
    tokenStore.clear()
    set({ user: null, status: 'anonymous' })
  },

  async loadSession() {
    if (!tokenStore.access) {
      set({ status: 'anonymous' })
      return
    }
    set({ status: 'loading' })
    try {
      const user = await apiGet<CurrentUser>('/auth/me')
      set({ user, status: 'authenticated' })
    } catch {
      tokenStore.clear()
      set({ user: null, status: 'anonymous' })
    }
  },

  setUser(user) {
    set({ user })
  },

  can(permission) {
    const { user } = get()
    if (!user) return false
    return user.is_superuser || user.permissions.includes(permission)
  },

  canAny(...permissions) {
    const { user } = get()
    if (!user) return false
    if (user.is_superuser) return true
    return permissions.some((permission) => user.permissions.includes(permission))
  },

  hasRole(...roles) {
    const { user } = get()
    if (!user) return false
    const codes = user.roles.map((role) => role.code)
    return roles.some((role) => codes.includes(role))
  },
}))

// Oturum süresi dolduğunda API katmanından gelen olay
window.addEventListener('sws:session-expired', () => {
  useAuth.setState({ user: null, status: 'anonymous' })
})

// ---------------------------------------------------------------------------
// Arayüz tercihleri
// ---------------------------------------------------------------------------
export type Theme = 'light' | 'dark' | 'system'

const THEME_KEY = 'sws-theme'
const SIDEBAR_KEY = 'sws-sidebar-collapsed'

function applyTheme(theme: Theme): void {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const dark = theme === 'dark' || (theme === 'system' && prefersDark)
  document.documentElement.classList.toggle('dark', dark)
}

interface UIState {
  theme: Theme
  language: Language
  sidebarCollapsed: boolean
  paletteOpen: boolean
  searchOpen: boolean
  setTheme: (theme: Theme) => void
  changeLanguage: (language: Language) => void
  toggleSidebar: () => void
  setPaletteOpen: (open: boolean) => void
  setSearchOpen: (open: boolean) => void
}

export const useUI = create<UIState>((set, get) => ({
  theme: (localStorage.getItem(THEME_KEY) as Theme) ?? 'system',
  language: getStoredLanguage(),
  sidebarCollapsed: localStorage.getItem(SIDEBAR_KEY) === '1',
  paletteOpen: false,
  searchOpen: false,

  setTheme(theme) {
    localStorage.setItem(THEME_KEY, theme)
    applyTheme(theme)
    set({ theme })
    // Sunucudaki tercihi de güncelle (hata olursa yerel tercih korunur)
    void post('/auth/preferences', { theme }).catch(() => undefined)
  },

  changeLanguage(language) {
    setLanguage(language)
    set({ language })
    void post('/auth/preferences', { language }).catch(() => undefined)
  },

  toggleSidebar() {
    const collapsed = !get().sidebarCollapsed
    localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0')
    set({ sidebarCollapsed: collapsed })
  },

  setPaletteOpen(open) {
    set({ paletteOpen: open })
  },

  setSearchOpen(open) {
    set({ searchOpen: open })
  },
}))

// İlk yüklemede tema uygula ve sistem değişimini dinle
applyTheme(useUI.getState().theme)
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if (useUI.getState().theme === 'system') applyTheme('system')
})

// ---------------------------------------------------------------------------
// Bildirim tostları
// ---------------------------------------------------------------------------
export interface Toast {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  description?: string
}

interface ToastState {
  toasts: Toast[]
  push: (toast: Omit<Toast, 'id'>) => void
  dismiss: (id: number) => void
}

let toastCounter = 0

export const useToast = create<ToastState>((set) => ({
  toasts: [],
  push(toast) {
    const id = ++toastCounter
    set((state) => ({ toasts: [...state.toasts, { ...toast, id }] }))
    setTimeout(() => {
      set((state) => ({ toasts: state.toasts.filter((item) => item.id !== id) }))
    }, toast.type === 'error' ? 8000 : 4500)
  },
  dismiss(id) {
    set((state) => ({ toasts: state.toasts.filter((item) => item.id !== id) }))
  },
}))

/** Kısayol: hata nesnesinden tost üretir */
export function toastError(error: unknown, fallback = 'Bir hata oluştu'): void {
  const message = error instanceof Error ? error.message : fallback
  useToast.getState().push({ type: 'error', title: message })
}

export function toastSuccess(title: string, description?: string): void {
  useToast.getState().push({ type: 'success', title, description })
}

// Kurum para birimini uygula (ayarlar yüklendiğinde çağrılır)
export function applyOrganizationSettings(value: Record<string, unknown> | null): void {
  if (value && typeof value.currency === 'string') setCurrency(value.currency)
}
