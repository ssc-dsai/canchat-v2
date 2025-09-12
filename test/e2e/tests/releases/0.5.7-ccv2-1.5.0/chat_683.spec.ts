import { test, expect } from '@playwright/test';
import { env } from 'process';

test('chat_683, PR#148 -- feat(mcp): FastMCP with CrewAI integration', async ({ page }, testInfo) => {
  await page.goto('/');
  await page.getByLabel('More').click();

  await expect(page.getByRole('button', { name: 'MCP: Current Time' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'MCP: News Headlines' })).toBeVisible();
  await page.getByRole('button', { name: 'MCP: Current Time' }).click();
  await page.getByRole('button', { name: 'MCP: News Headlines' }).click();
  await page.locator('body').press('Escape');
  await expect(page.locator('#chat-container')).toContainText('MCP: Current Time , MCP: News Headlines');

  if (testInfo.project.name.includes('admin')) {
    await page.getByRole('button', { name: 'User profile' }).click();
    await page.getByRole('menuitem', { name: 'Admin Panel' }).click();
    await page.getByRole('link', { name: 'Settings' }).click();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: 'MCP' }).click();
    await expect(page.locator('form')).toContainText('Time Server');
    await expect(page.locator('form')).toContainText('News Server');
    await expect(page.getByText('get_current_time')).toBeVisible();
    await expect(page.getByText('get_top_headlines')).toBeVisible();
    await expect(page.locator('form')).toMatchAriaSnapshot(`- text: MCP Servers 2`);
  }
});
