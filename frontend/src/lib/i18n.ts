/**
 * Çok dilli destek / Internationalisation.
 * Varsayılan dil Türkçe; İngilizce tam olarak desteklenir.
 */
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from '@/locales/en/translation.json'
import tr from '@/locales/tr/translation.json'

export const SUPPORTED_LANGUAGES = ['tr', 'en'] as const
export type Language = (typeof SUPPORTED_LANGUAGES)[number]

const LANGUAGE_KEY = 'sws-language'

export function getStoredLanguage(): Language {
  const stored = localStorage.getItem(LANGUAGE_KEY)
  return SUPPORTED_LANGUAGES.includes(stored as Language) ? (stored as Language) : 'tr'
}

export function setLanguage(language: Language): void {
  localStorage.setItem(LANGUAGE_KEY, language)
  document.documentElement.lang = language
  void i18n.changeLanguage(language)
}

void i18n.use(initReactI18next).init({
  resources: {
    tr: { translation: tr },
    en: { translation: en },
  },
  lng: getStoredLanguage(),
  fallbackLng: 'tr',
  interpolation: { escapeValue: false },
  returnNull: false,
  // Eksik anahtarları geliştirme sırasında konsola yaz
  saveMissing: false,
  missingKeyHandler: (_lngs, _ns, key) => {
    if (import.meta.env.DEV) {
      console.warn(`[i18n] Eksik çeviri anahtarı / Missing key: ${key}`)
    }
  },
})

document.documentElement.lang = getStoredLanguage()

export default i18n
