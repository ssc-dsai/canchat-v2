// Checks that the version displays that from the current directory name

import { test, expect } from '@playwright/test';
import { env } from 'process';


test('version_check', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('admin'), 'Only admin profile check required');
  await page.goto('/');
  await page.getByRole('button', { name: 'User profile' }).click();
  await page.getByRole('menuitem', { name: 'Settings' }).click();
  await page.getByRole('button', { name: 'About' }).click();
  const dirPath = __dirname;
  const subdirs = require('fs').readdirSync(dirPath).filter(f => require('fs').statSync(require('path').join(dirPath, f)).isDirectory());
  const lastSubdir = subdirs.sort().pop() ?? '';
  await expect(page.locator('body')).toContainText(lastSubdir, { timeout: 1000 });
});