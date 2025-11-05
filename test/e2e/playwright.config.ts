import { defineConfig, devices, Page } from '@playwright/test';

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
import dotenv from 'dotenv';
import path from 'path';

// Env variables
process.env.BASE_PATH = __dirname;
dotenv.config({ path: path.resolve(__dirname, '.env') });

// Long test timeout
process.env.LONG_TIMEOUT = '180000';

export default defineConfig({
  /* Global test timeout */
  timeout: 60000,
  /* Directory for test files */
  testDir: './tests',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: "http://localhost:8080",

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on',

    // Capture screenshot after each test failure.
    screenshot: 'only-on-failure',

    // Record video only when retrying a test for the first time.
    video: 'on-first-retry',

  },
  expect: {
    timeout: 3000,
  },
  /* Configure projects for major browsers */
  projects: [
    // Setup project
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'core',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/admin.json',
      },
      testDir: './tests/core',
      dependencies: ['setup'],
    },
    {
      name: 'chromium-admin',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['core'],
      testDir: './tests/releases',
    },
    {
      name: 'firefox-admin',
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['core'],
      testDir: './tests/releases',
    },
    {
      name: 'chromium-globalanalyst',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/globalanalyst.json',
      },
      dependencies: ['core'],
      testDir: './tests/releases',
    },
    {
      name: 'firefox-globalanalyst',
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'playwright/.auth/globalanalyst.json',
      },
      dependencies: ['core'],
      testDir: './tests/releases',
    },
    {
      name: 'chromium-analyst',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/analyst.json',
      },
      dependencies: ['core'],
      testDir: './tests/releases',
    },
    {
      name: 'firefox-analyst',
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'playwright/.auth/analyst.json',
      },
      dependencies: ['core'],
      testDir: './tests/releases',
    },
    {
      name: 'chromium-user',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['core'],
      testDir: './tests/releases',
    },
    {
      name: 'firefox-user',
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['core'],
      testDir: './tests/releases',
    },
    { name: 'test', testMatch: /launch.spec.ts/ },
  ],

});
