import { test, expect } from '@playwright/test';
import {
	showAdminSettings,
	waitToSettle,
	toggleSwitch,
	sendChatMessage,
	showStartPage,
	showSidebar
} from '../../src/utils/navigation';
import { describeLocalImage } from '../../src/utils/openai';

test('Test - Image Generation Availability', async ({ page }, testInfo) => {
	const timeout = parseInt(process.env.LONG_TIMEOUT as string) || 120000;
	test.setTimeout(timeout); // Set timeout to LONG_TIMEOUT

	await showStartPage(page);
	await showAdminSettings(page, 'Settings', 'Images');

	await toggleSwitch(page.getByRole('switch').first(), true);
	await page.getByRole('combobox', { name: 'Select a model' }).fill('dall-e-2');
	await page.getByRole('button', { name: 'Save' }).click();

	await showStartPage(page);
	await page.getByLabel('More').click();

	await toggleSwitch(page.getByRole('button', { name: 'Image' }).getByRole('switch'), true);

	await page.locator('body').press('Escape');
	await showSidebar(page, 'hide');

	await expect(page.locator('#chat-container')).toContainText('Image generation');
	const response = await sendChatMessage(
		page,
		'Make a picture of the Easter Bunny.',
		'Generating an image'
	);
	await waitToSettle(page, 1000);

	const screenshot = await page.screenshot({
		path: './playwright-report/screenshots/image_gen.png'
	});

	const responseOpenAi = await describeLocalImage('./playwright-report/screenshots/image_gen.png');
	await expect(responseOpenAi).not.toContain('error');

	await test.info().attach('Results', {
		body: `Image description: ${responseOpenAi}`,
		contentType: 'text/plain'
	});

	await test.info().attach('Screenshot', {
		body: screenshot,
		contentType: 'image/png'
	});

	await page.close();
});
