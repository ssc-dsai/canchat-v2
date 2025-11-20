import { test, expect } from '@playwright/test';
import { setUserContext } from '../src/utils/utils';
import {
	showAdminSettings,
	toggleSwitch,
	sendChatMessage,
	showStartPage
} from '../src/utils/navigation';

test('Test - MCP Availability', async ({ page }, testInfo) => {
	const timeout = parseInt(process.env.LONG_TIMEOUT as string) || 120000;
	test.setTimeout(timeout); // Set timeout to LONG_TIMEOUT

	await showStartPage(page);
	await showAdminSettings(page, 'Settings', 'MCP');

	await toggleSwitch(page.getByRole('switch', { name: 'Enable MCP API' }), true);

	// Check if both services are running
	const time = await page
		.locator(
			"//div[normalize-space(text())='Time Server']/../../..//span[normalize-space(text())='running']"
		)
		.count();
	const news = await page
		.locator(
			"//div[normalize-space(text())='News Server']/../../..//span[normalize-space(text())='running']"
		)
		.count();
	await expect(time).toBeGreaterThan(0);
	await expect(news).toBeGreaterThan(0);

	await showStartPage(page);

	await page.getByLabel('More').click();
	await toggleSwitch(
		page.getByRole('button', { name: 'MCP: Current Time' }).getByRole('switch'),
		true
	);

	await page.locator('body').press('Escape');
	await expect(page.locator('#chat-container')).toContainText('MCP: Current Time');
	var response = await sendChatMessage(page, 'What is the time?', 'Consulting CrewAI agents...');
	await expect(response).toContain('time');

	await page.getByRole('link', { name: 'logo New Chat' }).click();
	await page.getByLabel('More').click();

	await toggleSwitch(
		page.getByRole('button', { name: 'MCP: News Headlines' }).getByRole('switch'),
		true
	);

	await page.locator('body').press('Escape');
	await expect(page.locator('#chat-container')).toContainText('MCP: News Headline');
	response = await sendChatMessage(
		page,
		'What are the current headlines?',
		'Consulting CrewAI agents...'
	);
	await expect(response).not.toContain('No recent articles found matching your criteria.');

	await page.close();
});
