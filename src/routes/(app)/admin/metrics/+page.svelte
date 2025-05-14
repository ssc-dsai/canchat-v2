<script>
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	// Redirect to the new metrics location in workspace
	onMount(() => {
		goto('/workspace/metrics');
	});
</script>

<div class="flex items-center justify-center h-full">
	<div class="text-center">
		<div
			class="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gray-900 dark:border-gray-100 mx-auto"
		></div>
	</div>
</div>
