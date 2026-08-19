/** Eğitim Merkezi: adım adım rehberler ve ilerleme takibi / Training Center. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle2, ChevronLeft, ChevronRight, Circle, CircleDot, ExternalLink,
  GraduationCap, PlayCircle, Sparkles,
} from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import {
  Alert, Badge, Card, EmptyState, ErrorState, LoadingState, Modal, PageHeader,
  ProgressBar, StatCard, StatusBadge, Tabs,
} from '@/components/ui'
import { get, post } from '@/lib/api'
import { formatDuration, formatNumber, formatPercent } from '@/lib/format'
import { toastError, toastSuccess } from '@/lib/store'
import type { TrainingOverview, Tutorial, TutorialStep } from '@/lib/types'

// Çeviri dosyasında karşılığı bulunan eğitim kategorileri
const CATEGORIES = ['basics', 'operations', 'finance', 'sports', 'management', 'system', 'ai']

/** Gövde metnindeki **kalın** işaretlerini gerçek strong etiketine çevirir. */
function renderRichText(text: string): ReactNode[] {
  // split, yakalama grubu sayesinde tek/çift indeksleri sırayla düz/kalın verir
  return text.split(/\*\*(.+?)\*\*/g).map((part, index) =>
    index % 2 === 1 ? (
      <strong key={index} className="font-semibold text-slate-900 dark:text-slate-100">
        {part}
      </strong>
    ) : (
      <span key={index}>{part}</span>
    ),
  )
}

/** Eğitim durumuna göre ikon */
function StatusIcon({ status }: { status: string }) {
  if (status === 'completed') {
    return <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
  }
  if (status === 'in_progress') {
    return <CircleDot className="h-4 w-4 shrink-0 text-amber-500" />
  }
  return <Circle className="h-4 w-4 shrink-0 text-slate-300 dark:text-slate-600" />
}

