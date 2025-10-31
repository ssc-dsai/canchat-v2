import { test, expect } from '@playwright/test';
import { showSidebar, waitToSettle } from '../../../src/utils/navigation';

test('PR#248 -- fix(admin-settings/interface/banners): ensure the correct language is displayed on first render', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('admin'), 'Only admin profile check required');
  try {
    await page.goto('/');
    await showSidebar(page);

    await page.getByRole('button', { name: 'User profile' }).click();
    await page.getByRole('menuitem', { name: 'Admin Panel' }).click();
    await page.getByRole('link', { name: 'Settings' }).click();
    await page.getByRole('button', { name: 'Interface' }).click();
    await page.locator('.p-1').first().click();
    await page.locator('.p-1').first().click();
    await page.locator('.w-fit.rounded-xl').first().selectOption('success');

    await waitToSettle(page);
    await page.locator('.flex > select:nth-child(2)').selectOption('en-GB');
    await page.getByRole('textbox', { name: 'Content' }).fill('English');
    await page.locator('.p-1').first().click();
    await page.locator('div:nth-child(2) > .flex.flex-row > select').first().selectOption('success');
    
    await waitToSettle(page);
    await page.locator('div:nth-child(2) > .flex.flex-row > select:nth-child(2)').selectOption('fr-CA');
    await page.getByRole('textbox', { name: 'Content' }).nth(1).fill('francais');

    await page.getByRole('button', { name: 'Save' }).click();

    await page.waitForTimeout(500);

    await page.goto('/');

    await showSidebar(page);
    await page.getByRole('link', { name: 'logo New Chat' }).click();
    await page.locator('#chat-input').press('ControlOrMeta+F5');
    await expect(page.locator('body')).toContainText('FR');
    await expect(page.locator('#chat-container')).toContainText('English');
    await page.getByRole('button', { name: 'FR', exact: true }).click();
    await expect(page.locator('body')).toContainText('EN');
    await expect(page.locator('#chat-container')).toContainText('francais');
    await page.getByRole('button', { name: 'EN', exact: true }).click();
  }
  finally {
    // Cleanup - remove the banners
    await page.getByRole('button', { name: 'User profile' }).click();
    await page.getByRole('menuitem', { name: 'Admin Panel' }).click();
    await page.getByRole('link', { name: 'Settings' }).click();
    await page.getByRole('button', { name: 'Interface' }).click();
    await page.locator('.flex.flex-col.space-y-1 > div > .px-2').first().click();
    await page.locator('.flex.flex-col.space-y-1 > div > .px-2').first().click();
    await page.getByRole('button', { name: 'Save' }).click();
    await page.getByRole('link', { name: 'logo New Chat' }).click();
  }
});
