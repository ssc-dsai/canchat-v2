import { BasePage, type Language } from './base.page';
import { type Page, type Locator, expect } from '@playwright/test';

export class ChatPage extends BasePage {
	readonly messageInput: Locator;
	sendButton!: Locator;
	stopGenerationButton!: Locator;
	readonly regenerateButton: Locator;
	readonly responseMessages: Locator;
	readonly responseMessageGenerating: Locator;
	readonly responseSelector = '#response-content-container';
	chatStatusDescription!: Locator;

	constructor(page: Page, lang: Language = 'en-GB') {
		super(page, lang);

		this.messageInput = page.locator('#chat-input');
		this.regenerateButton = page.locator('div:nth-child(8) > .visible');
		this.responseMessages = page.locator('#response-content-container');
		this.responseMessageGenerating = page.locator('.space-y-2');
		this.responseSelector = '#response-content-container';
		this.chatStatusDescription = page.locator('.status-description');

		this.updateLanguage(lang);
	}

	/**
	 * Override to update Chat-specific locators
	 * @param lang The new language to switch to ('en-GB' or 'fr-CA')
	 */
	override updateLanguage(lang: Language) {
		super.updateLanguage(lang);

		this.sendButton = this.page.getByRole('button', {
			name: this.t['Send message'] || 'Send message'
		});
		this.stopGenerationButton = this.page.locator('button.bg-white.hover\\:bg-gray-100');
	}

	/**
	 * Starts a new chat session
	 */
	async newChat() {
		await this.toggleSidebar(true);
		await this.sidebarNewChatButton.click();
		await expect(this.messageInput).toBeVisible();
	}

	/**
	 * Sends a message and waits for the response generation
	 */
	async sendMessage(text: string, waitForReply: boolean = true, idleMessage: string = '') {
		await expect(this.messageInput).toBeVisible();

		await this.messageInput.fill(text);
		await expect(this.sendButton).toBeEnabled();
		await this.sendButton.click();

		if (waitForReply) {
			await this.waitForGeneration(idleMessage);
		}
	}

	/**
	 * Waits for the response to complete
	 */
	async waitForGeneration(idleMessage: string = '') {
		const selector = this.responseSelector;
		await this.page.waitForSelector(selector, { state: 'visible' });

		await this.page.waitForFunction(
			({ selector, idleMessage }) => {
				const el = document.querySelector(selector);
				if (!el) return false;
				const text = el.textContent?.trim() || '';
				return text.length > 0 && (idleMessage.length === 0 || !text.includes(idleMessage));
			},
			{ selector, idleMessage },
			{ timeout: 180000 }
		);

		await this.waitToSettle(1500);
	}

	/**
	 * Retrieves the chat status description displayed above the answer
	 * Example is wiki grounding "Enhanced with 5 ressources"
	 */
	async getChatStatusDescription(status: string) {
		await expect(this.chatStatusDescription).toContainText(status, { timeout: 60000 });
	}

	/**
	 * Retrieves the text content of the most recent chat bubble
	 */
	async getLastMessageText(): Promise<string> {
		await expect(this.responseMessages.last()).toBeVisible();
		await expect(this.responseMessageGenerating).not.toBeVisible();
		return await this.responseMessages.last().innerText();
	}

	/**
	 * Triggers regeneration of the last AI response
	 */
	async regenerateLastResponse() {
		await this.regenerateButton.click();
		await this.waitForGeneration();
	}

	/**
	 * Checks if the "Network Problem" error is visible
	 */
	async isNetworkErrorPresent(): Promise<boolean> {
		return await this.responseMessages.getByText('Network Problem').isVisible();
	}

	/**
	 * Opens the 'More' menu and toggles a specific tool/capability
	 * @param toolName The name of the button in the menu
	 * @param enable Desired state (true/false)
	 */
	async toggleChatTool(toolName: string, enable: boolean) {
		await this.page.getByLabel('More').click();
		const toolButton = this.page.getByRole('menuitem', { name: toolName });
		const toolSwitch = toolButton.getByRole('switch');

		await expect(toolButton).toBeVisible();

		const isChecked = await toolSwitch.isChecked();
		if (isChecked !== enable) {
			await toolSwitch.click();
			await expect(toolSwitch).toBeChecked({ checked: enable });
		}

		await this.page.keyboard.press('Escape');
	}

