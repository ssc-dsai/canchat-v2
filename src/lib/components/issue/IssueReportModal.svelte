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
			submitError = $i18n.t('You can only upload up to {{maxCount}} files', {
				maxCount: MAX_FILES
			});
			input.value = ''; // Clear the selection
			files = null;
			return;
		}

		// Validate file types
		if (input.files) {
			const invalidFiles = Array.from(input.files).filter(
				(file) => !file.type.startsWith('image/')
			);
			if (invalidFiles.length > 0) {
				submitError = $i18n.t('Only image files are allowed.');
				input.value = '';
				files = null;
				return;
			}
		}

		submitError = '';
		files = input.files;
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
		if (isSubmitting) return; // Guard against multiple submissions

		try {
			if (!issueType || !email || !description || (issueType === ISSUE_TYPE && !stepsToReproduce)) {
				submitError = $i18n.t('Please fill out all required fields');
				return;
			}

			isSubmitting = true;
			submitError = '';

			const formData = new FormData();
			formData.append('email', email);
			formData.append('description', description);
			if (issueType === ISSUE_TYPE) {
				formData.append('stepsToReproduce', stepsToReproduce);
			}
			formData.append('username', $user?.name || email); // it has to be one of these two if they are a user
			formData.append('issueType', getJiraIssueType(issueType));

			// Handle files properly
			if (files) {
				for (let i = 0; i < files.length; i++) {
					formData.append(`file${i}`, files[i]);
				}
			}

			// Get hostname for environment detection
			const hostname = window.location.hostname;
			let apiUrl;

			if (hostname === 'localhost' || hostname === '127.0.0.1') {
				apiUrl = 'http://localhost:8080';
			} else {
				// In production, use the same origin
				apiUrl = window.location.origin;
			}

			const response = await fetch(`${apiUrl}/api/incident-report`, {
				method: 'POST',
				credentials: 'include',
				body: formData
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || 'Failed to submit report');
			}

			const data = await response.json();

			if (!data.success) {
				throw new Error(data.error || 'Failed to create ticket');
			}

			submitSuccess = true;
			setTimeout(() => {
				isSubmitting = false; // Set this before closing
				closeModal();
			}, 2000);
		} catch (error) {
			submitError =
				error instanceof Error
					? error.message
					: $i18n.t('Failed to submit report. Please try again later.');
			isSubmitting = false; // Make sure to reset on error
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
	<div class="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
		<h3 class="text-2xl font-medium font-primary text-gray-900 dark:text-gray-100">
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
			<div class="bg-green-50 border border-green-400 text-green-700 px-4 py-3 rounded-lg">
				<p>{$i18n.t('Thank you! Your issue report has been submitted successfully.')}</p>
			</div>
		{:else}
			<div class="w-full">
				{#if !issueType}
					<p class="text-sm text-gray-600 dark:text-gray-300 mb-4">
						{$i18n.t(
							'Share your feedback to help us improve - report issues or suggest new features.'
						)}
					</p>
				{:else if issueType === ISSUE_TYPE}
					<p class="text-sm text-gray-600 dark:text-gray-300 mb-4">
						{$i18n.t(
							'Report any problems or bugs you encounter to help us improve the application.'
						)}
					</p>
				{:else}
					<p class="text-sm text-gray-600 dark:text-gray-300 mb-4">
						{$i18n.t(
							'Share your ideas for new features or improvements to make the application better.'
						)}
					</p>
				{/if}

				<form on:submit|preventDefault={submitReport} class="space-y-4">
					<div>
						<label for="issueType" class="text-sm mb-2 block text-gray-900 dark:text-gray-100"
							>{$i18n.t('Type')} *</label
						>
						<select
							id="issueType"
							bind:value={issueType}
							required
							title={$i18n.t('Please select an item in the list')}
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-100 dark:text-gray-300 dark:bg-gray-850 outline-none border-0"
						>
							<option value="" disabled selected>{$i18n.t('Select a type...')}</option>
							{#each issueTypes as type}
								<option value={type.value}>{$i18n.t(type.label)}</option>
							{/each}
						</select>
					</div>

					{#if issueType}
						{#if submitError}
							<div class="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded-lg">
								<p>{submitError}</p>
							</div>
						{/if}

						<div>
							<label for="email" class="text-sm mb-2 block text-gray-900 dark:text-gray-100"
								>{$i18n.t('Email')}</label
							>
							<input
								type="email"
								id="email"
								bind:value={email}
								readonly
								disabled
								aria-label={$i18n.t('Email')}
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-100 dark:text-gray-300 dark:bg-gray-850 outline-none opacity-75 cursor-not-allowed"
							/>
						</div>

						{#if issueType === ISSUE_TYPE}
							<div>
								<label for="description" class="text-sm mb-2 block text-gray-900 dark:text-gray-100"
									>{$i18n.t('Description')} *</label
								>
								<textarea
									id="description"
									bind:value={description}
									rows="4"
									required
									placeholder={$i18n.t('Please describe what happened')}
									class="w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-100 dark:text-gray-300 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-gray-700"
								></textarea>
							</div>

							<div>
								<label
									for="stepsToReproduce"
									class="text-sm mb-2 block text-gray-900 dark:text-gray-100"
									>{$i18n.t('Steps to Reproduce')} *</label
								>
								<textarea
									id="stepsToReproduce"
									bind:value={stepsToReproduce}
									rows="4"
									required
									placeholder={$i18n.t('Please list the steps to reproduce this issue')}
									class="w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-100 dark:text-gray-300 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-gray-700"
								></textarea>
							</div>
						{:else}
							<div>
								<label for="description" class="text-sm mb-2 block text-gray-900 dark:text-gray-100"
									>{$i18n.t('Suggestion')} *</label
								>
								<textarea
									id="description"
									bind:value={description}
									rows="4"
									required
									placeholder={$i18n.t('Please describe your suggestion in detail')}
									class="w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-100 dark:text-gray-300 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-gray-700"
								></textarea>
							</div>
						{/if}

						<div>
							<label for="files" class="text-sm mb-2 block text-gray-900 dark:text-gray-100">
								{$i18n.t('Attach images')} ({$i18n.t('max')}
								{MAX_FILES})
							</label>
							<div class="relative mt-1">
								<input
									type="file"
									id="files"
									on:change={handleFileChange}
									multiple
									accept="image/*"
									aria-label={$i18n.t('Choose files to upload')}
									class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
								/>
								<div class="text-sm text-gray-600 dark:text-gray-400 flex items-center">
									<span
										class="inline-flex items-center px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-300"
									>
										{$i18n.t('Choose Files')}
									</span>
									<span class="ml-3 text-gray-700 dark:text-gray-400">
										{fileInputText(files)}
									</span>
								</div>
							</div>
						</div>

						<div class="flex justify-end space-x-3 pt-4">
							<button
								type="button"
								on:click={closeModal}
								class="text-sm px-4 py-2 transition rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white"
							>
								<div class="self-center font-medium">
									{$i18n.t('Cancel')}
								</div>
							</button>
							<button
								type="submit"
								disabled={isSubmitting}
								class="text-sm px-4 py-2 transition rounded-lg {isSubmitting
									? 'cursor-not-allowed bg-gray-400 text-white dark:bg-gray-100 dark:text-gray-800'
									: 'bg-gray-900 hover:bg-gray-850 text-white dark:bg-gray-100 dark:hover:bg-white dark:text-gray-800'} flex"
							>
								<div class="self-center font-medium">
									{#if isSubmitting}
										{$i18n.t('Submitting...')}
									{:else}
										{$i18n.t('Submit Report')}
									{/if}
								</div>
								{#if isSubmitting}
									<div class="ml-1.5 self-center">
										<svg
											class="w-4 h-4"
											viewBox="0 0 24 24"
											fill="currentColor"
											xmlns="http://www.w3.org/2000/svg"
										>
											<style>
												.spinner_ajPY {
													transform-origin: center;
													animation: spinner_AtaB 0.75s infinite linear;
												}
												@keyframes spinner_AtaB {
													100% {
														transform: rotate(360deg);
													}
												}
											</style>
											<path
												d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
												opacity=".25"
											/>
											<path
												d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
												class="spinner_ajPY"
											/>
										</svg>
									</div>
								{/if}
							</button>
						</div>
					{/if}
				</form>
			</div>
		{/if}
	</div>
</Modal>
