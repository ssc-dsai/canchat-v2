import { Page, Locator, expect } from '@playwright/test';

export async function showSidebar(page: Page, visibility: 'show' | 'hide' | 'toggle' = 'show') {
	const toggleButton = '#sidebar-toggle-button';
	const hideButton = '#hide-sidebar-button';

	const visibleButton = await Promise.race([
		page.waitForSelector(toggleButton, { state: 'visible' }).then(() => toggleButton),
		page.waitForSelector(hideButton, { state: 'visible' }).then(() => hideButton)
	]);

	if (
		(visibility === 'show' && visibleButton === toggleButton) ||
		(visibility === 'hide' && visibleButton === hideButton) ||
		visibility === 'toggle'
	) {
		console.log('Toggling sidebar.');
		await page.click(visibleButton);
	}
}

export async function setLanguage(page: Page, language: 'en' | 'fr' | 'toggle' = 'en') {
	const engButton = await page.locator(
		"//button[contains(@class,'group')][./div[contains(normalize-space(text()),'FR')]]"
	);
	const frButton = await page.locator(
		"//button[contains(@class,'group')][./div[contains(normalize-space(text()),'EN')]]"
	);

	await waitToSettle(page);

	const languageButton = await Promise.race([
		engButton.waitFor({ state: 'visible' }).then(() => engButton),
		frButton.waitFor({ state: 'visible' }).then(() => frButton)
	]);

	if (
		(language === 'en' && languageButton !== engButton) ||
		(language === 'fr' && languageButton !== frButton) ||
		language === 'toggle'
	) {
		console.log('Changing language to', language);
		await languageButton.click();
	}

	await waitToSettle(page);
}

export async function showAdminSettings(
	page: Page,
	menu: string = 'Settings',
	section: string = 'General'
) {
	await page.goto('/');
	await waitToSettle(page, 250);
	await page.getByRole('button', { name: 'User profile' }).click();
	await page.getByRole('menuitem', { name: 'Admin Panel' }).click();
	await page.getByRole('link', { name: menu }).click();
	await waitToSettle(page, 250);
	await page.getByRole('button', { name: section }).click();
	await waitToSettle(page, 250);
}

export async function waitToSettle(page: Page, stableMs: number = 500, timeoutMs: number = 30000) {
	// Ensure navigation/load finished first
	await page.waitForURL(page.url());
	await page.waitForLoadState('networkidle');

	// Wait until the body content hasn't changed for `stableMs` milliseconds.

	await page.waitForFunction(
		// pageFunction runs in browser context
		({ stableMs }) => {
			const body = document.querySelector('body');
			if (!body) return false;
			const html = body.innerHTML;

			// Initialize snapshot storage if missing
			if (!(window as any).__lastBodySnapshot) {
				(window as any).__lastBodySnapshot = { html, time: Date.now() };
				return false;
			}

			const snap = (window as any).__lastBodySnapshot;
			if (snap.html !== html) {
				snap.html = html;
				snap.time = Date.now();
			}

			return Date.now() - snap.time >= stableMs;
		},
		{ stableMs },
		{ timeout: timeoutMs }
	);
}

export async function showStartPage(page: Page, language: 'en' | 'fr' = 'en') {
	await showPage(page, '/');
	await showSidebar(page, 'show');
	await setLanguage(page, language);
}

export async function showPage(page: Page, url: string) {
	await waitToSettle(page);
	await page.goto(url);
	await page
		.locator("//img[@id='logo'][@alt='CANChat Logo'][@src='/static/splash.png']")
		.waitFor({ state: 'detached', timeout: 10000 })
		.catch(() => {});
	await waitToSettle(page);
}

export async function sendChatMessage(
	page: Page,
	message: string,
	idleMessage: string = ''
): Promise<string> {
	await waitToSettle(page);

	await page.locator('#chat-input').fill(message);
	await page.getByRole('button', { name: 'Send message' }).click();

	const selector = '#response-content-container';

	// Wait for the response to be populated
	await page.waitForSelector(selector, { state: 'visible' });

	await page.waitForFunction(
		({ selector, idleMessage }) => {
			const el = document.querySelector(selector);
			console.log('el', el?.textContent);
			if (!el) return false;
			const text = el.textContent?.trim() || '';
			return text.length > 0 && (idleMessage.length === 0 || !text.includes(idleMessage));
		},
		{ selector, idleMessage },
		{ timeout: 180000 }
	);

	await waitToSettle(page, 1500);

	return (await page.locator(selector).textContent()) ?? '';
}

export async function toggleSwitch(locator: Locator, checked: boolean = true) {
	await locator.waitFor({ state: 'visible' });
	await expect(locator).toHaveAttribute('data-state', /^(checked|unchecked)$/);

	// Await the promise before comparing
	const currentState = await locator.getAttribute('data-state');
	if ((currentState === 'checked') !== checked) {
		await locator.click();
	}
}
