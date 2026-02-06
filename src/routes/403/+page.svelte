<script>
	import { getI18n } from '$lib/utils/context';
	import { WEBUI_NAME } from '$lib/stores';
	import { onMount } from 'svelte';

	const i18n = getI18n();

	let loaded = false;

	onMount(() => {
		loaded = true;
	});
</script>

<svelte:head>
	<title>Access Required - {$WEBUI_NAME}</title>
</svelte:head>

{#if loaded}
	<div class="absolute w-full h-full flex z-50 bg-white dark:bg-gray-900">
		<div class="absolute rounded-xl w-full h-full flex justify-center items-center">
			<div class="m-auto max-w-2xl px-6">
				<div class="text-center">
					<!-- Lock Icon -->
					<div class="flex justify-center mb-6">
						<div
							class="rounded-full bg-gray-100 dark:bg-gray-800 p-6 inline-flex items-center justify-center"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-16 h-16 text-gray-600 dark:text-gray-400"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								stroke-width="1.5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
								/>
							</svg>
						</div>
					</div>

					<!-- Error Code -->
					<div class="text-6xl font-bold text-gray-800 dark:text-gray-200 mb-2">403</div>

					<!-- Main Message -->
					<div class="text-2xl font-semibold text-gray-700 dark:text-gray-300 mb-4">
						{$i18n.t('Access Not Authorized')}
					</div>

					<!-- Description -->
					<div class="text-base text-gray-600 dark:text-gray-400 mb-8 leading-relaxed">
						{$i18n.t(
							"You don't currently have permission to access this system. To gain access, you'll need to complete the enrollment process."
						)}
					</div>

					<!-- Enrollment Instructions -->
					<div
						class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6 mb-8 text-left"
					>
						<h3 class="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-3">
							{$i18n.t('How to Enrol')}
						</h3>
						<ol class="list-decimal list-inside space-y-2 text-sm text-blue-800 dark:text-blue-200">
							<li>
								{$i18n.t('Contact your system administrator to request access')}
							</li>
							<li>
								{$i18n.t('Complete any required enrollment or onboarding forms')}
							</li>
							<li>
								{$i18n.t('Wait for approval confirmation (this may take 1-2 business days)')}
							</li>
							<li>
								{$i18n.t('Once approved, try signing in again')}
							</li>
						</ol>
					</div>

					<!-- Action Buttons -->
					<div class="flex flex-col sm:flex-row gap-3 justify-center">
						<a
							href="mailto:support@example.com?subject=Access%20Request"
							class="inline-flex items-center justify-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-5 h-5 mr-2"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								stroke-width="2"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
								/>
							</svg>
							{$i18n.t('Request Access')}
						</a>

						<button
							class="inline-flex items-center justify-center px-6 py-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 font-medium rounded-lg transition-colors duration-200"
							on:click={() => {
								window.location.href = '/auth';
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-5 h-5 mr-2"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								stroke-width="2"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M10 19l-7-7m0 0l7-7m-7 7h18"
								/>
							</svg>
							{$i18n.t('Back to Sign In')}
						</button>
					</div>

					<!-- Help Text -->
					<div class="mt-8 text-sm text-gray-500 dark:text-gray-500">
						{$i18n.t('Need immediate assistance?')}
						<a href="#" class="text-blue-600 dark:text-blue-400 hover:underline font-medium ml-1">
							{$i18n.t('Contact Support')}
						</a>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
