import { test, expect } from '../../../src/fixtures/base-fixture';

test.describe('Feature: Wiki Grounding', () => {
	test('Service Availability', async ({ userPage }, testInfo) => {
		const timeout = parseInt(process.env.LONG_TIMEOUT as string) || 120_000;
		test.setTimeout(timeout);

		await userPage.goto('/');
		await userPage.toggleChatTool('Wiki Grounding', true);
		await expect(userPage.page.locator('#chat-container')).toContainText('Wiki Grounding', {
			timeout: 15000
		});

		await userPage.sendMessage('Who is the current Canadian Prime Minister?');
		await expect(userPage.responseMessages.last()).toContainText('Carney', { timeout: 60000 });
		const responseText = await userPage.getLastMessageText();

		await testInfo.attach('Results', {
			body: `Chat response: ${responseText}`,
			contentType: 'text/plain'
		});
	});
});
