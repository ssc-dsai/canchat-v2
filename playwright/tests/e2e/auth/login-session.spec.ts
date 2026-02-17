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

const users = usersData.users as UserRecord[];
const usersForLoginValidation = users;
const usersForSession = users.filter((user) => user.role !== 'pending');

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
				guestPage,
				locale
			}, testInfo) => {
				const page = guestPage.page;
				const authPage = new AuthPage(page, locale as Language);
				const chatPage = new ChatPage(page, locale as Language);

				for (const user of usersForLoginValidation) {
					if (!user) {
						testInfo.annotations.push({
							type: 'warning',
							description: 'Skipping a user because user data is missing.'
						});
						continue;
					}

					await authPage.login(user.email, user.password);

					if (user.role === 'pending') {
						const pendingMessage = page.getByText(getPendingMessage(locale as Language));
						await expect(pendingMessage).toBeVisible({ timeout: 30000 });
						await expect(authPage.signOutButtonPendingUser).toBeVisible({ timeout: 30000 });
						await authPage.signOutPendingUser();
					} else {
						await chatPage.goto(`/?lang=${locale}`);
						await expect(page.locator('#chat-input')).toBeVisible({ timeout: 60000 });
						await chatPage.signOut();
					}
				}
			});

	test('CHAT-LOGIN-TC002: Redirects to login when session token expires', async ({
		guestPage,
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
		const page = guestPage.page;
		const authPage = new AuthPage(page, locale as Language);

		const chatPage = new ChatPage(page, locale as Language);
		await authPage.login(user.email, user.password);
		await chatPage.goto(`/?lang=${locale}`);
		await expect(page.locator('#chat-input')).toBeVisible({ timeout: 60000 });

		await page.evaluate(() => localStorage.removeItem('token'));
		await page.context().clearCookies();

		await page.reload();
		await expect(page).toHaveURL(/\/auth/);

		await authPage.login(user.email, user.password);
		await chatPage.goto(`/?lang=${locale}`);
		await expect(page.locator('#chat-input')).toBeVisible({ timeout: 60000 });
	});

	test('CHAT-SESSION-TC001: User stays connected during session using cookies', async ({
		guestPage,
		locale
	}, testInfo) => {
		const page = guestPage.page;
		const authPage = new AuthPage(page, locale as Language);
		const chatPage = new ChatPage(page, locale as Language);

		for (const user of usersForSession) {
			if (!user) {
				testInfo.annotations.push({
					type: 'warning',
					description: 'Skipping a user because user data is missing.'
				});
				continue;
			}

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
			await page.context().clearCookies().catch(() => {});
			await page.reload();
			await expect(page).toHaveURL(/\/auth/);
		}
	});
});
