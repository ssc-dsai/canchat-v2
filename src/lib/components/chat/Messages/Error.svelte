<script lang="ts">
	import { getI18n } from '$lib/utils/context';

	import Info from '$lib/components/icons/Info.svelte';

	const i18n = getI18n();

	export let content = '';

	const localizeErrorContent = (value: string) => {
		return value.replace('Network Problem', $i18n.t('Network Problem'));
	};
</script>

<div class="flex my-2 gap-2.5 border px-4 py-3 border-red-600/10 bg-red-600/10 rounded-lg">
	<div class=" self-start mt-0.5">
		<Info className="size-5 text-red-700 dark:text-red-400" />
	</div>

	<div class=" self-center text-sm">
		{typeof content === 'string' ? localizeErrorContent(content) : JSON.stringify(content)}
	</div>
</div>
