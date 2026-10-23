import { defineConfig } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    viewport: { width: 1600, height: 1000 },
    launchOptions: { executablePath: process.env.VIDEOSCRIPT_BROWSER_PATH || undefined },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: (process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python') + ' -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000',
      cwd: '..',
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: false,
      timeout: 30_000,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 10_000 },
      env: { VIDEOSCRIPT_DATA_DIR: join(tmpdir(), `videoscript-e2e-${process.pid}`) },
    },
    {
      command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort',
      url: 'http://127.0.0.1:5173/',
      reuseExistingServer: false,
      timeout: 30_000,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 10_000 },
    },
  ],
});
