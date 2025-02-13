<script lang="ts">
	import { getContext } from 'svelte';
	import { locale } from '$lib/stores/locale';
	import Tooltip from './Tooltip.svelte';

	const i18n = getContext('i18n');

	function toggleLanguage() {
		$locale = $locale === 'en-GB' ? 'fr-CA' : 'en-GB';
		$i18n.changeLanguage($locale);
	}

	$: currentLangDisplay = $locale === 'en-GB' ? 'FR' : 'EN';
</script>

<Tooltip content={$locale === 'en-GB' ? 'Français' : 'English'}>
	<button
		class="flex cursor-pointer px-2 py-2 rounded-xl text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
		on:click={toggleLanguage}
	>
		<div class="m-auto self-center text-sm font-medium">
			{currentLangDisplay}
		</div>
	</button>
</Tooltip>
