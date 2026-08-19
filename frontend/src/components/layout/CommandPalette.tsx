/** Ctrl+K komut paleti / Command palette. */
import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { CornerDownLeft, Search, Terminal } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { get } from '@/lib/api'
import { useUI } from '@/lib/store'
import type { PaletteCommand } from '@/lib/types'

export function CommandPalette() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { paletteOpen, setPaletteOpen } = useUI()
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data } = useQuery({
    queryKey: ['palette-commands'],
    queryFn: () => get<{ commands: PaletteCommand[] }>('/search/commands'),
    staleTime: 10 * 60_000,
    enabled: paletteOpen,
  })

  const commands = useMemo(() => {
    const all = data?.commands ?? []
    if (!query.trim()) return all
    const normalized = query.toLocaleLowerCase('tr-TR')
    return all.filter((command) => command.label.toLocaleLowerCase('tr-TR').includes(normalized))
  }, [data, query])

  useEffect(() => {
    if (paletteOpen) {
      setQuery('')
      setActiveIndex(0)
      setTimeout(() => inputRef.current?.focus(), 30)
    }
  }, [paletteOpen])

  useEffect(() => {
    setActiveIndex(0)
  }, [query])

  if (!paletteOpen) return null

  function run(command: PaletteCommand) {
    setPaletteOpen(false)
    navigate(command.route)
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === 'Escape') {
      setPaletteOpen(false)
    } else if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((index) => Math.min(index + 1, commands.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter' && commands[activeIndex]) {
      event.preventDefault()
      run(commands[activeIndex])
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-[12vh]">
      <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={() => setPaletteOpen(false)} />
      <div
        className="relative w-full max-w-xl animate-slide-up overflow-hidden rounded-xl bg-white shadow-panel dark:bg-surface-dark-alt"
        onKeyDown={onKeyDown}
      >
        <div className="flex items-center gap-3 border-b border-slate-200 px-4 dark:border-slate-700">
          <Terminal className="h-4 w-4 shrink-0 text-slate-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t('commandPalette.placeholder')}
            className="h-12 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400 dark:text-slate-100"
          />
          <kbd className="rounded border border-slate-300 px-1.5 text-[10px] text-slate-400 dark:border-slate-600">
            ESC
          </kbd>
        </div>

        <div className="max-h-[50vh] overflow-y-auto p-2">
          {commands.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-slate-400">{t('commandPalette.noCommands')}</p>
          ) : (
            commands.map((command, index) => (
              <button
                key={command.id}
                type="button"
                onClick={() => run(command)}
                onMouseEnter={() => setActiveIndex(index)}
                className={clsx(
                  'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors',
                  index === activeIndex
                    ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
                    : 'text-slate-700 dark:text-slate-300',
                )}
              >
                <Search className="h-4 w-4 shrink-0 text-slate-400" />
                <span className="flex-1 truncate">{command.label}</span>
                <span className="truncate text-xs text-slate-400">{command.route}</span>
                {index === activeIndex && <CornerDownLeft className="h-3.5 w-3.5 shrink-0 text-slate-400" />}
              </button>
            ))
          )}
        </div>

        <footer className="flex items-center gap-4 border-t border-slate-200 px-4 py-2 text-[11px] text-slate-400 dark:border-slate-700">
          <span>↑↓ gezin</span>
          <span>↵ çalıştır</span>
          <span>esc kapat</span>
        </footer>
      </div>
    </div>
  )
}
