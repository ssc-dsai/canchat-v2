import { test, expect } from '../../../src/fixtures/base-fixture';
import type { Page } from '@playwright/test';
import { AuthPage } from '../../../src/pages/auth.page';
import { ChatPage } from '../../../src/pages/chat.page';
import { type Language } from '../../../src/pages/base.page';
import * as fs from 'fs';
import * as path from 'path';

const usersFile = path.join(process.cwd(), 'playwright/src/test-data/users.json');
type UserRecord = {
	username: string;
	role: string;
	name: string;
	email: string;
	password: string;
};

const usersData = JSON.parse(fs.readFileSync(usersFile, 'utf-8')) as { users: UserRecord[] };

const getUserByUsername = (username: string) =>
	usersData.users.find((u) => u.username === username);

const getPendingMessage = (locale: Language) =>
	locale === 'fr-CA'
		? 'Veuillez patienter pendant que nous activons votre compte.'
		: 'Please wait while we activate your account.';

const rolesToValidate = ['admin', 'pending', 'user', 'analyst', 'globalanalyst'];

const rolesForSession = ['admin', 'user', 'analyst', 'globalanalyst'];

const navigateExternal = async (page: Page) => {
	try {
		await page.goto('https://example.com', { waitUntil: 'domcontentloaded', timeout: 15000 });
	} catch {
		await page.waitForTimeout(500);
	}
};

test.describe('Login Validation & Session Persistence', () => {
	test.setTimeout(180000);

	test('CHAT-LOGIN-TC001: Users can connect with valid credentials', async ({
		browser,
		locale
	}, testInfo) => {
		for (const role of rolesToValidate) {
			const user = getUserByUsername(role);
			if (!user) {
				testInfo.annotations.push({
					type: 'warning',
					description: `Skipping role ${role} because user data is missing.`
				});
				continue;
			}

			const context = await browser.newContext({
				locale: locale,
				permissions: testInfo.project.use.permissions
			});
			const page = await context.newPage();
			const authPage = new AuthPage(page, locale as Language);
			const chatPage = new ChatPage(page, locale as Language);

			await authPage.login(user.email, user.password);

			if (role === 'pending') {
				const pendingMessage = page.getByText(
					/Please wait while we activate your account\.|Veuillez patienter pendant que nous activons votre compte\./i
				);
				const pendingSignOutButton = page.getByRole('button', {
					name: /Sign Out|Déconnexion|Se déconnecter/i
				});
				await expect(pendingMessage).toBeVisible({ timeout: 30000 });
				await expect(pendingSignOutButton).toBeVisible({ timeout: 30000 });
				await pendingSignOutButton.click();
				await expect(page).toHaveURL(/\/auth/);
			} else {
				await chatPage.goto(`/?lang=${locale}`);
				await expect(page.locator('#chat-input')).toBeVisible({ timeout: 60000 });
			}

			await context.close();
		}
	});

	test('CHAT-LOGIN-TC002: Redirects to login when session token expires', async ({
		browser,
		locale
	}, testInfo) => {
		const user = getUserByUsername('user');
		if (!user) {
			testInfo.annotations.push({
				type: 'warning',
				description: 'Skipping because user credentials are missing.'
			});
			return;
		}
		const context = await browser.newContext({
			locale: locale,
			permissions: testInfo.project.use.permissions
		});
		const page = await context.newPage();
		const authPage = new AuthPage(page, locale as Language);

		const chatPage = new ChatPage(page, locale as Language);
		await authPage.login(user.email, user.password);
		await chatPage.goto(`/?lang=${locale}`);
		await expect(page.locator('#chat-input')).toBeVisible({ timeout: 60000 });

		await page.evaluate(() => localStorage.removeItem('token'));
		await context.clearCookies();

		await page.reload();
		await expect(page).toHaveURL(/\/auth/);

		await authPage.login(user.email, user.password);
		await chatPage.goto(`/?lang=${locale}`);
		await expect(page.locator('#chat-input')).toBeVisible({ timeout: 60000 });

		await context.close();
	});

	test('CHAT-SESSION-TC001: User stays connected during session using cookies', async ({
		browser,
		locale
	}, testInfo) => {
		for (const role of rolesForSession) {
			const user = getUserByUsername(role);
			if (!user) {
				testInfo.annotations.push({
					type: 'warning',
					description: `Skipping role ${role} because user data is missing.`
				});
				continue;
			}

			const context = await browser.newContext({
				locale: locale,
				permissions: testInfo.project.use.permissions
			});
			const page = await context.newPage();
			const authPage = new AuthPage(page, locale as Language);
			const chatPage = new ChatPage(page, locale as Language);

			await authPage.login(user.email, user.password);
			await chatPage.goto(`/?lang=${locale}`);
			await expect(page.locator('#chat-input')).toBeVisible({ timeout: 60000 });

			await navigateExternal(page);
			try {
				await chatPage.goto(`/?lang=${locale}`);
			} catch {
				await page.waitForTimeout(500);
				await chatPage.goto(`/?lang=${locale}`);
			}
			await expect(page.locator('#chat-input')).toBeVisible({ timeout: 60000 });

			await page.evaluate(() => localStorage.removeItem('token')).catch(() => {});
			await context.clearCookies().catch(() => {});
			await context.close();
		}
	});
});
