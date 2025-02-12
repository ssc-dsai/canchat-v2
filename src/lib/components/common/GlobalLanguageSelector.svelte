<script lang="ts">
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import Tooltip from './Tooltip.svelte';

	const i18n = getContext('i18n');
	let currentLang = $i18n.language;

	const toggleLanguage = () => {
		const newLang = currentLang === 'en-GB' ? 'fr-CA' : 'en-GB';
		$i18n.changeLanguage(newLang);
		currentLang = newLang;
	};

	// Show opposite language code
	$: currentLangDisplay = currentLang === 'en-GB' ? 'FR' : 'EN';
</script>

<Tooltip content={currentLang === 'en-GB' ? 'Français' : 'English'}>
	<button
		class="group flex cursor-pointer px-2 py-2 rounded-xl bg-white dark:bg-gray-900 transition hover:bg-gray-100 dark:hover:bg-gray-800"
		on:click={toggleLanguage}
	>
		<div
			class="m-auto self-center text-sm font-medium text-gray-900 dark:text-white px-1.5 rounded transition"
		>
			{currentLangDisplay}
		</div>
	</button>
</Tooltip>
