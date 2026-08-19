/**
 * Yerelleştirilmiş biçimlendirme / Locale-aware formatting.
 *
 *  Türkçe : 15.08.2026 · 1.250,50 · %85,4 · 1.250,50 ₺
 *  English: 08/15/2026 · 1,250.50 · 85.4% · $1,250.50
 */
import i18n from './i18n'

export type Locale = 'tr' | 'en'

function currentLocale(): Locale {
  return (i18n.language === 'en' ? 'en' : 'tr') as Locale
}

const INTL_LOCALE: Record<Locale, string> = { tr: 'tr-TR', en: 'en-US' }

let currencyCode = 'TRY'

/** Kurum ayarlarından gelen para birimini uygular */
export function setCurrency(code: string): void {
  if (code) currencyCode = code
}

export function getCurrency(): string {
  return currencyCode
}

// ---------------------------------------------------------------------------
// Sayı
// ---------------------------------------------------------------------------
export function formatNumber(value: number | null | undefined, decimals = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return new Intl.NumberFormat(INTL_LOCALE[currentLocale()], {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatDecimal(value: number | null | undefined, decimals = 2): string {
  return formatNumber(value, decimals)
}

export function formatCurrency(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  try {
    return new Intl.NumberFormat(INTL_LOCALE[currentLocale()], {
      style: 'currency',
      currency: currencyCode,
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value)
  } catch {
    return `${formatNumber(value, decimals)} ${currencyCode}`
  }
}

/** Grafik eksenleri için kısa gösterim: 12,5 B / 1,2 M */
export function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return new Intl.NumberFormat(INTL_LOCALE[currentLocale()], {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  const number = formatNumber(value, decimals)
  return currentLocale() === 'tr' ? `%${number}` : `${number}%`
}

/** Değişim göstergesi: +12,4 / -3,1 */
export function formatDelta(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  const sign = value > 0 ? '+' : ''
  return `${sign}${formatNumber(value, decimals)}`
}

// ---------------------------------------------------------------------------
// Tarih / saat
// ---------------------------------------------------------------------------
function toDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(value: string | Date | null | undefined): string {
  const date = toDate(value)
  if (!date) return '-'
  return currentLocale() === 'tr'
    ? new Intl.DateTimeFormat('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(date)
    : new Intl.DateTimeFormat('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' }).format(date)
}

export function formatDateLong(value: string | Date | null | undefined): string {
  const date = toDate(value)
  if (!date) return '-'
  return new Intl.DateTimeFormat(INTL_LOCALE[currentLocale()], {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

export function formatTime(value: string | Date | null | undefined): string {
  const date = toDate(value)
  if (!date) return '-'
  return new Intl.DateTimeFormat(INTL_LOCALE[currentLocale()], {
    hour: '2-digit',
    minute: '2-digit',
    hour12: currentLocale() === 'en',
  }).format(date)
}

export function formatDateTime(value: string | Date | null | undefined): string {
  const date = toDate(value)
  if (!date) return '-'
  return `${formatDate(date)} ${formatTime(date)}`
}

export function formatTimeRange(
  start: string | Date | null | undefined,
  end: string | Date | null | undefined,
): string {
  if (!start || !end) return '-'
  return `${formatTime(start)} – ${formatTime(end)}`
}

/** "3 gün önce" / "3 days ago" */
export function formatRelative(value: string | Date | null | undefined): string {
  const date = toDate(value)
  if (!date) return '-'
  const seconds = Math.round((date.getTime() - Date.now()) / 1000)
  const formatter = new Intl.RelativeTimeFormat(INTL_LOCALE[currentLocale()], { numeric: 'auto' })

  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['year', 31_536_000],
    ['month', 2_592_000],
    ['week', 604_800],
    ['day', 86_400],
    ['hour', 3_600],
    ['minute', 60],
  ]
  for (const [unit, secondsInUnit] of units) {
    if (Math.abs(seconds) >= secondsInUnit) {
      return formatter.format(Math.round(seconds / secondsInUnit), unit)
    }
  }
  return formatter.format(seconds, 'second')
}

/** ISO tarih (yyyy-MM-dd) - form alanları ve API için */
export function toISODate(value: Date | string | null | undefined): string {
  const date = toDate(value)
  if (!date) return ''
  const offset = date.getTimezoneOffset()
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10)
}

/** ISO tarih-saat, saniyesiz (yyyy-MM-ddTHH:mm) - datetime-local için */
export function toISODateTime(value: Date | string | null | undefined): string {
  const date = toDate(value)
  if (!date) return ''
  const offset = date.getTimezoneOffset()
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 16)
}

export function formatDuration(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) return '-'
  const hours = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  if (currentLocale() === 'tr') {
    return hours ? `${hours} sa ${mins} dk` : `${mins} dk`
  }
  return hours ? `${hours}h ${mins}m` : `${mins}m`
}

// ---------------------------------------------------------------------------
// Yüzme derecesi
// ---------------------------------------------------------------------------
/** 32.45 -> "32.45" · 95.12 -> "1:35.12" */
export function formatSwimTime(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds) || seconds < 0) return '-'
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds - minutes * 60
  if (minutes > 0) {
    return `${minutes}:${remainder.toFixed(2).padStart(5, '0')}`
  }
  return remainder.toFixed(2)
}

/** "1:35.12", "95.12" veya "1.35.12" -> saniye */
export function parseSwimTime(text: string): number | null {
  if (!text?.trim()) return null
  const cleaned = text.trim().replace(',', '.')
  try {
    if (cleaned.includes(':')) {
      const [minutes, seconds] = cleaned.split(':')
      const result = parseInt(minutes, 10) * 60 + parseFloat(seconds)
      return Number.isNaN(result) ? null : result
    }
    const parts = cleaned.split('.')
    if (parts.length === 3) {
      const result = parseInt(parts[0], 10) * 60 + parseFloat(`${parts[1]}.${parts[2]}`)
      return Number.isNaN(result) ? null : result
    }
    const result = parseFloat(cleaned)
    return Number.isNaN(result) ? null : result
  } catch {
    return null
  }
}

/** Derece farkı: -1.24 sn (hızlandı) */
export function formatTimeDelta(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '-'
  const sign = seconds > 0 ? '+' : ''
  const unit = currentLocale() === 'tr' ? 'sn' : 's'
  return `${sign}${seconds.toFixed(2)} ${unit}`
}

export function formatFileSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${formatNumber(bytes / 1024, 1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${formatNumber(bytes / (1024 * 1024), 1)} MB`
  return `${formatNumber(bytes / (1024 * 1024 * 1024), 2)} GB`
}

/** Baş harfler: "Ahmet Yılmaz" -> "AY" */
export function initials(name: string | null | undefined): string {
  if (!name) return '?'
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toLocaleUpperCase('tr-TR'))
    .join('')
}
