<script lang="ts">
	import { onMount } from 'svelte';
	import Chart from 'chart.js/auto';
	import { getDailyActiveUsers, getDomains, getTotalUsers } from '$lib/apis/metrics';

	let domains: string[] = [];
	let totalUsers: number = 0, totalPrompts: number = 0, totalCosts: number = 0, dailyUsers: number = 0, dailyPrompts: number = 0, dailyCosts: number = 0;
	let selectedDomain = '*';
	let dailyActiveUsersChart, dailyPromptsChart, dailyCostsChart;

	let dailyActiveUsersData = {}; // Replace with actual data
	let dailyPromptsData = {}; // Replace with actual data
	let dailyCostsData = {}; // Replace with actual data

	async function updateCharts(selectedDomain: string) {
		totalUsers = await getTotalUsers(localStorage.token, selectedDomain);
		// totalPrompts = await getTotalPrompts(localStorage.token, selectedDomain);
		// totalCosts = await getTotalCosts(localStorage.token, selectedDomain);
		dailyUsers = await getDailyActiveUsers(localStorage.token, selectedDomain);
		// dailyPrompts = await getDailyPrompts(localStorage.token, selectedDomain);
		// dailyCosts = await getDailyCosts(localStorage.token, selectedDomain);
		// dailyActiveUsersData = await getDailyActiveUsersData(localStorage.token, selectedDomain);
		// dailyPromptsData = await getDailyPromptsData(localStorage.token, selectedDomain);
		// dailyCostsData = await getDailyCostsData(localStorage.token, selectedDomain);
	}

	onMount(async () => {
		domains = await getDomains(localStorage.token);
		updateCharts(selectedDomain);

		const ctx1 = document.getElementById('dailyActiveUsersChart').getContext('2d');
		dailyActiveUsersChart = new Chart(ctx1, {
			type: 'line',
			data: {
				labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'], // Updated to 7 days
				datasets: [
					{
						label: 'Daily Active Users',
						data: dailyActiveUsersData[selectedDomain] || [],
						borderColor: 'blue',
						borderWidth: 1
					}
				]
			}
		});

		const ctx2 = document.getElementById('dailyPromptsChart').getContext('2d');
		dailyPromptsChart = new Chart(ctx2, {
			type: 'line',
			data: {
				labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'], // Updated to 7 days
				datasets: [
					{
						label: 'Daily Prompts Sent',
						data: dailyPromptsData[selectedDomain] || [],
						borderColor: 'green',
						borderWidth: 1
					}
				]
			}
		});

		const ctx3 = document.getElementById('dailyCostsChart').getContext('2d');
		dailyCostsChart = new Chart(ctx3, {
			type: 'line',
			data: {
				labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'], // Updated to 7 days
				datasets: [
					{
						label: 'Daily Costs',
						data: dailyCostsData[selectedDomain] || [],
						borderColor: 'red',
						borderWidth: 1
					}
				]
			}
		});

	});
</script>

<div class="container mx-auto p-6">
	<div class="mb-4 flex justify-between items-center">
		<h2 class="text-3xl font-extrabold text-gray-900 dark:text-gray-100">Metrics Dashboard</h2>
		<div>
			<label
				for="domain-select"
				class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
				>Select Domain:</label
			>
			<select
				id="domain-select"
				bind:value={selectedDomain}
				on:change={(event) => updateCharts(event.target.value)}
				class="block w-48 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
			>
				<option value="*">All</option>
				{#each domains as domain}
					<option value={domain}>{domain}</option>
				{/each}
			</select>
		</div>
	</div>

	<div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">Total Users</h5>
			<h4 class="text-3xl font-bold text-blue-700 dark:text-blue-400">{totalUsers}</h4>
			<p class="text-sm text-gray-600 dark:text-gray-400 mt-2">Across all domains</p>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">Total Prompts</h5>
			<h4 class="text-3xl font-bold text-green-700 dark:text-green-400">{totalPrompts}</h4>
			<p class="text-sm text-gray-600 dark:text-gray-400 mt-2">Currently active</p>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">Total Costs</h5>
			<h4 class="text-3xl font-bold text-red-700 dark:text-red-400">${totalCosts}</h4>
			<p class="text-sm text-gray-600 dark:text-gray-400 mt-2">Incurred so far</p>
		</div>
	</div>

	<div class="mb-10">
		<div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
			<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
				<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">Daily Users</h5>
				<h4 class="text-3xl font-bold text-blue-700 dark:text-blue-400">{dailyUsers}</h4>
				<p class="text-sm text-gray-600 dark:text-gray-400 mt-2">Across all domains</p>
			</div>
			<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
				<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">Daily Prompts</h5>
				<h4 class="text-3xl font-bold text-green-700 dark:text-green-400">{dailyPrompts}</h4>
				<p class="text-sm text-gray-600 dark:text-gray-400 mt-2">Currently active</p>
			</div>
			<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
				<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">Daily Costs</h5>
				<h4 class="text-3xl font-bold text-red-700 dark:text-red-400">${dailyCosts}</h4>
				<p class="text-sm text-gray-600 dark:text-gray-400 mt-2">Incurred so far</p>
			</div>
		</div>
	</div>

	<hr class="border-gray-400 dark:border-gray-600 my-8" />

	<div class="space-y-8">
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
				Daily Active Users
				<span class="text-sm font-medium text-green-600 dark:text-green-400 ml-2">+5%</span>
			</h5>
			<canvas id="dailyActiveUsersChart" height="50"></canvas>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
				Daily Prompts Sent
				<span class="text-sm font-medium text-red-600 dark:text-red-400 ml-2">-3%</span>
			</h5>
			<canvas id="dailyPromptsChart" height="50"></canvas>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
				Daily Prompts Costs
				<span class="text-sm font-medium text-green-600 dark:text-green-400 ml-2">+2%</span>
			</h5>
			<canvas id="dailyCostsChart" height="50"></canvas>
		</div>
	</div>
</div>
