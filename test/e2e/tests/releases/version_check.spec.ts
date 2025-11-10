// Checks the version displays correctly

import fs from 'fs';
import path from 'path';
import { test, expect } from '@playwright/test';

test('version_check', async ({ page }, testInfo) => {
	test.skip(!testInfo.project.name.includes('admin'), 'Only admin profile check required');

	// Navigate to About page
	await page.goto('/');
	await page.getByRole('button', { name: 'User profile' }).click();
	await page.getByRole('menuitem', { name: 'Settings' }).click();
	await page.getByRole('button', { name: 'About' }).click();

	// Read version.json file
	const versionFilePath = path.join(__dirname, 'version.json');
	if (!fs.existsSync(versionFilePath)) {
		throw new Error(`version.json not found at ${versionFilePath}`);
	}

	const versionData = JSON.parse(fs.readFileSync(versionFilePath, 'utf-8'));
	const version = versionData.version ?? versionData?.appVersion ?? '';

	if (!version) {
		throw new Error(`No valid version found in version.json`);
	}

	console.log('Expecting version to contain:', version);

	// Assert that the version text appears on the About page
	await expect(page.locator('body')).toContainText(version, { timeout: 1000 });

	// Get the full page body text and extract only the version substring matching:
	// pattern 0.5.7-ccv2-x.x.x where x are one or more digits (allow multiple digits per segment)
	const pageText = (await page.locator('body').textContent()) ?? '';
	const versionRegex = /0\.5\.7-ccv2-\d+\.\d+\.\d+/;
	const match = pageText.match(versionRegex);

	if (!match) {
		throw new Error(`No version matching regex ${versionRegex} found in page body`);
	}

	const matchedVersion = match[0];
	console.log('Version detected:', matchedVersion);

	await test.info().attach('Version', {
		body: `Version detected: ${matchedVersion}`,
		contentType: 'text/plain'
	});

	page.close();
});
