import { test as setup, expect, Page } from '@playwright/test';
import path from 'path';
import { showAdminSettings, showPage, waitToSettle } from '../src/utils/navigation';
const fs = require('fs');

const data = fs.readFileSync(path.join(__dirname, 'creds.json'));
const credentials = JSON.parse(data);
const adminUser = credentials.users.find(u => u.username === 'admin');

async function populateAccounts({ page }: { page: Page }) {
  // Remove all files in ../playwright/.auth
  const authDir = path.join(__dirname, '../playwright/.auth');
  if (fs.existsSync(authDir)) {
    for (const file of fs.readdirSync(authDir)) {
      fs.unlinkSync(path.join(authDir, file));
    }
  }

  await showPage(page, '/auth');

  // First login
  await page.getByRole('button').filter({ hasText: /^$/ }).click();
  await page.getByRole('textbox', { name: 'Enter Your Full Name' }).fill(adminUser.username);
  await page.getByRole('textbox', { name: 'Enter Your Email' }).fill(adminUser.email);
  await page.getByRole('textbox', { name: 'Enter Your Password' }).fill(adminUser.password);
  await page.getByRole('button', { name: 'Create Admin Account' }).click();

  await waitToSettle(page);
  await page.getByRole('button', { name: 'Okay, Let\'s Go!' }).click();

  await showAdminSettings(page,'Users & Access', 'Overview');

  for (const user of credentials.users) {
    if (user.username != 'admin') {
      await page.locator('[id="add-user\\9 \\9 \\9 \\9 "]').click();
      await page.getByRole('combobox').selectOption(user.name);
      await page.getByRole('textbox', { name: 'Enter Your Full Name' }).fill(user.name);
      await page.getByRole('textbox', { name: 'Enter Your Email' }).fill(user.email);
      await page.getByRole('textbox', { name: 'Enter Your Password' }).fill(user.password);
      await page.getByRole('button', { name: 'Save' }).click();
    }
  }

  await showAdminSettings(page,'Settings', 'Models');
  await page.getByRole('button', { name: 'modelfile profile chatgpt-4o-' }).click();
  await page.locator("//div[@contenteditable='true'][@data-placeholder='Enter English description']").fill('chatgpt');
  await page.locator("//div[@contenteditable='true'][@data-placeholder='Enter French description']").fill('chatgpt');
  await page.locator('#models').selectOption('public');
  await page.getByRole('button', { name: 'Save & Update' }).click();

  await page.getByRole('button', { name: 'User profile' }).click();
  await page.getByText('Sign Out').click();
}


setup('authenticate', async ({ page }) => {
  // If it's the first login, run setup('populateAccounts')
  await showPage(page, '/auth');

  try {
    await page.getByRole('button').filter({ hasText: /^$/ }).first().waitFor({ state: 'visible', timeout: 1000 });
    await populateAccounts({ page });
  } catch { }

  

  for (const user of credentials.users) {
    // If path.join(__dirname, `../playwright/.auth/${user.username}.json`) already exists, skip login
    const authFile = path.join(__dirname, `../playwright/.auth/${user.username}.json`);
    if (fs.existsSync(authFile)) {
      console.log(`Skipping login for ${user.username}, already authenticated.`);
      continue;
    }

    await page.waitForTimeout(500);
    await page.goto('/auth');
    await page.getByRole('textbox', { name: 'Enter Your Email' }).fill(user.email);
    await page.getByRole('textbox', { name: 'Enter Your Password' }).fill(user.password);
    await page.getByRole('button', { name: 'Sign in' }).click();
    // Wait until the page receives the cookies.
    //
    // Sometimes login flow sets cookies in the process of several redirects.
    // Wait for the final URL to ensure that the cookies are actually set.
    await page.waitForURL('/');
    //await expect(page.getByRole('heading', { name: /^Hello,/ })).toBeVisible();

    const okButton = page.getByRole('button').filter({ hasText: 'Okay, Let\'s Go!' }).first();
    if (await okButton.isVisible({ timeout: 1000 }))
      await okButton.click();

    await page.context().storageState({ path: authFile });

    await page.getByRole('button', { name: 'User profile' }).click();

    await page.getByText('Sign Out').isVisible();
    await page.getByText('Sign Out').click();
  }

  await page.close();

});