	/**
	 * Uploads a file via the 'More' menu
	 * @param filePath Path to the file
	 */
	async uploadFile(filePath: string) {
		const fileChooserPromise = this.page.waitForEvent('filechooser');

		await this.page.getByLabel('More').click();
		await this.page.getByText(this.getTranslation('Upload Files')).click();

		const fileChooser = await fileChooserPromise;
		await fileChooser.setFiles(filePath);

		await this.page
			.locator('li')
			.filter({ hasText: this.getTranslation('File uploaded successfully') })
			.waitFor({ state: 'visible', timeout: 180000 });
		await this.page
			.locator('li', { hasText: this.getTranslation('File uploaded successfully') })
			.waitFor({
				state: 'detached',
				timeout: 30000
			});
	}

	/**
	 * Returns the locator for the last generated image in the chat
	 */
	getLastImage() {
		return this.page.locator('[data-cy="image"]').last();
	}

	/**
	 * Copies the last user message and verifies toast
	 */
	async copyLastUserMessage() {
		const lastUserMessage = this.page.locator('.user-message').last();
		await lastUserMessage.scrollIntoViewIfNeeded();
		await lastUserMessage.hover();
		await lastUserMessage.locator('.chat-user').hover();
		const copyLabel = this.getTranslation('Copy');
		const copyBtn = lastUserMessage.locator(`button[aria-label="${copyLabel}"]`).first();
		await copyBtn.waitFor({ state: 'attached' });
		await copyBtn.click({ force: true });
	}

	/**
	 * Pastes content from the clipboard into the message input field.
	 */
	async pasteToMessageInput() {
		await this.messageInput.focus();
		const modifier = process.platform === 'darwin' ? 'Meta' : 'Control';
		await this.page.keyboard.press(`${modifier}+V`);
		await this.page.waitForTimeout(200);
	}

	/**
	 * Returns the current value of the message input field.
	 */
	async getMessageInputValue(): Promise<string> {
		return (await this.messageInput.innerText()).trim();
	}

	/**
	 * Waits for autocomplete suggestion to appear
	 */
	async waitForAutocomplete(): Promise<void> {
		await this.page.locator('.autocomplete-suggestion, [data-testid="autocomplete"]').waitFor({
			state: 'visible',
			timeout: 10000
		});
	}

	/**
	 * Accepts autocomplete by pressing Tab
	 */
	async acceptAutocomplete(): Promise<void> {
		await this.page.keyboard.press('Tab');
		await this.waitToSettle(500);
	}

	/**
	 * Opens edit mode for the last user message
	 */
	async editLastUserMessage(): Promise<void> {
		const lastUserMessage = this.page.locator('.user-message').last();
		await lastUserMessage.scrollIntoViewIfNeeded();
		await lastUserMessage.hover();

		const editLabel = this.getTranslation('Edit');
		const editBtn = lastUserMessage.locator(`button[aria-label="${editLabel}"]`).first();
		await editBtn.waitFor({ state: 'attached' });
		await editBtn.click({ force: true });
		await this.page
			.locator('textarea, [contenteditable="true"]')
			.last()
			.waitFor({ state: 'visible' });
	}

	/**
	 * Types new content in the edit textarea
	 */
	async typeEditContent(text: string): Promise<void> {
		const editTextarea = this.page
			.locator('.user-message textarea, .user-message [contenteditable="true"]')
			.last();
		await editTextarea.fill(text);
	}

	/**
	 * Saves the edited message without regenerating
	 */
	async saveMessageEdit(): Promise<void> {
		const saveLabel = this.getTranslation('Save');
		await this.page.getByRole('button', { name: saveLabel, exact: true }).click();
		await this.waitToSettle(500);
	}

	/**
	 * Cancels message editing
	 */
	async cancelMessageEdit(): Promise<void> {
		const cancelLabel = this.getTranslation('Cancel');
		await this.page.getByRole('button', { name: cancelLabel }).click();
		await this.waitToSettle(300);
	}

	/**
	 * Sends edited message (triggers regeneration)
	 */
	async sendEditedMessage(): Promise<void> {
		const sendLabel = this.getTranslation('Send');
		await this.page.getByRole('button', { name: sendLabel, exact: true }).click();
		await this.waitForGeneration();
	}