export default function TrainingPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isTR = i18n.language === 'tr'

  const [tab, setTab] = useState<'recommended' | 'all'>('recommended')
  const [category, setCategory] = useState('')
  const [active, setActive] = useState<Tutorial | null>(null)
  const [stepIndex, setStepIndex] = useState(0)

  const overviewQuery = useQuery({
    queryKey: ['training-overview', i18n.language],
    queryFn: () => get<TrainingOverview>('/training/overview'),
  })

  const tutorialsQuery = useQuery({
    queryKey: ['training-tutorials', tab, category],
    queryFn: () =>
      get<Tutorial[]>('/training/tutorials', {
        recommended_only: tab === 'recommended',
        ...(category ? { category } : {}),
      }),
  })

  // Genel ilerleme kartından bir eğitime tıklanınca tam içeriği çekilir
  const openMutation = useMutation({
    mutationFn: (tutorialId: string) => get<Tutorial>(`/training/tutorials/${tutorialId}`),
    onSuccess: (tutorial) => openTutorial(tutorial),
    onError: (error) => toastError(error),
  })

  const progressMutation = useMutation({
    mutationFn: (payload: {
      tutorial_id: string
      current_step: number
      status?: 'in_progress' | 'completed'
    }) => post<Tutorial>('/training/progress', payload),
    onSuccess: (updated) => {
      setActive(updated)
      void queryClient.invalidateQueries({ queryKey: ['training-tutorials'] })
      void queryClient.invalidateQueries({ queryKey: ['training-overview'] })
    },
    onError: (error) => toastError(error),
  })

  function statusLabel(status: string): string {
    if (status === 'completed') return t('training.completed')
    if (status === 'in_progress') return t('training.inProgress')
    return t('training.notStarted')
  }

  function openTutorial(tutorial: Tutorial) {
    // Tamamlanmış eğitimler baştan, yarım kalanlar kaldığı adımdan açılır
    const lastIndex = Math.max(tutorial.total_steps - 1, 0)
    const start = tutorial.status === 'completed' ? 0 : Math.min(Math.max(tutorial.current_step, 0), lastIndex)
    setActive(tutorial)
    setStepIndex(start)
  }

  function goNext() {
    if (!active) return
    const next = Math.min(stepIndex + 1, Math.max(active.total_steps - 1, 0))
    setStepIndex(next)
    progressMutation.mutate({ tutorial_id: active.id, current_step: next, status: 'in_progress' })
  }

  function goBack() {
    if (!active || stepIndex === 0) return
    const previous = stepIndex - 1
    setStepIndex(previous)
    progressMutation.mutate({ tutorial_id: active.id, current_step: previous, status: 'in_progress' })
  }

  function completeTutorial() {
    if (!active) return
    progressMutation.mutate(
      { tutorial_id: active.id, current_step: active.total_steps, status: 'completed' },
      {
        onSuccess: (updated) => {
          toastSuccess(t('training.completed'), isTR ? updated.title_tr : updated.title_en)
          setActive(null)
        },
      },
    )
  }

  function goToScreen(route: string) {
    setActive(null)
    navigate(route)
  }

  const overview = overviewQuery.data
  const tutorials = tutorialsQuery.data ?? []
  const step: TutorialStep | undefined = active?.steps[stepIndex]
  const stepRoute = step?.target_route ?? null
  const stepHint = (isTR ? step?.action_hint_tr : step?.action_hint_en) ?? null
  const isLastStep = active ? stepIndex >= active.total_steps - 1 : false
  const modalPercent = active && active.total_steps > 0
    ? ((stepIndex + 1) / active.total_steps) * 100
    : 0

  return (
    <>
      <PageHeader
        title={t('training.title')}
        subtitle={t('training.subtitle')}
        icon={<GraduationCap className="h-5 w-5" />}
        actions={
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => navigate('/help')}
          >
            {t('help.title')}
          </button>
        }
      />

      {/* Genel ilerleme */}
      {overviewQuery.isLoading ? (
        <LoadingState />
      ) : overviewQuery.error ? (
        <ErrorState error={overviewQuery.error} onRetry={overviewQuery.refetch} />
      ) : overview ? (
        <>
          <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label={t('training.overallProgress')}
              value={formatPercent(overview.overall_percent)}
              icon={<Sparkles className="h-5 w-5" />}
              tone="brand"
            />
            <StatCard
              label={t('training.tutorials')}
              value={formatNumber(overview.total_tutorials)}
              icon={<GraduationCap className="h-5 w-5" />}
              tone="neutral"
            />
            <StatCard
              label={t('training.completed')}
              value={formatNumber(overview.completed)}
              icon={<CheckCircle2 className="h-5 w-5" />}
              tone="success"
            />
            <StatCard
              label={t('training.inProgress')}
              value={formatNumber(overview.in_progress)}
              icon={<PlayCircle className="h-5 w-5" />}
              tone={overview.in_progress > 0 ? 'warning' : 'neutral'}
            />
          </div>

          <Card title={t('training.overallProgress')} className="mb-6">
            <ProgressBar
              value={overview.overall_percent}
              tone={overview.overall_percent >= 80 ? 'success' : 'brand'}
              showLabel
            />
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              {overview.completed} / {overview.total_tutorials} · {t('training.completed')}
            </p>
          </Card>

          {/* Eğitim izleri */}
          {overview.tracks.length === 0 ? (
            <Card className="mb-6">
              <EmptyState title={t('common.noData')} icon={<GraduationCap className="h-6 w-6" />} />
            </Card>
          ) : (
            <div className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {overview.tracks.map((track) => (
                <Card
                  key={track.id}
                  title={
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="card-title">{track.title}</h2>
                      {track.recommended && <Badge tone="info">{t('training.recommended')}</Badge>}
                    </div>
                  }
                >
                  <div className="mb-3 flex items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
                    <span>
                      {track.completed} / {track.total}
                    </span>
                    <span className="font-medium text-slate-700 dark:text-slate-200">
                      {formatPercent(track.percent)}
                    </span>
                  </div>
                  <ProgressBar
                    value={track.percent}
                    tone={track.percent >= 100 ? 'success' : track.percent > 0 ? 'brand' : 'warning'}
                  />
                  <ul className="mt-3 space-y-1.5">
                    {track.tutorials.map((item) => (
                      <li key={item.id}>
                        <button
                          type="button"
                          onClick={() => openMutation.mutate(item.id)}
                          disabled={openMutation.isPending}
                          className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm text-slate-700 transition-colors hover:bg-slate-100 disabled:opacity-60 dark:text-slate-300 dark:hover:bg-slate-700/50"
                        >
                          <StatusIcon status={item.status} />
                          <span className="min-w-0 flex-1 truncate">{item.title}</span>
                          <span className="shrink-0 text-xs text-slate-400">
                            {formatDuration(item.minutes)}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </Card>
              ))}
            </div>
          )}
        </>
      ) : null}

      {/* Eğitim listesi */}
      <Tabs
        tabs={[
          { id: 'recommended', label: t('training.recommended'), icon: <Sparkles className="h-4 w-4" /> },
          { id: 'all', label: t('training.allTutorials'), icon: <GraduationCap className="h-4 w-4" /> },
        ]}
        active={tab}
        onChange={(id) => setTab(id === 'all' ? 'all' : 'recommended')}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <select
          className="select w-auto"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          aria-label={t('common.filter')}
        >
          <option value="">{t('common.all')}</option>
          {CATEGORIES.map((item) => (
            <option key={item} value={item}>
              {t(`training.categories.${item}`, item)}
            </option>
          ))}
        </select>
        {(category || tab !== 'recommended') && (
          <button
            type="button"
            className="btn-ghost btn-sm"
            onClick={() => {
              setCategory('')
              setTab('recommended')
            }}
          >
            {t('common.clearFilters')}
          </button>
        )}
        <span className="ml-auto text-xs text-slate-500 dark:text-slate-400">
          {t('common.total')}: {tutorials.length}
        </span>
      </div>

      {tutorialsQuery.isLoading ? (
        <LoadingState />
      ) : tutorialsQuery.error ? (
        <ErrorState error={tutorialsQuery.error} onRetry={tutorialsQuery.refetch} />
      ) : tutorials.length === 0 ? (
        <Card>
          <EmptyState
            title={t('common.noResults')}
            description={t('training.subtitle')}
            icon={<GraduationCap className="h-6 w-6" />}
            action={
              <button type="button" className="btn-secondary btn-sm" onClick={() => setTab('all')}>
                {t('training.allTutorials')}
              </button>
            }
          />
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {tutorials.map((tutorial) => {
            const firstRoute = tutorial.steps[0]?.target_route ?? null
            return (
            <Card key={tutorial.id} className="flex flex-col">
              <div className="flex items-start justify-between gap-2">
                <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {isTR ? tutorial.title_tr : tutorial.title_en}
                </h2>
                <StatusBadge status={tutorial.status} label={statusLabel(tutorial.status)} />
              </div>
              <p className="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                {isTR ? tutorial.description_tr : tutorial.description_en}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Badge tone="neutral">{t(`training.categories.${tutorial.category}`, tutorial.category)}</Badge>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  {formatDuration(tutorial.estimated_minutes)}
                </span>
                <span className="text-xs text-slate-400">
                  {tutorial.total_steps} {t('training.progress').toLowerCase()}
                </span>
              </div>
              <div className="mt-3">
                <ProgressBar
                  value={tutorial.progress_percent}
                  tone={tutorial.status === 'completed' ? 'success' : 'brand'}
                  showLabel
                />
              </div>
              <div className="mt-4 flex items-center gap-2">
                <button
                  type="button"
                  className="btn-primary btn-sm"
                  onClick={() => openTutorial(tutorial)}
                >
                  <PlayCircle className="h-4 w-4" />
                  {tutorial.status === 'completed'
                    ? t('training.restart')
                    : tutorial.status === 'in_progress'
                      ? t('training.continue')
                      : t('training.start')}
                </button>
                {firstRoute && (
                  <button
                    type="button"
                    className="btn-ghost btn-sm"
                    onClick={() => navigate(firstRoute)}
                    title={t('training.goToScreen')}
                    aria-label={t('training.goToScreen')}
                  >
                    <ExternalLink className="h-4 w-4" />
                  </button>
                )}
              </div>
            </Card>
            )
          })}
        </div>
      )}

      {/* Adım adım eğitim modalı */}
      <Modal
        open={active !== null}
        onClose={() => setActive(null)}
        size="lg"
        title={active ? (isTR ? active.title_tr : active.title_en) : ''}
        footer={
          active ? (
            <div className="flex w-full flex-wrap items-center justify-between gap-2">
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {t('training.step', { current: stepIndex + 1, total: active.total_steps })}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={goBack}
                  disabled={stepIndex === 0 || progressMutation.isPending}
                >
                  <ChevronLeft className="h-4 w-4" />
                  {t('common.back')}
                </button>
                {isLastStep ? (
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    onClick={completeTutorial}
                    disabled={progressMutation.isPending}
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {t('training.markComplete')}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    onClick={goNext}
                    disabled={progressMutation.isPending}
                  >
                    {t('common.next')}
                    <ChevronRight className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          ) : undefined
        }
      >
        {active && step ? (
          <div className="space-y-4">
            <div>
              <p className="mb-1.5 text-xs font-medium text-brand-600 dark:text-brand-400">
                {t('training.step', { current: stepIndex + 1, total: active.total_steps })}
              </p>
              <ProgressBar value={modalPercent} tone="brand" />
            </div>

            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                {isTR ? step.title_tr : step.title_en}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                {renderRichText(isTR ? step.body_tr : step.body_en)}
              </p>
            </div>

            {stepHint && <Alert tone="info">{stepHint}</Alert>}

            {stepRoute && (
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => goToScreen(stepRoute)}
              >
                <ExternalLink className="h-4 w-4" />
                {t('training.goToScreen')}
              </button>
            )}

            {/* Adım haritası */}
            <ol className="space-y-1 border-t border-slate-200 pt-3 dark:border-slate-700">
              {active.steps.map((item, index) => (
                <li key={item.order}>
                  <button
                    type="button"
                    onClick={() => setStepIndex(index)}
                    className={
                      index === stepIndex
                        ? 'flex w-full items-center gap-2 rounded-lg bg-brand-50 px-2 py-1.5 text-left text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
                        : 'flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700/50'
                    }
                  >
                    <StatusIcon
                      status={
                        index < active.current_step
                          ? 'completed'
                          : index === stepIndex
                            ? 'in_progress'
                            : 'not_started'
                      }
                    />
                    <span className="min-w-0 flex-1 truncate">
                      {index + 1}. {isTR ? item.title_tr : item.title_en}
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          </div>
        ) : (
          <LoadingState />
        )}
      </Modal>
    </>
  )
}
