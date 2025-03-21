<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Modal from '../common/Modal.svelte';
	import { user } from '$lib/stores';
	import { createEventDispatcher } from 'svelte';

	export let show = false;

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	let email = $user?.email || '';
	let description = '';
	let stepsToReproduce = '';
	let files: FileList | null = null;
	let isSubmitting = false;
	let submitSuccess = false;
	let submitError = '';
	let issueType = ''; // Start empty instead of defaulting to 'Issue'
	const MAX_FILES = 3;

	const ISSUE_TYPE = 'Issue';
	const SUGGESTION_TYPE = 'Suggestion';

	// Use constants in the array but translate for display
	const issueTypes = [
		{ value: ISSUE_TYPE, label: $i18n.t('Issue') },
		{ value: SUGGESTION_TYPE, label: $i18n.t('Suggestion') }
	];

	let mounted = false; // Add mounted variable

	onMount(() => {
		mounted = true;
	});

	const getJiraIssueType = (type: string) => {
		return type === ISSUE_TYPE ? 'Bug' : 'Task';
	};

	const resetForm = () => {
		email = $user?.email || '';
		description = '';
		stepsToReproduce = '';
		files = null;
		submitSuccess = false;
		submitError = '';
		issueType = ''; // Reset the issue type as well
	};

	const handleFileChange = (event: Event) => {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files.length > MAX_FILES) {
			submitError = $i18n.t(`You can only upload up to ${MAX_FILES} files`);
			input.value = ''; // Clear the selection
			files = null;
		} else {
			submitError = '';
			files = input.files;
		}
	};

	const closeModal = () => {
		show = false;
		resetForm(); // Reset immediately instead of with timeout
	};

	$: if (!show && mounted) {
		closeModal();
	}

	$: if (issueType) {
		// Clear form data when switching between issue types
		description = '';
		stepsToReproduce = '';
		files = null;
		submitError = '';
		submitSuccess = false;

		// Clear file input element if it exists
		const fileInput = document.getElementById('files') as HTMLInputElement;
		if (fileInput) {
			fileInput.value = '';
		}
	}

	const submitReport = async () => {
		if (!issueType || !email || !description || (issueType === ISSUE_TYPE && !stepsToReproduce)) {
			submitError = $i18n.t('Please fill out all required fields');
			return;
		}

		isSubmitting = true;
		submitError = '';

		try {
			// Prepare form data for file uploads
			const formData = new FormData();
			formData.append('email', email);
			formData.append('description', description);
			if (issueType === ISSUE_TYPE) {
				formData.append('stepsToReproduce', stepsToReproduce);
			}
			formData.append('username', $user?.name || email); // it has to be one of these two if they are a user
			formData.append('issueType', getJiraIssueType(issueType));

			// Add files if any
			if (files) {
				for (let i = 0; i < files.length; i++) {
					formData.append('files', files[i]);
				}
			}

			console.log('Submitting incident report...');

			// Send to our API endpoint
			const response = await fetch('/api/incident-report', {
				method: 'POST',
				body: formData
			});

			const responseData = await response.json();

			if (!response.ok) {
				console.error('Error response:', responseData);
				throw new Error(responseData.error || `Error: ${response.status}`);
			}

			console.log('Report submitted successfully:', responseData);

			// Show error if the server reported one despite 200 status
			if (responseData.success === false) {
				throw new Error(responseData.error || 'Failed to create ticket in Jira');
			}

			submitSuccess = true;
			// Don't reset form immediately, let the success message show
			setTimeout(() => {
				resetForm();
				closeModal();
			}, 2000);
		} catch (error) {
			console.error('Error submitting incident report:', error);
			submitError =
				error instanceof Error
					? error.message
					: $i18n.t('Failed to submit report. Please try again later.');
		} finally {
			isSubmitting = false;
		}
	};

	const fileInputText = (files: FileList | null) => {
		if (!files || files.length === 0) {
			return $i18n.t('No file chosen');
		}
		return Array.from(files)
			.map((f) => f.name)
			.join(', ');
	};
</script>

