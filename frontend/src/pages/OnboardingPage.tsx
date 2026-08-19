/** İlk kurulum sihirbazı / First-run onboarding wizard. */
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowRight, CheckCircle2, Circle, ExternalLink, Waves } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { Alert, ErrorState, LoadingState, ProgressBar, Spinner } from '@/components/ui'
import { get, post } from '@/lib/api'
import { formatPercent } from '@/lib/format'
import { toastError, toastSuccess, useAuth } from '@/lib/store'
import type { OnboardingState } from '@/lib/types'

/** Sunucudan gelen kurulum adımı (dile göre çevrilmiş olarak döner) */
interface OnboardingStepInfo {
  id: string
  title: string
  description: string
  route: string
}

/** Adımın tamamlanma durumunu OnboardingState alanlarından okur. */
function isStepDone(id: string, state: OnboardingState): boolean {
  switch (id) {
    case 'organization':
      return state.organization_configured
    case 'pool':
    case 'lanes':
      return state.has_pool
    case 'instructor':
      return state.has_instructor
    case 'student':
      return state.has_student
    case 'ai':
      return state.ai_configured
    case 'backup':
      return state.backup_configured
    case 'finish':
      return state.completed
    default:
      return state.steps_done.includes(id)
  }
}

export default function OnboardingPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const stateQuery = useQuery({
    queryKey: ['onboarding-state'],
    queryFn: () => get<OnboardingState>('/training/onboarding'),
  })

  const stepsQuery = useQuery({
    queryKey: ['onboarding-steps', i18n.language],
    queryFn: () => get<OnboardingStepInfo[]>('/training/onboarding/steps'),
  })

  // Sihirbazdan çıkış: her iki uç da kullanıcı kaydını günceller,
  // bu yüzden oturum yeniden yüklenip ana sayfaya dönülür.
  async function finishSession() {
    await useAuth.getState().loadSession()
    navigate('/', { replace: true })
  }

  const skipMutation = useMutation({
    mutationFn: () => post('/training/onboarding/skip'),
    onSuccess: async () => {
      toastSuccess(t('common.success'), t('training.onboardingSubtitle'))
      await finishSession()
    },
    onError: (error) => toastError(error),
  })

  const completeMutation = useMutation({
    mutationFn: () => post('/training/onboarding/complete'),
    onSuccess: async () => {
      toastSuccess(t('common.success'), t('training.onboarding'))
      await finishSession()
    },
    onError: (error) => toastError(error),
  })

  const busy = skipMutation.isPending || completeMutation.isPending

  if (stateQuery.isLoading || stepsQuery.isLoading) {
    return (
      <div className="grid min-h-screen place-items-center bg-slate-50 dark:bg-surface-dark">
        <LoadingState />
      </div>
    )
  }

  if (stateQuery.error || stepsQuery.error) {
    return (
      <div className="grid min-h-screen place-items-center bg-slate-50 p-6 dark:bg-surface-dark">
        <div className="w-full max-w-lg">
          <ErrorState
            error={stateQuery.error ?? stepsQuery.error}
            onRetry={() => {
              void stateQuery.refetch()
              void stepsQuery.refetch()
            }}
          />
          <div className="mt-4 text-center">
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => skipMutation.mutate()}
              disabled={busy}
            >
              {t('common.skip')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  const state = stateQuery.data
  const steps = stepsQuery.data ?? []
  if (!state) return null

  const doneCount = steps.filter((step) => isStepDone(step.id, state)).length
  const percent = steps.length > 0 ? (doneCount / steps.length) * 100 : 0
  const firstPending = steps.find((step) => !isStepDone(step.id, state))
  const current =
    steps.find((step) => step.id === selectedId) ?? firstPending ?? steps[steps.length - 1]

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8 dark:bg-surface-dark">
      <div className="mx-auto w-full max-w-5xl">
        {/* Hoş geldiniz */}
        <header className="mb-6 flex items-start gap-3">
          <div className="mt-0.5 rounded-xl bg-brand-500 p-2.5 text-white shadow-card">
            <Waves className="h-6 w-6" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100 sm:text-2xl">
              {t('training.onboardingWelcome')}
            </h1>
            <p className="mt-1 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
              {t('training.onboardingIntro')}
            </p>
          </div>
        </header>

        {/* İlerleme */}
        <div className="card mb-5 p-4">
          <div className="mb-2 flex items-center justify-between gap-3 text-sm">
            <span className="font-medium text-slate-700 dark:text-slate-200">
              {t('training.onboarding')}
            </span>
            <span className="text-slate-500 dark:text-slate-400">
              {doneCount} / {steps.length} · {formatPercent(percent)}
            </span>
          </div>
          <ProgressBar value={percent} tone={percent >= 100 ? 'success' : 'brand'} />
        </div>

        <div className="grid gap-4 md:grid-cols-[280px_minmax(0,1fr)]">
          {/* Adım listesi */}
          <nav className="card p-2">
            <ul className="space-y-0.5">
              {steps.map((step, index) => {
                const done = isStepDone(step.id, state)
                const isCurrent = current?.id === step.id
                return (
                  <li key={step.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(step.id)}
                      className={
                        isCurrent
                          ? 'flex w-full items-center gap-2.5 rounded-lg bg-brand-50 px-3 py-2 text-left dark:bg-brand-900/30'
                          : 'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left hover:bg-slate-100 dark:hover:bg-slate-700/50'
                      }
                    >
                      {done ? (
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                      ) : (
                        <Circle className="h-4 w-4 shrink-0 text-slate-300 dark:text-slate-600" />
                      )}
                      <span className="min-w-0 flex-1">
                        <span
                          className={
                            isCurrent
                              ? 'block truncate text-sm font-medium text-brand-700 dark:text-brand-300'
                              : 'block truncate text-sm text-slate-700 dark:text-slate-200'
                          }
                        >
                          {index + 1}. {step.title}
                        </span>
                        <span
                          className={
                            done
                              ? 'text-xs text-emerald-600 dark:text-emerald-400'
                              : 'text-xs text-slate-400 dark:text-slate-500'
                          }
                        >
                          {done ? t('training.stepDone') : t('training.stepPending')}
                        </span>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </nav>

          {/* Mevcut adım */}
          <section className="card p-5">
            {current ? (
              <>
                <p className="text-xs font-medium uppercase tracking-wide text-brand-600 dark:text-brand-400">
                  {t('training.step', {
                    current: steps.findIndex((step) => step.id === current.id) + 1,
                    total: steps.length,
                  })}
                </p>
                <h2 className="mt-1.5 text-lg font-semibold text-slate-900 dark:text-slate-100">
                  {current.title}
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                  {current.description}
                </p>

                <div className="mt-4">
                  {isStepDone(current.id, state) ? (
                    <Alert tone="success" title={t('training.stepDone')} />
                  ) : (
                    <Alert tone="info" title={t('training.stepPending')} />
                  )}
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => navigate(current.route)}
                  >
                    <ExternalLink className="h-4 w-4" />
                    {t('training.goToScreen')}
                  </button>
                  {firstPending && firstPending.id !== current.id && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => setSelectedId(firstPending.id)}
                    >
                      {t('common.next')}
                      <ArrowRight className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => {
                      void stateQuery.refetch()
                    }}
                    disabled={stateQuery.isFetching}
                  >
                    {stateQuery.isFetching && <Spinner />}
                    {t('common.refresh')}
                  </button>
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-500 dark:text-slate-400">{t('common.noData')}</p>
            )}
          </section>
        </div>

        {/* Alt işlemler */}
        <footer className="mt-6 flex flex-col gap-3 border-t border-slate-200 pt-4 dark:border-slate-700 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t('training.onboardingSubtitle')}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => skipMutation.mutate()}
              disabled={busy}
            >
              {skipMutation.isPending && <Spinner />}
              {t('common.skip')}
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => completeMutation.mutate()}
              disabled={busy}
            >
              {completeMutation.isPending && <Spinner />}
              <CheckCircle2 className="h-4 w-4" />
              {t('common.finish')}
            </button>
          </div>
        </footer>
      </div>
    </div>
  )
}
