// @ts-check
import { defineConfig } from 'astro/config';

// Root-absolute paths suit a user site or a custom domain.
// For a GitHub project site later, set `base` before building.
export default defineConfig({
  site: 'https://dukyong414.github.io',
  base: '/',
  trailingSlash: 'always',
  build: { format: 'directory' },
  compressHTML: true,
  vite: {
    server: {
      host: '0.0.0.0',
      port: 43123,
      strictPort: true,
    },
  },
});
