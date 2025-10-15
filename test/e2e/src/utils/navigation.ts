import { Page, Locator, expect } from '@playwright/test';

export async function showSidebar(page: Page) {

    const toggleButton = '#sidebar-toggle-button';
    const hideButton = '#hide-sidebar-button';

    const visibleButton = await Promise.race([
        page.waitForSelector(toggleButton, { state: 'visible' }).then(() => toggleButton),
        page.waitForSelector(hideButton, { state: 'visible' }).then(() => hideButton)
    ]);

    if (visibleButton === toggleButton) {
        console.log('Toggling sidebar.');
        await page.click(toggleButton);
    }

}

export async function showAdminSettings(page: Page) {
    await page.getByRole('button', { name: 'User profile' }).click();
    await page.getByRole('menuitem', { name: 'Admin Panel' }).click();
    await page.getByRole('link', { name: 'Settings' }).click();
    page.waitForLoadState('networkidle');
}

export async function sendChatMessage(page: Page, message: string, idleMessage: string = ''): Promise<string> {

    await page.locator('#chat-input').fill(message);
    await page.getByRole('button', { name: 'Send message' }).click();

    const selector = '#response-content-container';

    // Wait for the response to be populated
    await page.waitForSelector(selector, { state: 'visible' });

    await page.waitForFunction(
        ({ selector, idleMessage }) => {
            const el = document.querySelector(selector);
            if (!el) return false;
            const text = el.textContent?.trim() || '';
            return !text.includes(idleMessage) && text.length > 0;
        },
        { selector, idleMessage }
    );

    await page.waitForLoadState('networkidle');

    return (await page.locator(selector).textContent()) ?? '';
}

export async function toggleSwitch(locator: Locator, checked: boolean = true) {

    await locator.waitFor({ state: 'visible' });
    await expect(locator).toHaveAttribute('data-state', /^(checked|unchecked)$/);

    // Await the promise before comparing
    const currentState = await locator.getAttribute('data-state');
    if ((currentState === 'checked') !== checked) {
        await locator.click();
    }
}

