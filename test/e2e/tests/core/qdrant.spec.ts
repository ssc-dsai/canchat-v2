import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { sendChatMessage } from '../../src/utils/navigation';


test('Test - Qdrant Availability', async ({ page }, testInfo) => {
  test.setTimeout(180000); // Set timeout to 3 minutes
  await page.goto('/');

  // Define the test file path
  const filePath = './resources/text/pg11.txt';


  const fileChooserPromise = page.waitForEvent('filechooser');
  await page.getByLabel('More').click();
  await page.getByText('Upload Files').click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles(filePath);

  // Wait for locator "li" to contain text "File uploaded successfully" to appear
  await page.locator('li').filter({ hasText: 'File uploaded successfully' }).waitFor({ state: 'visible', timeout: 180000 });
  await page.locator('li', { hasText: 'File uploaded successfully' }).waitFor({
    state: 'detached',
    timeout: 30000
  });

  const response = await sendChatMessage(page, 'Summarize the uploaded document.');
  console.log(`RAG response: ${response}`);
  await expect(response).toContain('Gutenberg');

  await test.info().attach('Results', {
    body: `Chat response: ${response}`,
    contentType: 'text/plain'
  });

  await page.close();
});