	/**
	 * Gets the text of the last user message
	 */
	async getLastUserMessageText(): Promise<string> {
		const lastUserMessage = this.page.locator('.user-message .chat-user').last();
		return (await lastUserMessage.innerText()).trim();
	}

	/**
	 * Copies the last AI answer and verifies toast
	 */
	async copyLastAnswer(): Promise<void> {
		const lastResponse = this.page.locator('#response-content-container').last();
		await lastResponse.scrollIntoViewIfNeeded();
		await lastResponse.hover();
		const copyBtn = this.page.locator('.copy-response-button').last();
		await copyBtn.waitFor({ state: 'visible', timeout: 10000 });
		await copyBtn.click({ force: true });
	}

	/**
	 * Prepares to interact with answer buttons by scrolling and hovering
	 */
	private async prepareAnswerButtonInteraction(): Promise<void> {
		const lastResponse = this.page.locator('#response-content-container').last();
		await lastResponse.scrollIntoViewIfNeeded();
		await lastResponse.hover();
	}

	/**
	 * Clicks an answer action button by aria-label
	 */
	private async clickAnswerButton(ariaLabel: string): Promise<void> {
		await this.prepareAnswerButtonInteraction();
		const btn = this.page.locator(`button[aria-label="${ariaLabel}"]`).last();
		await btn.waitFor({ state: 'visible', timeout: 10000 });
		await btn.click({ force: true });
	}

	/**
	 * Opens edit mode for the last AI answer
	 */
	async editLastAnswer(): Promise<void> {
		const editLabel = this.getTranslation('Edit');
		await this.clickAnswerButton(editLabel);
		await this.page
			.locator('textarea, [contenteditable="true"]')
			.last()
			.waitFor({ state: 'visible' });
	}

	/**
	 * Types new content in the answer edit textarea
	 */
	async typeAnswerEditContent(text: string): Promise<void> {
		const editTextarea = this.page.locator('textarea[id^="message-edit-"]').last();
		await editTextarea.fill(text);
	}

	/**
	 * Saves the edited answer as a new copy
	 */
	async saveAnswerAsCopy(): Promise<void> {
		//const label = this.getTranslation('Save as Copy'); //Bug CHAT-1439
		const label = 'Save as Copy';
		await this.page.getByRole('button', { name: label }).click();
		await this.waitToSettle(500);
	}

	/**
	 * Saves the edited answer (replaces current)
	 */
	async saveAnswerEdit(): Promise<void> {
		const saveLabel = this.getTranslation('Save');
		await this.page.getByRole('button', { name: saveLabel, exact: true }).click();
		await this.waitToSettle(500);
	}

	/**
	 * Cancels answer editing
	 */
	async cancelAnswerEdit(): Promise<void> {
		const cancelLabel = this.getTranslation('Cancel');
		await this.page.getByRole('button', { name: cancelLabel }).click();
		await this.waitToSettle(300);
	}

	/**
	 * Navigates to previous answer version
	 */
	async goToPreviousAnswer(): Promise<void> {
		const label = this.getTranslation('Previous Response');
		const btn = this.page.locator(`button[aria-label="${label}"]`).last();
		if (await btn.isVisible()) {
			await btn.click();
		} else {
			await this.page.locator('div.flex.self-center.min-w-fit button').first().click();
		}
		await this.waitToSettle(500);
	}

	/**
	 * Navigates to next answer version
	 */
	async goToNextAnswer(): Promise<void> {
		const label = this.getTranslation('Next Response');
		const btn = this.page.locator(`button[aria-label="${label}"]`).last();
		if (await btn.isVisible()) {
			await btn.click();
		} else {
			await this.page.locator('div.flex.self-center.min-w-fit button').last().click();
		}
		await this.waitToSettle(500);
	}

