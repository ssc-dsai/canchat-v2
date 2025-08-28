<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getModels, getToolServersData } from '$lib/apis';
	import { getTools } from '$lib/apis/tools';
	import { getBanners } from '$lib/apis/configs';
	import { getUserSettings } from '$lib/apis/users';
	import {
		config,
		user,
		settings,
		models,
		tools,
		banners,
		showSettings,
		showChangelog,
		temporaryChatEnabled,
		toolServers
	} from '$lib/stores';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import SettingsModal from '$lib/components/chat/SettingsModal.svelte';
	import ChangelogModal from '$lib/components/ChangelogModal.svelte';
	import AccountPending from '$lib/components/layout/Overlay/AccountPending.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($user === undefined || $user === null) {
			await goto('/auth');
			return;
		}

		if ($user?.role && $user?.role !== 'pending') {
			const userSettings = await getUserSettings(localStorage.token).catch(console.error);
			if (userSettings) {
				settings.set(userSettings.ui);
			} else {
				let localStorageSettings = {};
				try {
					localStorageSettings = JSON.parse(localStorage.getItem('settings') ?? '{}');
				} catch (e) {
					console.error('Failed to parse settings from localStorage', e);
				}
				settings.set(localStorageSettings);
			}

			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);

			banners.set(await getBanners(localStorage.token));
			tools.set(await getTools(localStorage.token));
			toolServers.set(await getToolServersData($i18n, $settings?.toolServers ?? []));

			document.addEventListener('keydown', async (event) => {
				const isCtrl = event.ctrlKey || event.metaKey;
				const isShift = event.shiftKey;
				const key = event.key.toLowerCase();

				if (isCtrl && isShift && key === 'o') {
					event.preventDefault();
					document.getElementById('sidebar-new-chat-button')?.click();
				}
				if (isShift && event.key === 'Escape') {
					event.preventDefault();
					document.getElementById('chat-input')?.focus();
				}
				if (isCtrl && isShift && event.key === ';') {
					event.preventDefault();
					[...document.getElementsByClassName('copy-code-button')].at(-1)?.click();
				}
				if (isCtrl && isShift && key === 'c') {
					event.preventDefault();
					[...document.getElementsByClassName('copy-response-button')].at(-1)?.click();
				}
				if (isCtrl && isShift && key === 's') {
					event.preventDefault();
					document.getElementById('sidebar-toggle-button')?.click();
				}
				if (isCtrl && isShift && document.getElementById('delete-chat-button')) {
					document.getElementById('delete-chat-button')?.click();
				}
				if (isCtrl && event.key === '.') {
					event.preventDefault();
					showSettings.set(!$showSettings);
				}
				if (isCtrl && event.key === '/') {
					event.preventDefault();
					document.getElementById('show-shortcuts-button')?.click();
				}
				if (isCtrl && isShift && (key === `'` || key === `"`)) {
					event.preventDefault();
					temporaryChatEnabled.set(!$temporaryChatEnabled);
					await goto('/');
					setTimeout(() => {
						document.getElementById('new-chat-button')?.click();
					}, 0);
				}
			});

			if ($user?.role === 'admin' && ($settings?.showChangelog ?? true)) {
				showChangelog.set($settings?.version !== $config.version);
			}

			if ($user?.permissions?.chat?.temporary ?? true) {
				if ($page.url.searchParams.get('temporary-chat') === 'true') {
					temporaryChatEnabled.set(true);
				}
				if ($user?.permissions?.chat?.temporary_enforced) {
					temporaryChatEnabled.set(true);
				}
			}
			await tick();
		}
		loaded = true;
	});
</script>

<SettingsModal bind:show={$showSettings} />
<ChangelogModal bind:show={$showChangelog} />

<div class="app relative">
	<div
		class="text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900 h-screen max-h-[100dvh] overflow-auto flex flex-row justify-end"
	>
		{#if $user?.role && $user?.role === 'pending'}
			<AccountPending />
		{/if}

		<Sidebar />

		{#if loaded}
			<slot />
		{:else}
			<div class="w-full flex-1 h-full flex items-center justify-center">
				<Spinner />
			</div>
		{/if}
	</div>
</div>

<style>
	.loading {
		display: inline-block;
		clip-path: inset(0 1ch 0 0);
		animation: l 1s steps(3) infinite;
		letter-spacing: -0.5px;
	}
	@keyframes l {
		to {
			clip-path: inset(0 -1ch 0 0);
		}
	}
	pre[class*='language-'] {
		position: relative;
		overflow: auto;
		margin: 5px 0;
		padding: 1.75rem 0 1.75rem 1rem;
		border-radius: 10px;
	}
	pre[class*='language-'] button {
		position: absolute;
		top: 5px;
		right: 5px;
		font-size: 0.9rem;
		padding: 0.15rem;
		background-color: #828282;
		border: ridge 1px #7b7b7c;
		border-radius: 5px;
		text-shadow: #c4c4c4 0 0 2px;
	}
	pre[class*='language-'] button:hover {
		cursor: pointer;
		background-color: #bcbabb;
	}
</style>
