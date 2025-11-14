import { test, expect } from '@playwright/test';
import { showSidebar, showStartPage, setLanguage } from '../../../src/utils/navigation';
import { text } from 'stream/consumers';

test('PR#264 -- enh: revised prompt warning text', async ({ page }, testInfo) => {
	await showStartPage(page);
	await setLanguage(page, 'en');

	await expect(page.getByLabel('Disclaimer')).toContainText('All records are transitory.');
	await setLanguage(page, 'fr');

	await expect(page.getByLabel('Disclaimer')).toContainText('Tous les enregistrements sont');
});
