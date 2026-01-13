<script lang="ts">
	import { onMount } from 'svelte';
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import { config } from '$lib/stores';

	let emergencyMessage = {
		enabled: false,
		content: ''
	};

	$: if ($config?.emergency_message) {
		emergencyMessage = $config.emergency_message;
	}
</script>

{#if emergencyMessage.enabled && emergencyMessage.content}
	<div
		class="fixed top-0 left-0 right-0 bg-red-600 text-white px-4 py-2.5 shadow-lg z-[60]"
		role="alert"
	>
		<div class="max-w-full mx-auto flex items-start gap-3">
			<div class="flex-shrink-0 mt-0.5">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					class="w-5 h-5"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
					/>
				</svg>
			</div>
			<div class="flex-1 emergency-message-content text-sm">
				{@html marked.parse(DOMPurify.sanitize(emergencyMessage.content))}
			</div>
		</div>
	</div>
{/if}

<style>
	:global(.emergency-message-content p) {
		margin: 0;
		line-height: 1.5;
	}

	:global(.emergency-message-content a) {
		color: #60a5fa !important;
		text-decoration: underline;
		font-weight: 600;
	}

	:global(.emergency-message-content a:hover) {
		text-decoration: none;
	}

	:global(.emergency-message-content strong) {
		font-weight: 700;
	}

	:global(.emergency-message-content em) {
		font-style: italic;
	}

	:global(.emergency-message-content ul),
	:global(.emergency-message-content ol) {
		margin-left: 1.5rem;
	}

	:global(.emergency-message-content li) {
		margin: 0.25rem 0;
	}
</style>
