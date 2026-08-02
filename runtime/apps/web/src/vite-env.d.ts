/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_HOST_URL?: string;
  readonly VITE_DEFAULT_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
