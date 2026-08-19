/** Global arama paneli / Global search overlay. */
import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import {
  Award, CreditCard, LayoutGrid, Search, Trophy, User, Users, Waves,
} from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { Spinner } from '@/components/ui'
import { get } from '@/lib/api'
import { useUI } from '@/lib/store'
import type { SearchResponse } from '@/lib/types'

const GROUP_ICONS: Record<string, ReactNode> = {
  students: <Users className="h-4 w-4" />,
  guardians: <User className="h-4 w-4" />,
  instructors: <Award className="h-4 w-4" />,
  lessons: <LayoutGrid className="h-4 w-4" />,
  payments: <CreditCard className="h-4 w-4" />,
  packages: <CreditCard className="h-4 w-4" />,
  pools: <Waves className="h-4 w-4" />,
  groups: <Users className="h-4 w-4" />,
  competitions: <Trophy className="h-4 w-4" />,
}

const GROUP_LABELS: Record<string, string> = {
  students: 'nav.students',
  guardians: 'nav.guardians',
  instructors: 'nav.instructors',
  lessons: 'nav.lessons',
  payments: 'nav.payments',
  packages: 'membership.packages',
  pools: 'nav.pools',
  groups: 'nav.groups',
  competitions: 'nav.competitions',
}

export function GlobalSearch() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { searchOpen, setSearchOpen } = useUI()
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query), 250)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    if (searchOpen) {
      setQuery('')
      setDebounced('')
      setTimeout(() => inputRef.current?.focus(), 30)
    }
  }, [searchOpen])

  const { data, isFetching } = useQuery({
    queryKey: ['global-search', debounced],
    queryFn: () => get<SearchResponse>('/search', { q: debounced }),
    enabled: searchOpen && debounced.trim().length >= 2,
  })

  const { data: quickStats } = useQuery({
    queryKey: ['search-quick-stats'],
    queryFn: () => get<Record<string, number>>('/search/quick-stats'),
    enabled: searchOpen,
    staleTime: 60_000,
  })

  if (!searchOpen) return null

  const groups = Object.entries(data?.groups ?? {})

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-[10vh]">
      <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={() => setSearchOpen(false)} />
      <div className="relative w-full max-w-2xl animate-slide-up overflow-hidden rounded-xl bg-white shadow-panel dark:bg-surface-dark-alt">
        <div className="flex items-center gap-3 border-b border-slate-200 px-4 dark:border-slate-700">
          <Search className="h-4 w-4 shrink-0 text-slate-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => event.key === 'Escape' && setSearchOpen(false)}
            placeholder={t('common.searchPlaceholder')}
            className="h-12 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400 dark:text-slate-100"
          />
          {isFetching && <Spinner className="text-slate-400" />}
          <kbd className="rounded border border-slate-300 px-1.5 text-[10px] text-slate-400 dark:border-slate-600">
            ESC
          </kbd>
        </div>

        <div className="max-h-[60vh] overflow-y-auto p-2">
          {debounced.trim().length < 2 ? (
            <div className="px-3 py-6">
              <p className="mb-3 text-xs text-slate-400">En az 2 karakter yazın</p>
              {quickStats && (
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(quickStats).map(([key, value]) => (
                    <div key={key} className="rounded-lg bg-slate-50 p-3 text-center dark:bg-slate-800">
                      <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">{value}</p>
                      <p className="mt-0.5 text-[10px] text-slate-500">{key}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : groups.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-slate-400">{t('common.noResults')}</p>
          ) : (
            groups.map(([groupKey, hits]) => (
              <div key={groupKey} className="mb-2">
                <p className="flex items-center gap-2 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  {GROUP_ICONS[groupKey]}
                  {t(GROUP_LABELS[groupKey] ?? groupKey)}
                  <span className="text-slate-300">({hits.length})</span>
                </p>
                {hits.map((hit) => (
                  <button
                    key={`${hit.entity_type}-${hit.id}`}
                    type="button"
                    onClick={() => {
                      setSearchOpen(false)
                      navigate(hit.route)
                    }}
                    className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors hover:bg-slate-100 dark:hover:bg-slate-700"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-slate-800 dark:text-slate-200">{hit.title}</p>
                      {hit.subtitle && (
                        <p className="truncate text-xs text-slate-500 dark:text-slate-400">{hit.subtitle}</p>
                      )}
                    </div>
                    {hit.badge && (
                      <span className={clsx('badge-neutral shrink-0 text-[10px]')}>{hit.badge}</span>
                    )}
                  </button>
                ))}
              </div>
            ))
          )}
        </div>

        {data && (
          <footer className="border-t border-slate-200 px-4 py-2 text-[11px] text-slate-400 dark:border-slate-700">
            {data.total} sonuç · {data.took_ms} ms
          </footer>
        )}
      </div>
    </div>
  )
}
