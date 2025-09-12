import { test, expect } from '@playwright/test';
import { env } from 'process';

test('chat_747, PR#152 -- fix(metrics): Enhance model metrics access and display for analysts', async ({ page }) => {
  await page.goto('/'); 

});