/** Ana uygulama kabuğu: kenar çubuğu, üst çubuk, içerik alanı. */
import clsx from 'clsx'
import {
  Activity, Award, BarChart3, Bell, BookOpen, Brain, Calendar, ChevronLeft,
  CreditCard, FileText, GraduationCap, Grid3x3, Home, IdCard, LayoutGrid,
  LogOut, Menu, Moon, Search, Settings, Shield, Sparkles, Sun, Terminal,
  Trophy, User, Users, Waves, X,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { CommandPalette } from '@/components/layout/CommandPalette'
import { GlobalSearch } from '@/components/layout/GlobalSearch'
import { ToastContainer } from '@/components/ui'
import { get } from '@/lib/api'
import { initials } from '@/lib/format'
import type { Language } from '@/lib/i18n'
import { useAuth, useUI } from '@/lib/store'

interface NavItem {
  to: string
  labelKey: string
  icon: ReactNode
  permission?: string
  anyPermission?: string[]
}

interface NavSection {
  titleKey: string
  items: NavItem[]
}

const NAV_SECTIONS: NavSection[] = [
  {
    titleKey: 'nav.sections.overview',
    items: [{ to: '/', labelKey: 'nav.dashboard', icon: <Home className="h-4 w-4" /> }],
  },
  {
    titleKey: 'nav.sections.people',
    items: [
      { to: '/students', labelKey: 'nav.students', icon: <Users className="h-4 w-4" />, permission: 'student:read' },
      { to: '/guardians', labelKey: 'nav.guardians', icon: <User className="h-4 w-4" />, permission: 'guardian:read' },
      { to: '/instructors', labelKey: 'nav.instructors', icon: <Award className="h-4 w-4" />, permission: 'instructor:read' },
    ],
  },
  {
    titleKey: 'nav.sections.operations',
    items: [
      { to: '/calendar', labelKey: 'nav.calendar', icon: <Calendar className="h-4 w-4" />, permission: 'lesson:read' },
      { to: '/lessons', labelKey: 'nav.lessons', icon: <LayoutGrid className="h-4 w-4" />, permission: 'lesson:read' },
      { to: '/pools', labelKey: 'nav.pools', icon: <Waves className="h-4 w-4" />, permission: 'pool:read' },
      { to: '/lane-plan', labelKey: 'nav.lanes', icon: <Grid3x3 className="h-4 w-4" />, permission: 'pool:read' },
      { to: '/attendance', labelKey: 'nav.attendance', icon: <IdCard className="h-4 w-4" />, permission: 'attendance:read' },
    ],
  },
  {
    titleKey: 'nav.sections.finance',
    items: [
      { to: '/memberships', labelKey: 'nav.memberships', icon: <CreditCard className="h-4 w-4" />, permission: 'membership:read' },
      { to: '/finance', labelKey: 'nav.finance', icon: <BarChart3 className="h-4 w-4" />, permission: 'finance:read' },
    ],
  },
  {
    titleKey: 'nav.sections.sports',
    items: [
      { to: '/performance', labelKey: 'nav.performance', icon: <Activity className="h-4 w-4" />, permission: 'performance:read' },
      { to: '/competitions', labelKey: 'nav.competitions', icon: <Trophy className="h-4 w-4" />, permission: 'competition:read' },
    ],
  },
  {
    titleKey: 'nav.sections.analytics',
    items: [
      { to: '/statistics', labelKey: 'nav.statistics', icon: <BarChart3 className="h-4 w-4" />, permission: 'statistics:read' },
      { to: '/reports', labelKey: 'nav.reports', icon: <FileText className="h-4 w-4" />, permission: 'report:read' },
    ],
  },
  {
    titleKey: 'nav.sections.ai',
    items: [
      { to: '/ai', labelKey: 'nav.aiCenter', icon: <Sparkles className="h-4 w-4" />, permission: 'ai:use' },
      { to: '/ai-developer', labelKey: 'nav.aiDeveloper', icon: <Terminal className="h-4 w-4" />, permission: 'ai:developer' },
      { to: '/caio', labelKey: 'nav.caio', icon: <Brain className="h-4 w-4" />, permission: 'ai:caio' },
    ],
  },
  {
    titleKey: 'nav.sections.system',
    items: [
      { to: '/training', labelKey: 'nav.trainingCenter', icon: <GraduationCap className="h-4 w-4" /> },
      { to: '/help', labelKey: 'nav.help', icon: <BookOpen className="h-4 w-4" /> },
      { to: '/notifications', labelKey: 'nav.notifications', icon: <Bell className="h-4 w-4" /> },
      { to: '/settings', labelKey: 'nav.settings', icon: <Settings className="h-4 w-4" /> },
    ],
  },
]

export function AppLayout() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, can } = useAuth()
  const { sidebarCollapsed, toggleSidebar, theme, setTheme, setPaletteOpen, setSearchOpen } = useUI()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  // Okunmamış bildirim sayısı
  const { data: counts } = useQuery({
    queryKey: ['notification-counts'],
    queryFn: () => get<{ unread: number }>('/notifications/counts'),
    refetchInterval: 60_000,
  })

  // Klavye kısayolları
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPaletteOpen(true)
      }
      if (event.key === '/' && !(event.target as HTMLElement)?.closest('input,textarea')) {
        event.preventDefault()
        setSearchOpen(true)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [setPaletteOpen, setSearchOpen])

  useEffect(() => {
    setMobileOpen(false)
    setUserMenuOpen(false)
  }, [location.pathname])

  const visibleSections = NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter(
      (item) => !item.permission || can(item.permission),
    ),
  })).filter((section) => section.items.length > 0)

  function cycleTheme() {
    setTheme(theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light')
  }

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const sidebar = (
    <nav className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 text-white shadow-sm">
          <Waves className="h-5 w-5" />
        </div>
        {!sidebarCollapsed && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
              {t('app.name')}
            </p>
            <p className="truncate text-[10px] text-slate-500 dark:text-slate-400">
              {t('nav.system')} v0.9.0
            </p>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {visibleSections.map((section) => (
          <div key={section.titleKey}>
            {!sidebarCollapsed && <p className="nav-section">{t(section.titleKey)}</p>}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  title={sidebarCollapsed ? t(item.labelKey) : undefined}
                  className={({ isActive }) =>
                    clsx('nav-link', isActive && 'nav-link-active', sidebarCollapsed && 'justify-center px-2')
                  }
                >
                  {item.icon}
                  {!sidebarCollapsed && <span className="truncate">{t(item.labelKey)}</span>}
                  {!sidebarCollapsed && item.to === '/notifications' && (counts?.unread ?? 0) > 0 && (
                    <span className="ml-auto rounded-full bg-rose-500 px-1.5 text-[10px] font-semibold text-white">
                      {counts!.unread > 99 ? '99+' : counts!.unread}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={toggleSidebar}
        className="hidden items-center justify-center gap-2 border-t border-slate-200 py-2.5 text-xs text-slate-400 hover:text-slate-600 dark:border-slate-700 dark:hover:text-slate-300 lg:flex"
      >
        <ChevronLeft className={clsx('h-4 w-4 transition-transform', sidebarCollapsed && 'rotate-180')} />
        {!sidebarCollapsed && <span>Daralt</span>}
      </button>
    </nav>
  )

  return (
    <div className="flex h-full">
      {/* Masaüstü kenar çubuğu */}
      <aside
        className={clsx(
          'hidden shrink-0 border-r border-slate-200 bg-white transition-all dark:border-slate-700 dark:bg-surface-dark-alt lg:block',
          sidebarCollapsed ? 'w-16' : 'w-60',
        )}
      >
        {sidebar}
      </aside>

      {/* Mobil kenar çubuğu */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 animate-slide-down bg-white shadow-panel dark:bg-surface-dark-alt">
            {sidebar}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Üst çubuk */}
        <header className="no-print sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b border-slate-200 bg-white/90 px-3 backdrop-blur dark:border-slate-700 dark:bg-surface-dark-alt/90 sm:px-4">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="btn-ghost btn-sm lg:hidden"
            aria-label="Menü"
          >
            <Menu className="h-5 w-5" />
          </button>

          <button
            type="button"
            onClick={() => setSearchOpen(true)}
            className="flex h-9 flex-1 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm text-slate-400 transition-colors hover:border-slate-300 dark:border-slate-600 dark:bg-slate-800 dark:hover:border-slate-500 sm:max-w-md"
          >
            <Search className="h-4 w-4 shrink-0" />
            <span className="truncate">{t('common.searchPlaceholder')}</span>
            <kbd className="ml-auto hidden rounded border border-slate-300 px-1.5 text-[10px] dark:border-slate-600 sm:block">
              /
            </kbd>
          </button>

          <div className="ml-auto flex items-center gap-1">
            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              className="btn-ghost btn-sm hidden sm:inline-flex"
              title={`${t('commandPalette.title')} (Ctrl+K)`}
            >
              <Terminal className="h-4 w-4" />
            </button>

            <button
              type="button"
              onClick={() => i18n.changeLanguage(i18n.language === 'tr' ? 'en' : 'tr')}
              onDoubleClick={() => undefined}
              className="btn-ghost btn-sm font-semibold"
              title={t('settings.language')}
            >
              {i18n.language === 'tr' ? 'TR' : 'EN'}
            </button>

            <button type="button" onClick={cycleTheme} className="btn-ghost btn-sm" title={t('settings.theme')}>
              {theme === 'dark' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            </button>

            <Link to="/notifications" className="btn-ghost btn-sm relative" title={t('nav.notifications')}>
              <Bell className="h-4 w-4" />
              {(counts?.unread ?? 0) > 0 && (
                <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-rose-500" />
              )}
            </Link>

            <div className="relative">
              <button
                type="button"
                onClick={() => setUserMenuOpen((open) => !open)}
                className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                <div className="grid h-7 w-7 place-items-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
                  {initials(user?.full_name)}
                </div>
                <span className="hidden max-w-[120px] truncate text-sm text-slate-700 dark:text-slate-200 sm:block">
                  {user?.full_name}
                </span>
              </button>

              {userMenuOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setUserMenuOpen(false)} />
                  <div className="absolute right-0 z-20 mt-1 w-60 animate-slide-down rounded-lg border border-slate-200 bg-white p-1 shadow-panel dark:border-slate-700 dark:bg-surface-dark-alt">
                    <div className="border-b border-slate-200 px-3 py-2 dark:border-slate-700">
                      <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">
                        {user?.full_name}
                      </p>
                      <p className="truncate text-xs text-slate-500">{user?.email}</p>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {user?.roles.slice(0, 3).map((role) => (
                          <span key={role.id} className="badge-info text-[10px]">
                            {i18n.language === 'tr' ? role.name_tr : role.name_en}
                          </span>
                        ))}
                      </div>
                    </div>
                    <Link to="/settings?tab=profile" className="nav-link w-full">
                      <User className="h-4 w-4" />
                      {t('auth.myAccount')}
                    </Link>
                    {can('audit:read') && (
                      <Link to="/settings?tab=audit" className="nav-link w-full">
                        <Shield className="h-4 w-4" />
                        {t('nav.audit')}
                      </Link>
                    )}
                    <button type="button" onClick={handleLogout} className="nav-link w-full text-rose-600 dark:text-rose-400">
                      <LogOut className="h-4 w-4" />
                      {t('auth.logout')}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Eğitim modu bandı */}
        {user?.training_mode && (
          <div className="no-print flex items-center justify-center gap-2 bg-violet-600 px-4 py-1.5 text-xs font-medium text-white">
            <GraduationCap className="h-3.5 w-3.5" />
            {t('settings.trainingModeHint')}
          </div>
        )}

        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>

      <CommandPalette />
      <GlobalSearch />
      <ToastContainer />
    </div>
  )
}

/** Dil düğmesi için yardımcı (ayarlar ekranında da kullanılır) */
export function LanguageToggle() {
  const { i18n } = useTranslation()
  const { changeLanguage } = useUI()
  return (
    <div className="inline-flex rounded-lg border border-slate-300 p-0.5 dark:border-slate-600">
      {(['tr', 'en'] as Language[]).map((code) => (
        <button
          key={code}
          type="button"
          onClick={() => changeLanguage(code)}
          className={clsx(
            'rounded px-3 py-1 text-xs font-medium transition-colors',
            i18n.language === code
              ? 'bg-brand-600 text-white'
              : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700',
          )}
        >
          {code === 'tr' ? 'Türkçe' : 'English'}
        </button>
      ))}
    </div>
  )
}

export { X }
