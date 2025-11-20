import { test, expect } from '@playwright/test';
import { setUserContext } from '../src/utils/utils';
import {
	showAdminSettings,
	toggleSwitch,
	sendChatMessage,
	showStartPage
} from '../src/utils/navigation';

test('Test - Wiki Grounding Availability', async ({ page }, testInfo) => {
	const timeout = parseInt(process.env.LONG_TIMEOUT as string) || 120000;
	test.setTimeout(timeout); // Set timeout to LONG_TIMEOUT

	await showStartPage(page);

	await page.getByLabel('More').click();

	await toggleSwitch(
		page.getByRole('button', { name: 'Wiki Grounding' }).getByRole('switch'),
		true
	);

	await page.locator('body').press('Escape');
	await expect(page.locator('#chat-container')).toContainText('Wiki Grounding');
	const response = await sendChatMessage(page, 'Who is the current Canadian Prime Minister?');
	await expect(response).toContain('Carney');
	await test.info().attach('Results', {
		body: `Chat response: ${response}`,
		contentType: 'text/plain'
	});

	await page.close();
});
