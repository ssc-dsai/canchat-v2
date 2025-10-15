import { test, expect } from '@playwright/test';
import { showSidebar } from '../../../src/utils/navigation';

test('PR#232 -- feat(metrics): implement export functionality for metrics data and logs', async ({ page }, testInfo) => {

    await page.goto('/');
    await showSidebar(page);


    await page.getByRole('link', { name: 'Workspace' }).click();
    if (!testInfo.project.name.includes('user')) {
        await expect(page.getByRole('link', { name: 'Metrics' })).toBeVisible();
        console.log(`Metrics link visible for ${testInfo.project.name}.`);

        await page.getByRole('link', { name: 'Metrics' }).click();
        await expect(page.getByRole('link', { name: 'Metrics' })).toBeVisible();
        await page.getByLabel('Date Range').selectOption('custom');
        const today = new Date().toISOString().slice(0, 10);
        await page.getByRole('textbox', { name: 'Start Date' }).fill(today);
        await page.getByRole('textbox', { name: 'End Date' }).fill(today);

        page.once('dialog', dialog => {
            console.log(`Dialog message: ${dialog.message()}`);
            dialog.dismiss().catch(() => { });
        });
        await page.getByRole('button', { name: 'Export Raw Data' }).click();

        const downloadPromise = page.waitForEvent('download');
        // await page.getByText('Download file').click();
        // const download = await downloadPromise;
        // page.on('download', download => download.path().then(console.log));
    } else {
        await expect(page.getByRole('link', { name: 'Metrics' })).not.toBeVisible();
        console.count('Metrics link not visible for user.');
    }
});
