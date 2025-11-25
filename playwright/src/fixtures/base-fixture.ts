import { mergeTests, type BrowserContext } from '@playwright/test';
import { authFixture } from './auth-fixture';
import { BasePage, type Language } from '../pages/base.page';
import { ChatPage } from '../pages/chat.page';
import { AdminPage } from '../pages/admin.page';

import { test as baseTest } from '@playwright/test';

type PageFixtures = {
	adminPage: AdminPage; // Returns AdminPage class
	userPage: ChatPage; // Returns ChatPage class (Logged in as 'user')
	analystPage: ChatPage; // Returns ChatPage class (Logged in as 'analyst')
	globalAnalystPage: ChatPage; // Returns ChatPage class (Logged in as 'globalanalyst')
	guestPage: ChatPage; // Returns ChatPage class (No Login)
};

const TEST_LANG = (process.env.TEST_LANG as Language) || 'en-GB';

export const test = mergeTests(authFixture, baseTest).extend<PageFixtures>({
	// --- Admin Fixture ---
	adminPage: async ({ browser, authFiles }, use) => {
		const context = await browser.newContext({ storageState: authFiles.admin });
		const page = await context.newPage();
		const adminPage = new AdminPage(page, TEST_LANG);
		await adminPage.goto('/');
		await use(adminPage);
		await context.close();
	},

	// --- Standard User Fixture ---
	userPage: async ({ browser, authFiles }, use) => {
		const context = await browser.newContext({ storageState: authFiles.user });
		const page = await context.newPage();
		const chatPage = new ChatPage(page, TEST_LANG);
		await chatPage.goto('/');
		await use(chatPage);
		await context.close();
	},

	// --- Analyst Fixture ---
	analystPage: async ({ browser, authFiles }, use) => {
		const context = await browser.newContext({ storageState: authFiles.analyst });
		const page = await context.newPage();
		const chatPage = new ChatPage(page, TEST_LANG);
		await chatPage.goto('/');
		await use(chatPage);
		await context.close();
	},

	// --- Global Analyst Fixture ---
	globalAnalystPage: async ({ browser, authFiles }, use) => {
		const context = await browser.newContext({ storageState: authFiles.globalAnalyst });
		const page = await context.newPage();
		const chatPage = new ChatPage(page, TEST_LANG);
		await chatPage.goto('/');
		await use(chatPage);
		await context.close();
	},

	// --- Guest/No-Auth Fixture ---
	guestPage: async ({ browser }, use) => {
		// Context with no storage state
		const context = await browser.newContext();
		const page = await context.newPage();
		const chatPage = new ChatPage(page, TEST_LANG);
		await chatPage.goto('/auth');
		await use(chatPage);
		await context.close();
	}
});

export { expect } from '@playwright/test';
