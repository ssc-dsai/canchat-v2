import { defineConfig, devices} from '@playwright/test';

// Env variables
process.env.BASE_PATH = process.cwd();

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
	reporter: [
		['html', { open: 'never' }],
		['json', { outputFile: './playwright-report/results.json' }]
	],
	/* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
	use: {
		/* Base URL to use in actions like `await page.goto('/')`. */
		baseURL: 'http://localhost:8080',

		/* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
		trace: 'on',

		// Capture screenshot after each test failure.
		screenshot: 'only-on-failure',

		// Record video only when retrying a test for the first time.
		video: 'on-first-retry'
	},
	expect: {
		timeout: 3000
	},
	webServer: {
		command: 'npm run start',
		url: 'http://localhost:8080',
		timeout: 120 * 1000,
		reuseExistingServer: !process.env.CI,
  	},
	/* Configure projects for major browsers */
	projects: [
		// Setup project
		{ name: 'setup', testMatch: /.*\.setup\.ts/ },
		{
			name: 'core',
			use: {
				...devices['Desktop Chrome'],
				storageState: 'tests/playwright/.auth/admin.json'
			},
			testDir: './tests/e2e/core',
			dependencies: ['setup']
		},
		{
			name: 'chromium-admin',
			use: {
				...devices['Desktop Chrome'],
				storageState: 'tests/playwright/.auth/admin.json'
			},
			dependencies: ['core'],
			testDir: './tests/e2e/releases'
		},
		{
			name: 'firefox-admin',
			use: {
				...devices['Desktop Firefox'],
				storageState: 'tests/playwright/.auth/admin.json'
			},
			dependencies: ['core'],
			testDir: './tests/e2e/releases'
		},
		{
			name: 'chromium-globalanalyst',
			use: {
				...devices['Desktop Chrome'],
				storageState: 'tests/playwright/.auth/globalanalyst.json'
			},
			dependencies: ['core'],
			testDir: './tests/e2e/releases'
		},
		{
			name: 'firefox-globalanalyst',
			use: {
				...devices['Desktop Firefox'],
				storageState: 'tests/playwright/.auth/globalanalyst.json'
			},
			dependencies: ['core'],
			testDir: './tests/e2e/releases'
		},
		{
			name: 'chromium-analyst',
			use: {
				...devices['Desktop Chrome'],
				storageState: 'tests/playwright/.auth/analyst.json'
			},
			dependencies: ['core'],
			testDir: './tests/e2e/releases'
		},
		{
			name: 'firefox-analyst',
			use: {
				...devices['Desktop Firefox'],
				storageState: 'tests/playwright/.auth/analyst.json'
			},
			dependencies: ['core'],
			testDir: './tests/e2e/releases'
		},
		{
			name: 'chromium-user',
			use: {
				...devices['Desktop Chrome'],
				storageState: 'tests/playwright/.auth/user.json'
			},
			dependencies: ['core'],
			testDir: './tests/e2e/releases'
		},
		{
			name: 'firefox-user',
			use: {
				...devices['Desktop Firefox'],
				storageState: 'tests/playwright/.auth/user.json'
			},
			dependencies: ['core'],
			testDir: './tests/e2e/releases'
		},
		{ name: 'test', testMatch: /launch.spec.ts/ }
	]
});
