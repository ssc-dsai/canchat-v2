import { test, expect } from '@playwright/test';
import { setUserContext } from '../../../src/utils/utils';
import { showSidebar, showAdminSettings, toggleSwitch, sendChatMessage } from '../../../src/utils/navigation';

test('chat_683, PR#148 -- feat(mcp): FastMCP with CrewAI integration', async ({ page }, testInfo) => {


  // #1 - Enable MCP plugins in admin settings
  // Set to admin user
  page = await setUserContext(page, 'admin');

  await page.goto('/');
  await showSidebar(page);

  await showAdminSettings(page);
  await page.getByRole('button', { name: 'MCP' }).click();

  await toggleSwitch(page.getByRole('switch', { name: 'Enable MCP API' }), true);

  // Check if both services are running
  const time = await page.locator("//div[normalize-space(text())='Time Server']/../../..//span[normalize-space(text())='running']").count();
  const news = await page.locator("//div[normalize-space(text())='News Server']/../../..//span[normalize-space(text())='running']").count();
  await expect(time).toBeGreaterThan(0);
  await expect(news).toBeGreaterThan(0);

  // #2 - Test MCP plugins in chat
  // Set to test user
  page = await setUserContext(page, testInfo.project.name);
  await page.goto('/');

  await page.getByLabel('More').click();
  await toggleSwitch(page.getByRole('button', { name: 'MCP: Current Time' }).getByRole('switch'), true);
  // await toggleSwitch(
  //   page.getByRole('button', { name: 'MCP: Current Time' }).getByRole('switch'),
  //   true
  // );
  await page.locator('body').press('Escape');
  await expect(page.locator('#chat-container')).toContainText('MCP: Current Time');
  var response = await sendChatMessage(page, 'What is the time?', 'Consulting CrewAI agents...');
  await expect(response).toContain('time');

  await page.getByRole('link', { name: 'logo New Chat' }).click();
  await page.getByLabel('More').click();

  await toggleSwitch(page.getByRole('button', { name: 'MCP: News Headlines' }).getByRole('switch'), true);
  // await toggleSwitch(
  //   page.getByRole('button', { name: 'MCP: News Headlines' }).getByRole('switch'),
  //   true
  // );
  await page.locator('body').press('Escape');
  await expect(page.locator('#chat-container')).toContainText('MCP: News Headline');
  response = await sendChatMessage(page, 'What are the current headlines?', 'Consulting CrewAI agents...');
  await expect(response).not.toContain('No recent articles found matching your criteria.');

  // #3 - Disable MCP plugins in admin settings
  // Set to admin user
  page = await setUserContext(page, 'admin');
  await page.goto('/');
  await showAdminSettings(page);


  await page.getByRole('paragraph').filter({ hasText: /^$/ }).click();
  await page.locator('#chat-input').fill('Write 20 paragraphs of your chosing');
  await page.goto('http://localhost:8080/c/328facac-1154-4f45-bdaa-6f71f44e2bfa');
  await expect(page.getByText('1. The forest stood silent at')).toBeVisible();
  await expect(page.locator('#response-content-container')).toContainText('1. The forest stood silent at dawn, shrouded in mist that curled around tree trunks like the fingers of a ghost. Muffled birdsong echoed through the towering canopy as light trickled through the interwoven branches above. It was a cathedral of nature, and the air hummed with the scent of pine and damp earth. In that moment, life seemed still, eternal, and deeply mysterious.');
  await page.getByRole('link', { name: 'logo New Chat' }).click();
  await page.getByLabel('More').click();
  await page.getByRole('button', { name: 'MCP: News Headlines' }).getByRole('switch').click();
  await page.getByRole('button', { name: 'MCP: Current Time' }).getByRole('switch').click();
  await page.getByRole('paragraph').filter({ hasText: /^$/ }).click();
  await page.locator('#chat-input').fill('What are the current headlines?');
  await page.goto('http://localhost:8080/c/93739420-52bc-4453-8397-deab549f4f80');
  await expect(page.locator('#response-content-container')).toContainText('Consulting CrewAI agents...');

});
