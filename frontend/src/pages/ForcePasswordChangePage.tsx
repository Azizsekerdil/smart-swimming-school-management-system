/**
 * Zorunlu parola değişimi ekranı / Forced password change screen.
 *
 * İlk kurulumda `admin / admin` kimliğiyle giriş yapılır. Bu ekran
 * geçilmeden uygulamanın hiçbir bölümü açılmaz; sunucu tarafında da aynı kural
 * uygulanır (bkz. `backend/app/core/bootstrap.py`), yani bu yalnızca bir arayüz
 * kısıtı değildir.
 */
import { AlertTriangle, Loader2, Lock } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { ApiError, post } from '@/lib/api'
import { useAuth } from '@/lib/store'
import type { Message } from '@/lib/types'

export default function ForcePasswordChangePage() {
  const { t } = useTranslation()
  const loadSession = useAuth((state) => state.loadSession)
  const logout = useAuth((state) => state.logout)
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [repeat, setRepeat] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    if (next !== repeat) {
      setError(t('auth.passwordMismatch'))
      return
    }
    setLoading(true)
    try {
      await post<Message>('/auth/change-password', {
        current_password: current,
        new_password: next,
      })
      await loadSession()
    } catch (exception) {
      setError(exception instanceof ApiError ? exception.message : t('errors.generic'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-full place-items-center bg-surface-light-alt p-6 dark:bg-surface-dark">
      <div className="w-full max-w-md">
        <div
          role="alert"
          className="mb-6 flex items-start gap-3 rounded-lg border border-amber-400 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200"
        >
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="font-semibold">{t('auth.bootstrapWarningTitle')}</p>
            <p className="mt-1">{t('auth.bootstrapWarningBody')}</p>
          </div>
        </div>

        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          {t('auth.mustChangePassword')}
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {t('auth.bootstrapChangeHint')}
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="current" className="label">
              {t('auth.currentPassword')}
            </label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                id="current"
                type="password"
                autoComplete="current-password"
                required
                value={current}
                onChange={(event) => setCurrent(event.target.value)}
                className="input pl-9"
              />
            </div>
          </div>

          <div>
            <label htmlFor="next" className="label">
              {t('auth.newPassword')}
            </label>
            <input
              id="next"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={next}
              onChange={(event) => setNext(event.target.value)}
              className="input"
            />
            <p className="mt-1 text-xs text-slate-500">{t('auth.passwordPolicy')}</p>
          </div>

          <div>
            <label htmlFor="repeat" className="label">
              {t('auth.confirmPassword')}
            </label>
            <input
              id="repeat"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={repeat}
              onChange={(event) => setRepeat(event.target.value)}
              className="input"
            />
          </div>

          {error && (
            <div className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2.5 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-300">
              {error}
            </div>
          )}

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('auth.changePassword')}
          </button>
          <button type="button" className="btn-ghost w-full" onClick={() => void logout()}>
            {t('auth.logout')}
          </button>
        </form>
      </div>
    </div>
  )
}
