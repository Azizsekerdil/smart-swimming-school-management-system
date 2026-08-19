/// <reference types="vite/client" />

/**
 * Vite ortam değişkeni tipleri / Vite environment types.
 * `import.meta.env` ve CSS/varlık import'ları bu referansla tanınır.
 */
interface ImportMetaEnv {
  readonly DEV: boolean
  readonly PROD: boolean
  readonly MODE: string
  readonly BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
