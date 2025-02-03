<script lang="ts">
    import { getContext, onMount } from 'svelte';
    import { getLanguages } from '$lib/i18n';
    import Tooltip from '../common/Tooltip.svelte';

    const i18n = getContext('i18n');
    let languages: Awaited<ReturnType<typeof getLanguages>> = [];
    let currentLang = $i18n.language;

    const toggleLanguage = () => {
        const newLang = currentLang === 'en-GB' ? 'fr-CA' : 'en-GB';
        $i18n.changeLanguage(newLang);
        currentLang = newLang;
    };

    onMount(async () => {
        languages = await getLanguages();
    });

    $: currentLanguage = languages.find(lang => lang.code === currentLang);
</script>

<div class="w-full flex justify-between items-center px-1 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900 transition">
    <span class="text-xs font-medium">{$i18n.t('Language')}</span>
    <button
        class="flex items-center space-x-1 px-2 py-1 rounded"
        on:click={toggleLanguage}
    >
        <span class="text-sm">
            {#if currentLanguage}
                {currentLanguage.title}
            {/if}
        </span>
    </button>
</div>
