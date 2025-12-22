<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import Departments from '$lib/components/workspace/Departments.svelte';

	// Check if user has department usage access based on role
	$: hasDepartmentUsageAccess = $user?.role === 'admin' || $user?.role === 'global_analyst';

	onMount(async () => {
		// Wait for user data to be loaded before making navigation decisions
		if (!$user) {
			// If no user data, wait a bit and try again or redirect to login
			setTimeout(() => {
				if (!$user || !hasDepartmentUsageAccess) {
					goto('/');
				}
			}, 100);
			return;
		}

		// Redirect to home if user doesn't have department usage access
		if (!hasDepartmentUsageAccess) {
			await goto('/');
		}
	});
</script>

{#if hasDepartmentUsageAccess}
	<Departments />
{/if}
