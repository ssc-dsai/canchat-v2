<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user } from '$lib/stores';
	import { getPromptByCommand } from '$lib/apis/prompts';

	const i18n = getContext('i18n');

	export let command: string;
	let prompt = null;
	let loading = true;
	let error = null;

	onMount(async () => {
		try {
			// Remove any leading slash from the command
			const sanitizedCommand = command?.replace(/^\//, '');
			if (!sanitizedCommand) {
				throw new Error('Invalid command');
			}

			prompt = await getPromptByCommand(localStorage.token, sanitizedCommand);
		} catch (err) {
			console.error('Error loading prompt:', err);
			error = err.message || 'Failed to load prompt';
		} finally {
			loading = false;
		}
	});
</script>

<div class="w-full max-h-full">
	{#if loading}
		<div class="flex justify-center items-center h-64">
			<div class="loader">Loading...</div>
		</div>
	{:else if error}
		<div class="flex justify-center items-center h-64">
			<div class="text-red-500">{error}</div>
		</div>
	{:else if prompt}
		<div class="flex flex-col max-w-lg mx-auto mt-10 mb-10">
			<div class="w-full flex flex-col justify-center">
				<div class="text-2xl font-medium font-primary mb-2.5">
					{$i18n.t('View prompt')}
				</div>

				<div class="w-full flex flex-col gap-2.5">
					<div class="w-full">
						<div class="text-sm mb-2">{$i18n.t('Title')}</div>
						<div class="w-full mt-1 px-4 py-2 rounded-lg bg-gray-50 dark:bg-gray-850">
							{prompt.title}
						</div>
					</div>

					<div class="w-full">
						<div class="text-sm mb-2">{$i18n.t('Command')}</div>
						<div class="w-full mt-1 px-4 py-2 rounded-lg bg-gray-50 dark:bg-gray-850">
							/{prompt.command}
						</div>
					</div>

					<div>
						<div class="text-sm mb-2">{$i18n.t('Prompt Content')}</div>
						<div
							class="w-full mt-1 px-4 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 whitespace-pre-wrap"
						>
							{prompt.content}
						</div>
					</div>
				</div>
			</div>
		</div>
	{:else}
		<div class="flex justify-center items-center h-64">
			<div class="text-gray-500">{$i18n.t('Prompt not found')}</div>
		</div>
	{/if}
</div>
