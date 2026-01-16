<script lang="ts">
	import { getContext } from 'svelte';

	import {
		user,
		showControls,
		showSidebar,
		suggestionCycle,
		config,
		showArchivedChats
	} from '$lib/stores';
	import { goto } from '$app/navigation';

	import ModelSelector from '../chat/ModelSelector.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import HelpMenu from './Help/HelpMenu.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import MenuLines from '../icons/MenuLines.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import QuestionMarkCircle from '../icons/QuestionMarkCircle.svelte';
	import GlobalLanguageSelector from '../common/GlobalLanguageSelector.svelte';
	import ShortcutsModal from '../chat/ShortcutsModal.svelte';
	import IssueModal from '../common/IssueModal.svelte';
	import SuggestionModal from '../common/SuggestionModal.svelte';
	import { init } from 'i18next';

	const i18n = getContext('i18n');

	export let initNewChat: Function;
	export let showSetDefault: boolean = true;

	export let chat;
	export let selectedModels;
	export let showModelSelector = true;

	// Help functionality
	let showShortcuts = false;
	let showIssue = false;
	let showSuggestion = false;

	$: SurveyUrl = $i18n.language === 'fr-CA' ? $config?.survey_url_fr : $config?.survey_url;
	$: DocsUrl = $i18n.language === 'fr-CA' ? $config?.docs_url_fr : $config?.docs_url;
	$: TrainingUrl = $i18n.language === 'fr-CA' ? $config?.training_url_fr : $config?.training_url;

	const handleNewChat = () => {
		suggestionCycle.update((n) => n + 1);
		initNewChat();
	};
</script>

<div class="sticky top-0 z-30 w-full px-1.5 py-1.5 -mb-8 flex items-center">
	<div
		class=" bg-gradient-to-b via-50% from-white via-white to-transparent dark:from-gray-900 dark:via-gray-900 dark:to-transparent pointer-events-none absolute inset-0 -bottom-7 z-[-1] blur"
	></div>

	<div class=" flex max-w-full w-full mx-auto px-1 pt-0.5 bg-transparent">
		<div class="flex items-center w-full max-w-full">
			<div
				class="{$showSidebar
					? 'md:hidden'
					: ''} mr-1 self-start flex flex-none items-center text-gray-600 dark:text-gray-400"
			>
				<button
					id="sidebar-toggle-button"
					class="cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition"
					on:click={() => {
						showSidebar.set(!$showSidebar);
					}}
					aria-label="Toggle Sidebar"
				>
					<div class=" m-auto self-center">
						<MenuLines />
					</div>
				</button>
			</div>

			<div
				class="flex-1 overflow-hidden max-w-full py-0.5
			{$showSidebar ? 'ml-1' : ''}
			"
			>
				{#if showModelSelector}
					<ModelSelector bind:selectedModels {showSetDefault} />
				{/if}
			</div>

			{#if !$showSidebar}
				<Tooltip content={$i18n.t('New Chat')}>
					<button
						id="new-chat-button"
						class="flex cursor-pointer p-2 rounded-xl text-gray-900 hover:bg-gray-50 dark:text-white dark:hover:bg-gray-850 transition"
						on:click={handleNewChat}
						aria-label="New Chat"
					>
						<div class="m-auto self-center">
							<PencilSquare className="size-5" strokeWidth="2" />
						</div>
					</button>
				</Tooltip>
			{/if}

			{#if $user && ($user.role === 'admin' || $user?.permissions?.chat?.controls)}
				<Tooltip content={$i18n.t('Controls')}>
					<button
						class="flex cursor-pointer px-2 py-2 rounded-xl text-gray-900 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
						on:click={async () => {
							await showControls.set(!$showControls);
						}}
						aria-label="Controls"
					>
						<div class="m-auto self-center">
							<AdjustmentsHorizontal className="size-5" strokeWidth="0.5" />
						</div>
					</button>
				</Tooltip>
			{/if}

			<div>
				<button
					id="show-shortcuts-button"
					class="hidden"
					on:click={() => {
						showShortcuts = !showShortcuts;
					}}
				/>
				<HelpMenu
					showDocsHandler={() => {
						window.open(DocsUrl, '_blank');
					}}
					showTrainingHandler={() => {
						window.open(TrainingUrl, '_blank');
					}}
					showShortcutsHandler={() => {
						showShortcuts = !showShortcuts;
					}}
					showSurveyHandler={() => {
						window.open(SurveyUrl, '_blank');
					}}
					showIssueHandler={() => {
						showIssue = true;
					}}
					showSuggestionHandler={() => {
						showSuggestion = true;
					}}
				>
					<Tooltip content={$i18n.t('Help')} placement="bottom">
						<div
							class="flex cursor-pointer p-2 rounded-xl text-gray-900 hover:bg-gray-50 dark:text-white dark:hover:bg-gray-850 transition"
						>
							<div class="m-auto self-center">
								<QuestionMarkCircle className="size-5" strokeWidth="2" />
							</div>
						</div>
					</Tooltip>
				</HelpMenu>
			</div>

			<GlobalLanguageSelector />

			{#if $user !== undefined}
				<div
					class="select-none flex rounded-xl p-2 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				>
					<UserMenu
						role={$user.role}
						on:show={(e) => {
							if (e.detail === 'archived-chat') {
								showArchivedChats.set(true);
							}
						}}
					>
						<img
							src={$user.profile_image_url}
							class="size-6 object-cover rounded-full"
							alt="User profile"
							draggable="false"
						/>
					</UserMenu>
				</div>
			{/if}
		</div>
	</div>
</div>
<ShortcutsModal bind:show={showShortcuts} />
<IssueModal bind:show={showIssue} />
<SuggestionModal bind:show={showSuggestion} />
