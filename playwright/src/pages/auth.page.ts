import { BasePage, type Language } from './base.page';
import { type Page, type Locator, expect } from '@playwright/test';

export class AuthPage extends BasePage {
	readonly emailInput: Locator;
	readonly passwordInput: Locator;
	readonly signInButton: Locator;
	readonly createAccountButton: Locator;
	readonly nameInput: Locator;
	readonly onboardingButton: Locator;
	readonly isFirstRunButton: Locator;

	constructor(page: Page, lang: Language = 'en-GB') {
		super(page, lang);

		this.emailInput = page.getByRole('textbox', {
			name: this.t['Enter Your Email'] || 'Enter Your Email'
		});
		this.passwordInput = page.getByRole('textbox', {
			name: this.t['Enter Your Password'] || 'Enter Your Password'
		});
		this.signInButton = page.getByRole('button', { name: this.t['Sign in'] || 'Sign in' });
		this.createAccountButton = page.getByRole('button', {
			name: this.t['Create Admin Account'] || 'Create Admin Account'
		});
		this.nameInput = page.getByRole('textbox', {
			name: this.t['Enter Your Full Name'] || 'Enter Your Full Name'
		});
		this.onboardingButton = page.getByRole('button', {
			name: this.t["Okay, Let's Go!"] || "Okay, Let's Go!"
		});

		this.isFirstRunButton = page.getByRole('button').filter({ hasText: /^$/ });
	}

	/**
	 * Perform the user login
	 * @param email The email address of the user.
	 * @param pass The password for the account.
	 */
	async login(email: string, pass: string) {
		await this.goto('/auth');
		await this.emailInput.fill(email);
		await this.passwordInput.fill(pass);
		await this.signInButton.click();

		await this.page.waitForURL('/');
		await expect(this.page.locator('body')).toBeVisible();

		// Handle "Ok, Let's Go!" onboarding popup
		if (await this.onboardingButton.isVisible({ timeout: 2000 })) {
			await this.onboardingButton.click();
		}
	}

	/**
	 * Registers a new Admin account (first run only)
	 * @param name The name of the admin.
	 * @param email The email address of the admin.
	 * @param pass The password for the account.
	 */
	async registerAdmin(name: string, email: string, pass: string) {
		await this.nameInput.fill(name);
		await this.emailInput.fill(email);
		await this.passwordInput.fill(pass);
		await this.createAccountButton.click();

		// Handle "Ok, Let's Go!" onboarding popup
		await this.onboardingButton.waitFor();
		await this.onboardingButton.click();
	}
}
