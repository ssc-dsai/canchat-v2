import { defineConfig, devices,  Page  } from '@playwright/test';

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
import dotenv from 'dotenv';
import path from 'path';
dotenv.config({ path: path.resolve(__dirname, '.env') });


export default defineConfig({
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
    baseURL: process.env.CANCHAT_URL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    // Setup project
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium-admin',
      use: { ...devices['Desktop Chrome'], 
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'firefox-admin',
      use: { ...devices['Desktop Firefox'], 
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'chromium-globalanalyst',
      use: { ...devices['Desktop Chrome'], 
        storageState: 'playwright/.auth/globalanalyst.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'firefox-globalanalyst',
      use: { ...devices['Desktop Firefox'], 
        storageState: 'playwright/.auth/globalanalyst.json',
      },
      dependencies: ['setup'],
    },    
    {
      name: 'chromium-analyst',
      use: { ...devices['Desktop Chrome'], 
        storageState: 'playwright/.auth/analyst.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'firefox-analyst',
      use: { ...devices['Desktop Firefox'], 
        storageState: 'playwright/.auth/analyst.json',
      },
      dependencies: ['setup'],
    },    
    {
      name: 'chromium-user',
      use: { ...devices['Desktop Chrome'], 
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'firefox-user',
      use: { ...devices['Desktop Firefox'], 
        storageState: 'playwright/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    // {
    //   name: 'chromium',
    //   use: { ...devices['Desktop Chrome'] },
    // },
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
  ],




  
  /* Run your local dev server before starting the tests */
  // webServer: {
  //   command: 'npm run start',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});
