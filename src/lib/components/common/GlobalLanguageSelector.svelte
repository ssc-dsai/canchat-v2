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
        class="flex cursor-pointer px-2 py-2 rounded-xl text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
        on:click={toggleLanguage}
    >
        <div class="m-auto self-center text-sm font-medium">
            {currentLangDisplay}
        </div>
    </button>
	<button
		class="flex cursor-pointer px-2 py-2 rounded-xl bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 transition"
		on:click={toggleLanguage}
	>
		<!-- Updated text container with a solid contrasting background -->
		<div
			class="m-auto self-center text-sm font-medium text-gray-900 dark:text-white bg-white dark:bg-gray-900 px-1 rounded"
		>
			{currentLangDisplay}
		</div>
	</button>
</Tooltip>
