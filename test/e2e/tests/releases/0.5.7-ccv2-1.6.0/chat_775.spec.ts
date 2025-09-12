import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';


test('chat_775, PR#183 -- feat(qdrant): Add comprehensive cleanup scripts for Qdrant vector database', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('admin'), 'Skipping test for non-admin projects');

  test.setTimeout(30000); // Set timeout to 5 minutes
  await page.goto('/');

  // Define the directory path
  const directoryPath = './resources/text';

  // Read all files in the directory
  const fileNames = fs.readdirSync(directoryPath);

  // Construct absolute paths for each file
  const absoluteFilePaths = fileNames.map(fileName => path.join(directoryPath, fileName));

  // await page.getByLabel('More').click();
  // const fileChooserPromise = page.waitForEvent('filechooser');
  // await page.getByText('Upload Files').click();
  // const fileChooser = await fileChooserPromise;
  // await fileChooser.setFiles(absoluteFilePaths);

  // Loop through each file and upload it one at a time
  for (const filePath of absoluteFilePaths) {
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.getByLabel('More').click();
    await page.getByText('Upload Files').click();
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);
    // Wait for locator "li" to contain text "File uploaded successfully" to appear
    await page.locator('li').filter({ hasText: 'File uploaded successfully' }).waitFor({ state: 'hidden', timeout: 10000 });
    await page.locator('li').filter({ hasText: 'File uploaded successfully' }).waitFor({ state: 'visible', timeout: 270000 });
  }
});
