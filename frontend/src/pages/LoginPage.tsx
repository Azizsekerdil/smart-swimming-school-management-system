/** Giriş ekranı / Login screen. */
import { AlertCircle, AlertTriangle, Loader2, Lock, Mail, Waves } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { LanguageToggle } from '@/components/layout/AppLayout'
import { ApiError, get } from '@/lib/api'
import { useAuth } from '@/lib/store'

interface BootstrapStatus {
  bootstrap_pending: boolean
  local_request: boolean
}

export default function LoginPage() {
  const { t } = useTranslation()
  const login = useAuth((state) => state.login)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [bootstrapPending, setBootstrapPending] = useState(false)

  // İlk çalıştırma uyarısı. Sunucu bu bilgiyi yalnızca yerel cihaza verir;
  // ağ üzerinden sorulduğunda daima `false` döner.
  useEffect(() => {
    let cancelled = false
    get<BootstrapStatus>('/auth/bootstrap-status')
      .then((status) => {
        if (!cancelled) setBootstrapPending(Boolean(status?.bootstrap_pending))
      })
      .catch(() => {
        /* uyarı bilgisi alınamadıysa sessiz geç */
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email.trim(), password)
    } catch (exception) {
      setError(exception instanceof ApiError ? exception.message : t('errors.generic'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-full lg:grid-cols-2">
      {/* Sol: marka paneli */}
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-brand-600 via-brand-700 to-brand-900 p-12 lg:flex lg:flex-col lg:justify-between">
        <svg
          className="pointer-events-none absolute inset-x-0 bottom-0 opacity-20"
          viewBox="0 0 400 120"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path d="M0 60c40 0 40-30 80-30s40 30 80 30 40-30 80-30 40 30 80 30 40-30 80-30v90H0z" fill="#fff" />
          <path
            d="M0 85c40 0 40-30 80-30s40 30 80 30 40-30 80-30 40 30 80 30 40-30 80-30v65H0z"
            fill="#fff"
            opacity=".5"
          />
        </svg>

        <div className="relative flex items-center gap-3 text-white">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-white/20 backdrop-blur">
            <Waves className="h-6 w-6" />
          </div>
          <div>
            <p className="text-lg font-semibold">{t('app.name')}</p>
            <p className="text-xs text-white/70">{t('app.fullName')}</p>
          </div>
        </div>

        <div className="relative text-white">
          <h1 className="text-3xl font-semibold leading-tight text-balance">{t('app.tagline')}</h1>
          <ul className="mt-8 space-y-3 text-sm text-white/85">
            {[
              'Öğrenci, veli ve eğitmen yönetimi',
              'Kulvar planlama ve otomatik çakışma denetimi',
              'Yoklama, üyelik ve finans takibi',
              'Sporcu performans analizi ve yarışma yönetimi',
              'Yerel (LM Studio) ve bulut yapay zekâ desteği',
            ].map((feature) => (
              <li key={feature} className="flex items-center gap-2.5">
                <span className="h-1.5 w-1.5 rounded-full bg-white/70" />
                {feature}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/50">MIT Lisansı · Açık kaynak bileşenlerle geliştirildi</p>
      </div>

      {/* Sağ: form */}
      <div className="flex items-center justify-center bg-surface-light-alt p-6 dark:bg-surface-dark">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-2.5 lg:hidden">
              <div className="grid h-10 w-10 place-items-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 text-white">
                <Waves className="h-5 w-5" />
              </div>
              <p className="font-semibold text-slate-900 dark:text-slate-100">{t('app.name')}</p>
            </div>
            <div className="ml-auto">
              <LanguageToggle />
            </div>
          </div>

          {bootstrapPending && (
            <div
              role="alert"
              className="mb-5 flex items-start gap-3 rounded-lg border border-amber-400 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200"
            >
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              <div>
                <p className="font-semibold">{t('auth.bootstrapBannerTitle')}</p>
                <p className="mt-1">{t('auth.bootstrapBannerBody')}</p>
              </div>
            </div>
          )}

          <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
            {t('auth.welcomeBack')}
          </h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{t('auth.loginSubtitle')}</p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <div>
              <label htmlFor="email" className="label">
                {t('auth.identifier')}
              </label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  id="email"
                  type="text"
                  inputMode="email"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="input pl-9"
                  placeholder="ornek@yuzmeokulu.local"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="label">
                {t('auth.password')}
              </label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="input pl-9"
                  placeholder="••••••••"
                />
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2.5 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-300">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {loading ? t('auth.signingIn') : t('auth.signIn')}
            </button>
          </form>

          <p className="mt-8 text-center text-xs text-slate-400">
            {t('app.fullName')} · v0.9.0
          </p>
        </div>
      </div>
    </div>
  )
}
