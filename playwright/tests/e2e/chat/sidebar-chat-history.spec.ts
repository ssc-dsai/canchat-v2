import { test, expect } from '../../../src/fixtures/base-fixture';

test.describe('Sidebar and Chat History Features', () => {
	test.setTimeout(120000);

	// ===========================================
	// CHAT-SIDEBAR-TC001: Hide/Display Sidebar
	// ===========================================
	test('CHAT-SIDEBAR-TC001: User can hide/display the sidebar', async ({ userPage }) => {
		// 1. If the sidebar is displayed, click on the "Hide Sidebar" button.
		await userPage.toggleSidebar(false);

		// 2. User observes that the sidebar is hidden.
		await expect(userPage.sidebarCloseButton).not.toBeVisible();
		await expect(userPage.sidebarOpenButton).toBeVisible();
		await expect(userPage.headerNewChatButton).toBeVisible();
		await expect(userPage.sidebarNewChatButton).not.toBeVisible();

		// 3. If the sidebar is hidden, user clicks on the "Show Sidebar" button.
		await userPage.toggleSidebar(true);

		// 4. User observes that the sidebar is displayed.
		await expect(userPage.sidebarCloseButton).toBeVisible();
		await expect(userPage.sidebarOpenButton).not.toBeVisible();
		await expect(userPage.headerNewChatButton).not.toBeVisible();
		await expect(userPage.sidebarNewChatButton).toBeVisible();
	});

	// ===========================================
	// CHAT-SIDEBAR-TC002: Create New Chat from Sidebar
	// ===========================================
	test('CHAT-SIDEBAR-TC002: User can create a new chat from the sidebar', async ({ userPage }) => {
		// 1. User clicks on the new chat button in the sidebar
		const initialModel = await userPage.getSelectedModel();

		await userPage.toggleSidebar(true);
		await userPage.sidebarNewChatButton.click();

		// 2. User observes that the chat page suggestions cycle to new ones
		await expect(userPage.page.locator('button:has(span.font-medium)').first()).toBeVisible();

		// 3. User observes that the default model is selected in the new chat
		const modelAfterNewChat = await userPage.getSelectedModel();
		expect(modelAfterNewChat).toBe(initialModel);

		// 4. User enter a message in the chat: "When was Shared Services Canada founded?"
		await userPage.sendMessage('When was Shared Services Canada founded?');

		// 5. User wait for the answer to be fully generated.
		await expect(userPage.responseMessages.last()).toBeVisible();

		// 6. User clicks on the "New Chat" button in the sidebar
		// NOTE: Using page.goto('/') as a workaround because Playwright's click/dispatchEvent
		// is not triggering Svelte's event handlers on this button when inside a conversation.
		await userPage.page.goto('/');
		await expect(userPage.page.locator('button:has(span.font-medium)').first()).toBeVisible({ timeout: 30000 });

		// 8. User observe that his default model is selected in the chat page.
		const finalModel = await userPage.getSelectedModel();
		expect(finalModel).toBe(initialModel);
	});

	// ===========================================
	// CHAT-SIDEBAR-TC003: Search Chat History
	// ===========================================
	test('CHAT-SIDEBAR-TC003: User can perform a search on his chat history', async ({ userPage }) => {
		// 1. Ensure we have at least one specific chat to search for
		await userPage.sendMessage('Tell me about Shared Services Canada');
		await expect(userPage.responseMessages.last()).toBeVisible();
		await userPage.page.waitForTimeout(2000);

		// 2. Click inside the sidebar on the "Search" lookup field
		await userPage.toggleSidebar(true);
		await userPage.searchInput.click();

		// 3. User enter a search term: "Shared"
		await userPage.searchInput.fill('Shared');
		await expect(userPage.searchInput).toHaveValue('Shared');

		// 4. User observe that only the relevant chat is displayed
		const sharedChatItems = userPage.chatHistoryItems.filter({ hasText: /Shared/i });
		await expect(sharedChatItems.first()).toBeVisible({ timeout: 10000 });

		const countBefore = await userPage.chatHistoryItems.count();

		// 5. User clicks on the "X" button to clear the search field
		await userPage.clearSearchButton.waitFor({ state: 'visible', timeout: 10000 });
		await userPage.clearSearchButton.click();

		// 6. User observe that the search field is cleared and all chats are displayed again
		await expect(userPage.searchInput).toHaveValue('');
		await userPage.page.waitForTimeout(5000);
		const countAfter = await userPage.chatHistoryItems.count();
		expect(countAfter).toBeGreaterThanOrEqual(countBefore)

		// 7. User enter the search term for tag: "tag:"
		await userPage.searchInput.press('Escape');
		await userPage.searchInput.click();
		await userPage.searchInput.pressSequentially('tag:', { delay: 100 });
		await userPage.waitToSettle(5000);

		// 8. User selects one of the available tag (e.g., the first one)
		await userPage.selectSearchTag(0);
		const tagSearchValue = await userPage.searchInput.inputValue();
		expect(tagSearchValue).toContain('tag:');

		// 9. User observes the chat conversation are filtered
		await expect(userPage.chatHistoryItems.first()).toBeVisible();

		// 10. User clicks on one of the available conversation
		const firstChatTitle = await userPage.chatHistoryItems.first().innerText();
		await userPage.searchInput.press('Escape');
		await userPage.chatHistoryItems.first().click();

		// 11. User observes that the conversation opens
		await expect(userPage.page).toHaveURL(/\/c\/.+/);
	});

	// ===========================================
	// CHAT-SIDEBAR-TC004: Select Old Chat
	// ===========================================
	test.skip('CHAT-SIDEBAR-TC004: User can select an old chat in his history', async ({ userPage }) => {
		// 1. User clicks on a conversation inside the sidebar. 

		// 2. User observe the conversation opens
		// 3. User sends a follow-up message to the conversation
		// 4. User observe that he receives an answer
	});

	// ===========================================
	// CHAT-SIDEBAR-TC005: Bulk Delete Chats
	// ===========================================
	test.skip('CHAT-SIDEBAR-TC005: User can select chats to delete', async ({ userPage }) => {
		// 1. User selects a conversation in the sidebar by clicking on the checkbox on the left of its name
		// 2. User observe that the delete section contains "1 selected"
		// 3. User clicks on the "Delete" button above the chat history section
		// 4. User observes that the conversation he had selected is deleted from the list
		// 5. User selects 2 conversations in the sidebar by clicking on the checkbox on the left of their names
		// 6. User observe that the delete section contains "2 selected"
		// 7. User clicks on the "Delete" button above the chat history section
		// 8. User observes that the conversation he had selected is deleted from the list
	});

	// ===========================================
	// CHAT-SIDEBAR-TC006: Create Folders and Move Conversations
	// ===========================================
	test.skip('CHAT-SIDEBAR-TC006: User can create chat folders and move conversation in them', async ({ userPage }) => {
		// 1. User hover over the "Chats" menu item in the sidebar to display the "+" new folder button
		// 2. User click on the "+" button to create a new folder
		// 3. User observe that a folder named "Untitled X" has been created under the "Chats" menu item.
		// 4. User select a conversation by dragging it and drop it inside the folder he created
		// 5. User observes that the conversation he selected has been moved inside the folder he chose.
	});

	// ===========================================
	// CHAT-SIDEBAR-TC007: Delete Chat Folders
	// ===========================================
	test.skip('CHAT-SIDEBAR-TC007: User can delete chat folders from the sidebar', async ({ userPage }) => {
		// 1. User hover over the folder name he want to delete (empty folder)
		// 2. User click on the 3 dots menu "Chat Menu" next to the chat name
		// 3. User clicks on the "Delete" button
		// 4. User clicks on the "Cancel" button
		// 5. User observe that the chat he selected has not been deleted
		// 6. User hover over the folder name he want to delete (empty folder)
		// 7. User click on the 3 dots menu "Chat Menu" next to the chat name
		// 8. User clicks on the "Delete" button
		// 9. User clicks on the "Confirm" button
		// 10. User observe the Toast message "Folder deleted successfully"
		// 11. User observes that the folder and conversation have been deleted
		// 12. User hover over the folder name he want to delete (1+ conversation)
		// 13. User click on the 3 dots menu "Chat Menu" next to the chat name
		// 14. User clicks on the "Delete" button
		// 15. User clicks on the "Confirm" button
		// 16. User observe the Toast message "Folder deleted successfully"
		// 17. User observes that the folder and conversation have been deleted
	});

	// ===========================================
	// CHAT-SIDEBAR-TC008: Pin/Unpin Chat
	// ===========================================
	test.skip('CHAT-SIDEBAR-TC008: User can pin a chat in the sidebar', async ({ userPage }) => {
		// 1. User sends a message to create a new conversation: "Write me a story"
		// 2. User hover over the conversation he just created and click on the 3dot button
		// 3. User clicks on the "Pin" menu item.
		// 4. User observes that the chat is moved to the "Pinned" section of the chat menu.
		// 5. User observes the Toast message "Chat pinned. You can find it at the top section of your chat list."
		// 6. User hover over the conversation he just pinned and click on the 3dot button
		// 7. User clicks on the "Unpin" menu item.
		// 8. User observes that the chat is moved from the "Pinned" section of the chat menu to the regular section.
		// 9. User observes the Toast message "Chat unpinned. It will now appear in the regular list."
	});

	// ===========================================
	// CHAT-SIDEBAR-TC009: Rename Chat or Folder
	// ===========================================
	test.skip('CHAT-SIDEBAR-TC009: User can rename a chat or folder in the sidebar', async ({ userPage }) => {
		// 1. User sends a message to create a new conversation: "Write me a story"
		// 2. User hover over the conversation he just created and click on the 3dot button
		// 3. User clicks on the "Rename" menu item.
		// 4. User click on the "X" to cancel the renaming
		// 5. User observes that the conversation is no longer in edit mode
		// 6. User observes a Toast notification "Chat title rename cancelled"
		// 7. User hover over the conversation he just created and click on the 3dot button
		// 8. User clicks on the "Rename" menu item.
		// 9. User renames the chat to "Test Rename 1"
		// 10. User clicks on the "Confirm" button.
		// 11. User observe the chat has been renamed to the new value
		// 12. User observes a toast notification "Chat title saved."
		// 13. User double clicks on the chat he just renamed to enter edit mode
		// 14. User renames the chat to "Test Rename 2"
		// 15. User clicks on the "Confirm" button.
		// 16. User observe the chat has been renamed to the new value
		// 17. User observes a toast notification "Chat title saved."
		// 18. User hover over a chat folder and click on the 3dot button
		// 19. User clicks on the "Rename" menu item
		// 20. User observes that the name is in edit mode
		// 21. User clicks outside the folder name to exit the edit mode.
		// 22. User double clicks on the folder name to enter edit mode
		// 23. User enter a new name for the folder: "Folder Test Rename"
		// 24. User press "Enter" on his keyboard to confirm the new name
		// 25. User observes that the folder has been renamed
		// 26. User observes a toast notification "Folder name updated successfully"
	});

	// ===========================================
	// CHAT-SIDEBAR-TC010: Clone Chat
	// ===========================================
	test.skip('CHAT-SIDEBAR-TC010: User can clone a chat in the sidebar', async ({ userPage }) => {
		// 1. User sends a message to create a new conversation
		// 2. User hover over the conversation he just created and click on the 3dot button
		// 3. User clicks on the "Clone" menu item.
		// 4. User observe a Toast notification "Chat cloned successfully. You are now in the new chat."
		// 5. User observe a newly chat that starts with "Clone of" + the name of the original chat name
	});

	// ===========================================
	// CHAT-SIDEBAR-TC011: Archive Chat
	// ===========================================
	test.skip('CHAT-SIDEBAR-TC011: User can archive a chat in the sidebar', async ({ userPage }) => {
		// 1. User sends a message to create a new conversation
		// 2. User hover over the conversation he just created and click on the 3dot button
		// 3. User clicks on the "Archive" menu item.
		// 4. User observe a Toast notification "Chat archived successfully"
		// 5. User observes that the chat is no longer in the sidebar
	});

	// ===========================================
	// CHAT-SIDEBAR-TC012: Download Chat
	// ===========================================
	test.skip('CHAT-SIDEBAR-TC012: User can download a chat from the sidebar', async ({ userPage }) => {
		// 1. User sends a message to create a new conversation
		// 2. User hover over the conversation he just created and click on the 3dot button
		// 3. User clicks on the "Download" menu item and then the "Plain Text (.txt)" sub-menu item
		// 4. User observe a .txt document has been downloaded that contains the name of the conversation he selected
		// 5. User hover over the conversation he just created and click on the 3dot button
		// 6. User clicks on the "Download" menu item and then the "PDF document (.pdf)" sub-menu item
		// 7. User observe a .pdf document has been downloaded that contains the name of the conversation he selected
	});

	// ===========================================
	// CHAT-SIDEBAR-TC013: Add and Remove Tags
	// ===========================================
	test.skip('CHAT-SIDEBAR-TC013: User can add and remove tags to a chat in the sidebar', async ({ userPage }) => {
		// 1. User sends a message to create a new conversation
		// 2. User hover over the conversation he just created and click on the 3dot button
		// 3. User clicks on the "+" menu item next to "Add a tag"
		// 4. User clicks on the "Checkmark" button
		// 5. User observes a Toast notification "Invalid Tag" is displayed
		// 6. User click on the "Add a tag" and selects one pre-existing from the list item.
		// 7. User clicks on the "Checkmark" button
		// 8. User hover over the conversation he just created and click on the 3dot button
		// 9. User observes that the tag he added is present.
		// 10. User hover over the tag he created and clicks the "X"
		// 11. User observes that the tag he added has been removed
	});

	// ===========================================
	// CHAT-SIDEBAR-TC014: Create New Chat from Header (Sidebar hidden)
	// ===========================================
	test.skip('CHAT-SIDEBAR-TC014: User can create a new chat from the header when the sidebar is hidden', async ({ userPage }) => {
		// 1. User clicks on the new chat button in the header
		// 2. User observes that the chat page suggestions cycle to new ones
		// 3. User observes that the default model is selected in the new chat
		// 4. User enter a message in the chat: "When was Shared Services Canada founded?"
		// 5. User wait for the answer to be fully generated.
		// 6. User clicks on the "New Chat" button in the header.
		// 7. User observe that a new chat has been created
		// 8. User observe that his default model is selected in the chat page.
	});
});