	/**
	 * Toggles read aloud for the last answer
	 * @returns true if reading started, false if stopped
	 */
	async toggleReadAloud(): Promise<boolean> {
		const readLabel = this.getTranslation('Read Aloud');
		const stopLabel = this.getTranslation('Stop');

		await this.prepareAnswerButtonInteraction();

		// Try to click either read or stop button
		const readBtn = this.page.locator(`button[aria-label="${readLabel}"]`).last();
		const stopBtn = this.page.locator(`button[aria-label="${stopLabel}"]`).last();

		if (await stopBtn.isVisible()) {
			await stopBtn.click({ force: true });
			return false;
		} else {
			await readBtn.waitFor({ state: 'visible', timeout: 10000 });
			await readBtn.click({ force: true });
			await this.page.waitForTimeout(1000);
			return await this.isSpeaking();
		}
	}

	/**
	 * Checks if speech synthesis is active
	 */
	async isSpeaking(): Promise<boolean> {
		return await this.page.evaluate(() => window.speechSynthesis?.speaking ?? false);
	}

	/**
	 * Generates an image from the last answer context
	 */
	async generateImageFromAnswer(): Promise<void> {
		const label = this.getTranslation('Generate Image');
		await this.clickAnswerButton(label);
	}

	/**
	 * Hovers over info button to reveal token usage tooltip
	 */
	async hoverAnswerInfo(): Promise<void> {
		// Info button has id="info-{message.id}" but no aria-label
		await this.prepareAnswerButtonInteraction();
		const infoBtn = this.page.locator('button[id^="info-"]').last();
		await infoBtn.waitFor({ state: 'visible', timeout: 10000 });
		await infoBtn.hover();
		await this.page.waitForTimeout(500);
	}

	/**
	 * Returns the token info tooltip content
	 */
	async getTokenInfoText(): Promise<string> {
		const tooltip = this.page
			.locator('[role="tooltip"], .tooltip, .popover')
			.filter({ hasText: /token/i });
		await tooltip.waitFor({ state: 'visible', timeout: 5000 });
		return (await tooltip.innerText()).trim();
	}

	/**
	 * Clicks thumbs up (good response) button
	 */
	async clickGoodResponse(): Promise<void> {
		const label = this.getTranslation('Good Response');
		await this.clickAnswerButton(label);
		await this.waitToSettle(500);
	}

	/**
	 * Clicks thumbs down (bad response) button
	 */
	async clickBadResponse(): Promise<void> {
		const label = this.getTranslation('Bad Response');
		await this.clickAnswerButton(label);
		await this.waitToSettle(500);
	}

	/**
	 * Sets the rating by clicking the numbered button (1-10)
	 */
	async setRating(value: number): Promise<void> {
		const feedbackContainer = this.page.locator('[id^="message-feedback-"]').last();
		await feedbackContainer.waitFor({ state: 'visible' });
		const ratingBtn = feedbackContainer.locator(`button:has-text("${value}")`).first();
		await ratingBtn.click();
	}

	/**
	 * Selects a "Why" reason by clicking the corresponding button
	 */
	async selectFeedbackReason(reasonKey: string): Promise<void> {
		const feedbackContainer = this.page.locator('[id^="message-feedback-"]').last();
		await feedbackContainer.waitFor({ state: 'visible' });

		// Map reason keys to translated text
		const reasonTextMap: Record<string, string> = {
			accurate_information: 'Accurate information',
			followed_instructions_perfectly: 'Followed instructions perfectly',
			showcased_creativity: 'Showcased creativity',
			positive_attitude: 'Positive attitude',
			attention_to_detail: 'Attention to detail',
			thorough_explanation: 'Thorough explanation',
			dont_like_the_style: "Don't like the style",
			too_verbose: 'Too verbose',
			not_helpful: 'Not helpful',
			not_factually_correct: 'Not factually correct',
			didnt_fully_follow_instructions: "Didn't fully follow instructions",
			refused_when_it_shouldnt_have: "Refused when it shouldn't have",
			being_lazy: 'Being lazy',
			other: 'Other'
		};

		const reasonText = this.getTranslation(reasonTextMap[reasonKey] || reasonKey);
		const reasonBtn = feedbackContainer.getByRole('button', { name: reasonText });
		await reasonBtn.click();
	}

	/**
	 * Enters feedback comment
	 */
	async enterFeedbackComment(comment: string): Promise<void> {
		const feedbackContainer = this.page.locator('[id^="message-feedback-"]').last();
		const textarea = feedbackContainer.locator('textarea').first();
		await textarea.fill(comment);
	}

