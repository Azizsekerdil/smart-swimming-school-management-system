import { useQuery } from '@tanstack/react-query'
import { Component, Suspense, lazy, useEffect, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { LoadingState } from '@/components/ui'
import { get } from '@/lib/api'
import { applyOrganizationSettings, useAuth } from '@/lib/store'
import type { AppSetting } from '@/lib/types'
import ForcePasswordChangePage from '@/pages/ForcePasswordChangePage'
import LoginPage from '@/pages/LoginPage'

// Kod bölme: her sayfa ayrı parça olarak yüklenir
const DashboardPage = lazy(() => import('@/pages/DashboardPage'))
const StudentsPage = lazy(() => import('@/pages/StudentsPage'))
const StudentDetailPage = lazy(() => import('@/pages/StudentDetailPage'))
const GuardiansPage = lazy(() => import('@/pages/GuardiansPage'))
const InstructorsPage = lazy(() => import('@/pages/InstructorsPage'))
const PoolsPage = lazy(() => import('@/pages/PoolsPage'))
const LanePlanPage = lazy(() => import('@/pages/LanePlanPage'))
const CalendarPage = lazy(() => import('@/pages/CalendarPage'))
const LessonsPage = lazy(() => import('@/pages/LessonsPage'))
const AttendancePage = lazy(() => import('@/pages/AttendancePage'))
const MembershipsPage = lazy(() => import('@/pages/MembershipsPage'))
const FinancePage = lazy(() => import('@/pages/FinancePage'))
const PerformancePage = lazy(() => import('@/pages/PerformancePage'))
const CompetitionsPage = lazy(() => import('@/pages/CompetitionsPage'))
const StatisticsPage = lazy(() => import('@/pages/StatisticsPage'))
const ReportsPage = lazy(() => import('@/pages/ReportsPage'))
const AICenterPage = lazy(() => import('@/pages/AICenterPage'))
const AIDeveloperPage = lazy(() => import('@/pages/AIDeveloperPage'))
const CAIOPage = lazy(() => import('@/pages/CAIOPage'))
const NotificationsPage = lazy(() => import('@/pages/NotificationsPage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))
const TrainingPage = lazy(() => import('@/pages/TrainingPage'))
const HelpPage = lazy(() => import('@/pages/HelpPage'))
const OnboardingPage = lazy(() => import('@/pages/OnboardingPage'))

// ---------------------------------------------------------------------------
// Hata sınırı
// ---------------------------------------------------------------------------
class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidCatch(error: Error) {
    console.error('[UI] Yakalanmamış hata:', error)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="grid h-full place-items-center p-8">
          <div className="max-w-md text-center">
            <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Bir şeyler ters gitti / Something went wrong
            </h1>
            <p className="mt-2 text-sm text-slate-500">{this.state.error.message}</p>
            <button
              type="button"
              className="btn-primary mt-4"
              onClick={() => window.location.reload()}
            >
              Sayfayı yenile / Reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

// ---------------------------------------------------------------------------
// Yetki koruması
// ---------------------------------------------------------------------------
function RequirePermission({ permission, children }: { permission?: string; children: ReactNode }) {
  const { t } = useTranslation()
  const can = useAuth((state) => state.can)

  if (permission && !can(permission)) {
    return (
      <div className="grid place-items-center py-20 text-center">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            {t('errors.forbidden')}
          </h1>
          <p className="mt-1 text-sm text-slate-500">{t('errors.forbiddenHint')}</p>
        </div>
      </div>
    )
  }
  return <>{children}</>
}

function NotFound() {
  const { t } = useTranslation()
  return (
    <div className="grid place-items-center py-20 text-center">
      <div>
        <p className="text-5xl font-bold text-slate-300 dark:text-slate-600">404</p>
        <h1 className="mt-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
          {t('errors.notFound')}
        </h1>
        <p className="mt-1 text-sm text-slate-500">{t('errors.notFoundHint')}</p>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
export default function App() {
  const { status, user, loadSession } = useAuth()
  const location = useLocation()

  useEffect(() => {
    void loadSession()
  }, [loadSession])

  // Kurum ayarlarını (para birimi vb.) uygula
  const { data: organization } = useQuery({
    queryKey: ['setting', 'organization'],
    queryFn: () => get<AppSetting>('/settings/organization'),
    enabled: status === 'authenticated',
    staleTime: 10 * 60_000,
  })

  useEffect(() => {
    if (organization?.value) {
      applyOrganizationSettings(organization.value as Record<string, unknown>)
    }
  }, [organization])

  if (status === 'idle' || status === 'loading') {
    return (
      <div className="grid h-full place-items-center">
        <LoadingState />
      </div>
    )
  }

  if (status === 'anonymous') {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" state={{ from: location }} replace />} />
      </Routes>
    )
  }

  // Zorunlu parola değişimi: ilk kurulum kimliğiyle girildiyse başka hiçbir
  // ekran açılmaz. Sunucu da aynı kuralı uygular; bu yalnızca arayüz kısıtı
  // değildir (bkz. backend/app/core/bootstrap.py).
  if (user?.must_change_password) {
    return (
      <ErrorBoundary>
        <ForcePasswordChangePage />
      </ErrorBoundary>
    )
  }

  // Kurulum sihirbazı: ilk girişte
  if (user && !user.onboarding_completed && location.pathname !== '/onboarding') {
    return (
      <ErrorBoundary>
        <Suspense fallback={<LoadingState />}>
          <Routes>
            <Route path="*" element={<OnboardingPage />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    )
  }

  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="/onboarding" element={<Suspense fallback={<LoadingState />}><OnboardingPage /></Suspense>} />
        <Route element={<AppLayout />}>
          <Route
            index
            element={
              <Suspense fallback={<LoadingState />}>
                <DashboardPage />
              </Suspense>
            }
          />
          {(
            [
              ['students', StudentsPage, 'student:read'],
              ['guardians', GuardiansPage, 'guardian:read'],
              ['instructors', InstructorsPage, 'instructor:read'],
              ['pools', PoolsPage, 'pool:read'],
              ['lane-plan', LanePlanPage, 'pool:read'],
              ['calendar', CalendarPage, 'lesson:read'],
              ['lessons', LessonsPage, 'lesson:read'],
              ['attendance', AttendancePage, 'attendance:read'],
              ['memberships', MembershipsPage, 'membership:read'],
              ['finance', FinancePage, 'finance:read'],
              ['performance', PerformancePage, 'performance:read'],
              ['competitions', CompetitionsPage, 'competition:read'],
              ['statistics', StatisticsPage, 'statistics:read'],
              ['reports', ReportsPage, 'report:read'],
              ['ai', AICenterPage, 'ai:use'],
              ['ai-developer', AIDeveloperPage, 'ai:developer'],
              ['caio', CAIOPage, 'ai:caio'],
              ['notifications', NotificationsPage, undefined],
              ['settings', SettingsPage, undefined],
              ['training', TrainingPage, undefined],
              ['help', HelpPage, undefined],
            ] as Array<[string, React.LazyExoticComponent<() => JSX.Element>, string | undefined]>
          ).map(([path, PageComponent, permission]) => (
            <Route
              key={path}
              path={path}
              element={
                <RequirePermission permission={permission}>
                  <Suspense fallback={<LoadingState />}>
                    <PageComponent />
                  </Suspense>
                </RequirePermission>
              }
            />
          ))}
          <Route
            path="students/:id"
            element={
              <RequirePermission permission="student:read">
                <Suspense fallback={<LoadingState />}>
                  <StudentDetailPage />
                </Suspense>
              </RequirePermission>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}
