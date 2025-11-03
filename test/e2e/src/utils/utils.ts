import { Page } from '@playwright/test';
import path from 'path';

const testPath = process.env.BASE_PATH || '/app/test/e2e';

interface StorageFile {
    cookies?: any[];
    origins?: { origin: string; localStorage?: { name: string; value: string }[] }[];
}

/**
 * Load and applies cookies + origins from a specific storage state JSON file.
 *
 * @param page Current Playwright Page
 * @param username The user profile name
 *
 * Example:
 * await setUser(context, page, 'user');
 */
export async function setUserContext(page: Page, username: string): Promise<Page> {
    // Get only the username portion of the project name
    if (username.split('-').length > 1) {
        username = username.split('-')[1];
    }
    const context = page.context();
    const browser = context.browser();
    if (!browser) {
        throw new Error('Browser is not available from this context');
    }



    const authPath = path.join(testPath, `./playwright/.auth/${username}.json`);

    const newContext = await browser.newContext({ storageState: authPath });

    const newPage = await newContext.newPage();
    return newPage;
}