	/**
	 * Submits the feedback form
	 */
	async submitFeedback(): Promise<void> {
		const saveLabel = this.getTranslation('Save');
		await this.page.getByRole('button', { name: saveLabel }).click();
		await this.waitToSettle(500);
	}

	/**
	 * Stops generation by clicking the Stop button
	 */
	async stopGeneration(): Promise<void> {
		await this.stopGenerationButton.click();
		await this.waitToSettle(500);
	}

	/**
	 * Clicks the continue response button
	 */
	async continueResponse(): Promise<void> {
		const label = this.getTranslation('Continue Response');
		await this.clickAnswerButton(label);
		await this.waitForGeneration();
	}

	/**
	 * Clicks regenerate button for the last answer
	 */
	async regenerateAnswer(): Promise<void> {
		const label = this.getTranslation('Regenerate');
		await this.clickAnswerButton(label);
		await this.waitForGeneration();
	}

	/**
	 * Opens the Report Issue modal
	 */
	async openReportIssue(): Promise<void> {
		const label = this.getTranslation('Report an Issue');
		await this.clickAnswerButton(label);
		await this.waitToSettle(500);
	}

	/**
	 * Fills the issue description
	 */
	async fillIssueDescription(text: string): Promise<void> {
		const textarea = this.page.locator('#description');
		await textarea.fill(text);
	}

	/**
	 * Fills the steps to reproduce
	 */
	async fillStepsToReproduce(text: string): Promise<void> {
		const textarea = this.page.locator('#stepsToReproduce');
		await textarea.fill(text);
	}

	/**
	 * Attaches an image to the report (inside the Issue modal)
	 */
	async attachImageToReport(filePath: string): Promise<void> {
		// Target the modal's file input specifically using its ID
		const fileInput = this.page.locator('#files');
		await fileInput.setInputFiles(filePath);
		await this.waitToSettle(500);
	}

	/**
	 * Submits the issue report
	 */
	async submitIssueReport(): Promise<void> {
		const submitLabel = this.getTranslation('Submit');
		await this.page.getByRole('button', { name: submitLabel }).click();
		await this.waitToSettle(500);
	}

	/**
	 * Closes the issue modal via X button
	 */
	async closeIssueModal(): Promise<void> {
		const closeLabel = this.getTranslation('Close');
		await this.page.getByRole('button', { name: closeLabel }).click({ force: true });
		await this.waitToSettle(500);
	}

	/**
	 * Cancels the issue report
	 */
	async cancelIssueReport(): Promise<void> {
		const cancelLabel = this.getTranslation('Cancel');
		await this.page.getByRole('button', { name: cancelLabel }).click();
		await this.waitToSettle(300);
	}

	/**
	 * Opens the Suggestion Box modal
	 */
	async openSuggestionBox(): Promise<void> {
		const label = this.getTranslation('Suggestion Box');
		await this.clickAnswerButton(label);
		await this.waitToSettle(500);
	}

	/**
	 * Fills the suggestion textarea
	 */
	async fillSuggestion(text: string): Promise<void> {
		const textarea = this.page.locator('#description');
		await textarea.fill(text);
	}

	/**
	 * Attaches an image to the suggestion
	 */
	async attachImageToSuggestion(filePath: string): Promise<void> {
		const fileInput = this.page.locator('#files');
		await fileInput.setInputFiles(filePath);
		await this.waitToSettle(500);
	}

	/**
	 * Submits the suggestion
	 */
	async submitSuggestion(): Promise<void> {
		const submitLabel = this.getTranslation('Submit');
		await this.page.getByRole('button', { name: submitLabel }).click();
		await this.waitToSettle(500);
	}

	/**
	 * Closes the suggestion modal via X button
	 */
	async closeSuggestionModal(): Promise<void> {
		const closeLabel = this.getTranslation('Close');
		await this.page.getByRole('button', { name: closeLabel }).click({ force: true });
		await this.waitToSettle(500);
	}

	/**
	 * Cancels the suggestion
	 */
	async cancelSuggestion(): Promise<void> {
		const cancelLabel = this.getTranslation('Cancel');
		await this.page.getByRole('button', { name: cancelLabel }).click();
		await this.waitToSettle(300);
	}
}