<Modal bind:show maxWidth="max-w-xl" on:close={closeModal} disableClose={isSubmitting}>
	<!-- Add custom header -->
	<div class="flex justify-between items-center p-4">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
			{#if !issueType}
				{$i18n.t('Issue and Suggestion Form')}
			{:else if issueType === ISSUE_TYPE}
				{$i18n.t('Issue Form')}
			{:else}
				{$i18n.t('Suggestion Form')}
			{/if}
		</h3>
		<button
			on:click={() => !isSubmitting && (show = false)}
			class="text-gray-400 {isSubmitting
				? 'opacity-50 cursor-not-allowed'
				: 'hover:text-gray-500'} focus:outline-none"
			disabled={isSubmitting}
		>
			<span class="sr-only">Close</span>
			<svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M6 18L18 6M6 6l12 12"
				/>
			</svg>
		</button>
	</div>

	<div class="p-4">
		{#if submitSuccess}
			<div class="bg-green-50 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
				<p>{$i18n.t('Thank you! Your issue report has been submitted successfully.')}</p>
			</div>
		{:else}
			{#if !issueType}
				<p class="text-gray-600 dark:text-gray-300 mb-4">
					{$i18n.t(
						'Share your feedback to help us improve - report issues or suggest new features.'
					)}
				</p>
			{:else if issueType === ISSUE_TYPE}
				<p class="text-gray-600 dark:text-gray-300 mb-4">
					{$i18n.t('Report any problems or bugs you encounter to help us improve the application.')}
				</p>
			{:else}
				<p class="text-gray-600 dark:text-gray-300 mb-4">
					{$i18n.t(
						'Share your ideas for new features or improvements to make the application better.'
					)}
				</p>
			{/if}
			<form on:submit|preventDefault={submitReport} class="space-y-4">
				<div>
					<label for="issueType" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						{$i18n.t('Type')} *
					</label>
					<select
						id="issueType"
						bind:value={issueType}
						required
						title={$i18n.t('Please select an item in the list')}
						class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
					>
						<option value="" disabled selected>{$i18n.t('Select a type...')}</option>
						{#each issueTypes as type}
							<option value={type.value}>{$i18n.t(type.label)}</option>
						{/each}
					</select>
				</div>

				{#if issueType}
					{#if submitError}
						<div class="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
							<p>{submitError}</p>
						</div>
					{/if}

					<!-- Email field -->
					<div>
						<label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							{$i18n.t('Email')}
						</label>
						<input
							type="email"
							id="email"
							bind:value={email}
							readonly
							disabled
							class="mt-1 block w-full rounded-md border-gray-300 bg-gray-50 cursor-not-allowed shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-300"
						/>
					</div>

					<!-- Different fields based on issue type -->
					{#if issueType === ISSUE_TYPE}
						<!-- Description field for Issue -->
						<div>
							<label
								for="description"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300"
							>
								{$i18n.t('Description')} *
							</label>
							<textarea
								id="description"
								bind:value={description}
								rows="5"
								required
								placeholder={$i18n.t('Please describe what happened')}
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
							></textarea>
						</div>

						<!-- Steps to reproduce field -->
						<div>
							<label
								for="stepsToReproduce"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300"
							>
								{$i18n.t('Steps to Reproduce')} *
							</label>
							<textarea
								id="stepsToReproduce"
								bind:value={stepsToReproduce}
								rows="5"
								required
								placeholder={$i18n.t('Please list the steps to reproduce this issue')}
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
							></textarea>
						</div>
					{:else}
						<!-- Suggestion field -->
						<div>
							<label
								for="description"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300"
							>
								{$i18n.t('Suggestion')} *
							</label>
							<textarea
								id="description"
								bind:value={description}
								rows="5"
								required
								placeholder={$i18n.t('Please describe your suggestion in detail')}
								class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
							></textarea>
						</div>
					{/if}

					<!-- File attachment field -->
					<div>
						<label for="files" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							{$i18n.t('Attachments')} ({$i18n.t('max')}
							{MAX_FILES})
						</label>
						<div class="relative mt-1">
							<input
								type="file"
								id="files"
								on:change={handleFileChange}
								multiple
								accept="image/*"
								class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
								aria-label={$i18n.t('Choose Files')}
								title={$i18n.t('Choose Files')}
							/>
							<div class="text-sm text-gray-500 dark:text-gray-400 flex items-center">
								<span
									class="inline-flex items-center px-4 py-2 rounded-md border-0 text-sm font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-gray-700 dark:text-gray-300"
									title={$i18n.t('Choose Files')}
								>
									{$i18n.t('Choose Files')}
								</span>
								<span class="ml-3" title={$i18n.t('No file chosen')}>
									{fileInputText(files)}
								</span>
							</div>
						</div>
					</div>

					<!-- Submit buttons -->
					<div class="flex justify-end space-x-3 pt-4">
						<button
							type="button"
							on:click={closeModal}
							class="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:border-gray-600 dark:hover:bg-gray-600"
						>
							{$i18n.t('Cancel')}
						</button>
						<button
							type="submit"
							disabled={isSubmitting}
							class="inline-flex justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-indigo-700 dark:hover:bg-indigo-800"
						>
							{#if isSubmitting}
								<svg
									class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
								>
									<circle
										class="opacity-25"
										cx="12"
										cy="12"
										r="10"
										stroke="currentColor"
										stroke-width="4"
									></circle>
									<path
										class="opacity-75"
										fill="currentColor"
										d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
									></path>
								</svg>
								{$i18n.t('Submitting...')}
							{:else}
								{$i18n.t('Submit Report')}
							{/if}
						</button>
					</div>
				{/if}
			</form>
		{/if}
	</div>
</Modal>
