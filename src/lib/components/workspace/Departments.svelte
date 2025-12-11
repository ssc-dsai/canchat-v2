<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { getDomains } from '$lib/apis/metrics';
	import { getUserByDomain } from '$lib/apis/users';
	import { Chart, registerables } from 'chart.js';
	import { user } from '$lib/stores';
	import Spinner from '../common/Spinner.svelte';

	function formatDate(date: Date): string {
		return date.toISOString().split('T')[0];
	}

	function toEpoch(dateString: string): number {
		return Math.floor(new Date(dateString).getTime() / 1000);
	}

	// Handler for start date changes - ensures end date is always after start date
	function handleStartDateChange(event) {
		const newStartDate = event.target.value;
		console.log('Start date changed:', newStartDate);
		startDate = newStartDate;

		// If start date is after or equal to end date, adjust end date to be one day after start date
		if (newStartDate && endDate && new Date(newStartDate) >= new Date(endDate)) {
			const startDateObj = new Date(newStartDate);
			const newEndDate = new Date(startDateObj.getTime() + 24 * 60 * 60 * 1000);
			endDate = newEndDate.toISOString().split('T')[0];
			console.log('End date auto-adjusted:', endDate);
		}

		updateCharts(selectedDomain);
	}

	// Register all Chart.js components
	Chart.register(...registerables);
	const i18n = getContext('i18n') as any;
	let unsubscribe: () => void;
	let componentLoaded = false;

	// Data variables
	let domains: string[] = [];
	let selectedDomain: string | null = null;

	// Export functionality variables
	let isExporting = false;
	let exportLogs: any[] = [];
	let showExportLogs = false;

	// Chart objects
	let userByDepartmentChart: any;
	let activeUserByDepartmentChart: any;

	// Chart data
	let isLoadingChartData: boolean = false;
	let departmentUsageData: any[] = [];

	// For chart options
	const chartOptions = {
		responsive: true,
		maintainAspectRatio: false,
		plugins: {
			legend: {
				display: true,
				labels: {
					color: document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#1f2937'
				},
				onClick: null // Disable the default click behavior
			},
			tooltip: {
				mode: 'nearest',
				intersect: false
			}
		},
		scales: {
			x: {
				ticks: {
					color: document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#1f2937'
				},
				grid: {
					color: document.documentElement.classList.contains('dark')
						? 'rgba(255, 255, 255, 0.1)'
						: 'rgba(0, 0, 0, 0.1)'
				}
			},
			y: {
				beginAtZero: true,
				ticks: {
					color: document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#1f2937'
				},
				grid: {
					color: document.documentElement.classList.contains('dark')
						? 'rgba(255, 255, 255, 0.1)'
						: 'rgba(0, 0, 0, 0.1)'
				}
			}
		}
	};

	// Function to update chart theme colors
	function updateChartThemeColors() {
		const isDark = document.documentElement.classList.contains('dark');
		const textColor = isDark ? '#e5e7eb' : '#1f2937';
		const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

		// Update chart options
		chartOptions.plugins.legend.labels.color = textColor;
		chartOptions.scales.x.ticks.color = textColor;
		chartOptions.scales.x.grid.color = gridColor;
		chartOptions.scales.y.ticks.color = textColor;
		chartOptions.scales.y.grid.color = gridColor;

		// Update existing charts with new theme colors
		const charts = [userByDepartmentChart, activeUserByDepartmentChart];
		charts.forEach((chart) => {
			if (chart) {
				chart.options.plugins.legend.labels.color = textColor;
				chart.options.scales.x.ticks.color = textColor;
				chart.options.scales.x.grid.color = gridColor;
				chart.options.scales.y.ticks.color = textColor;
				chart.options.scales.y.grid.color = gridColor;
				chart.update();
			}
		});
	}

	// Update chart labels function
	function updateChartLabels() {
		if (userByDepartmentChart) {
			userByDepartmentChart.data.datasets[0].label = $i18n.t('Active Users');
			userByDepartmentChart.data.datasets[1].label = $i18n.t('Total Users');
			userByDepartmentChart.update();
		}
	}

	// Date range controls
	let dateRangeOptions = [
		{ value: '7days', label: $i18n.t('Last 7 Days') },
		{ value: '30days', label: $i18n.t('Last 30 Days') },
		{ value: '60days', label: $i18n.t('Last 60 Days') },
		{ value: '90days', label: $i18n.t('Last 90 Days') },
		{ value: 'custom', label: $i18n.t('Custom Range') }
	];
	let selectedDateRange = '7days';
	let startDate = new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
	let endDate = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().split('T')[0];
	let showCustomDateRange = false;

	// Helper function to calculate days between dates
	function calculateDaysFromDateRange(start, end) {
		if (start && end) {
			const startDate = new Date(start);
			const endDate = new Date(end);
			const epochStart = Math.floor(startDate.getTime() / 1000);
			const epochEnd = Math.floor(endDate.getTime() / 1000);
			return { epochStart, epochEnd };
		}
		return 7; // Default to 7 days
	}

	// Function to update all charts with new data
	async function updateCharts(selectedDomain: string | null) {
		// Don't update charts if either date is empty (from clearing date inputs)
		if (!startDate || !endDate) {
			return;
		}

		isLoadingChartData = true;
		try {
			let updatedDomain = selectedDomain ?? undefined;
			// Fetch historical data for charts
			departmentUsageData = await getUserByDomain(
				localStorage.token,
				toEpoch(startDate),
				toEpoch(endDate),
				updatedDomain
			);
			// Initialize charts with the data
			setTimeout(() => {
				initializeCharts();
			}, 50);
		} catch (error) {
			console.error('Error updating charts:', error);
		} finally {
			isLoadingChartData = false;
		}
	}

	// Initialize charts function
	function initializeCharts() {
		// Users chart - for both overview and users tabs
		// Enrolled Users Chart
		const enrolledChartId = 'userEnrollmentsOverTimeChart';
		const enrolledCanvas = document.getElementById(enrolledChartId);
		const enrolledCtx = enrolledCanvas?.getContext('2d');
		if (enrolledCtx) {
			if (userByDepartmentChart) {
				userByDepartmentChart.destroy();
			}

			// Calculate dynamic height: 60px per department + padding
			const chartHeight = Math.max(300, departmentUsageData.length * 80);
			if (enrolledCanvas) {
				enrolledCanvas.style.height = `${chartHeight}px`;
			}

			userByDepartmentChart = new Chart(enrolledCtx, {
				type: 'bar',
				data: {
					labels: departmentUsageData.map((item) => item.department),
					datasets: [
						{
							label: '',
							data: departmentUsageData.map((item) => item.active_users),
							borderColor: 'rgba(255, 99, 132, 0.5)',
							backgroundColor: 'rgba(255, 99, 132, 0.5)',
							borderWidth: 2
						},
						{
							label: '',
							data: departmentUsageData.map((item) => item.total_users),
							borderColor: 'rgba(54, 162, 235, 0.5)',
							backgroundColor: 'rgba(54, 162, 235, 0.5)',
							borderWidth: 2
						}
					]
				},
				options: {
					...chartOptions,
					indexAxis: 'y'
					// maintainAspectRatio: false
				}
			});
			// Set translated labels after chart creation
			updateChartLabels();
		}
	}

	function handleDateRangeChange(event) {
		const range = event.target.value;
		selectedDateRange = range;

		const today = new Date();
		const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000);

		if (range === '7days') {
			startDate = formatDate(new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000));
			endDate = formatDate(tomorrow);
			showCustomDateRange = false;
		} else if (range === '30days') {
			startDate = formatDate(new Date(today.getTime() - 29 * 24 * 60 * 60 * 1000));
			endDate = formatDate(tomorrow);
			showCustomDateRange = false;
		} else if (range === '60days') {
			startDate = formatDate(new Date(today.getTime() - 59 * 24 * 60 * 60 * 1000));
			endDate = formatDate(tomorrow);
			showCustomDateRange = false;
		} else if (range === '90days') {
			startDate = formatDate(new Date(today.getTime() - 89 * 24 * 60 * 60 * 1000));
			endDate = formatDate(tomorrow);
			showCustomDateRange = false;
		} else if (range === 'custom') {
			showCustomDateRange = true;
			// Set sensible defaults for custom range (last 7 days including today)
			startDate = formatDate(new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000));
			endDate = formatDate(tomorrow);
		}
		console.log('Date range changed to:', range, { startDate, endDate });
		updateCharts(selectedDomain);
	}

	async function updateUserCount() {
		// Don't make API calls if either date is empty (from clearing date inputs)
		if (!startDate || !endDate) {
			return;
		}

		console.log('updateUserCount called with:', {
			startDate,
			endDate,
			startEpoch: toEpoch(startDate),
			endEpoch: toEpoch(endDate),
			selectedDomain
		});
		console.log('userByDepartmentData:', departmentUsageData);

		try {
			await updateCharts(selectedDomain);
		} catch (error) {
			console.error('Error fetching department users:', error);
		}
	}

	onMount(() => {
		// Subscribe to language changes
		unsubscribe = i18n.subscribe(() => {
			updateChartLabels();
		});

		// Add theme change observer
		const observer = new MutationObserver((mutations) => {
			mutations.forEach((mutation) => {
				if (
					mutation.type === 'attributes' &&
					mutation.attributeName === 'class' &&
					mutation.target === document.documentElement
				) {
					updateChartThemeColors();
				}
			});
		});

		observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class']
		});

		// Run async initialization
		(async () => {
			try {
				domains = await getDomains(localStorage.token);
				await updateCharts(selectedDomain);
				componentLoaded = true;
			} catch (error) {
				console.error('Error initializing charts:', error);
				componentLoaded = true;
			}
		})();

		// Return cleanup function synchronously
		return () => {
			observer.disconnect();
		};
	});

	onDestroy(() => {
		// Clean up subscription when component is destroyed
		if (unsubscribe) {
			unsubscribe();
		}

		// Clean up charts
		if (userByDepartmentChart) userByDepartmentChart.destroy();
		if (activeUserByDepartmentChart) activeUserByDepartmentChart.destroy();
	});

	// Update domain change handler to simplify
	function handleDomainChange(event: Event) {
		const newDomain = (event.target as HTMLSelectElement).value || null;
		selectedDomain = newDomain;
		updateCharts(selectedDomain);
	}

	// Export functionality

	async function handleExportData() {
		// Validate that we have valid dates
		if (!startDate || !endDate) {
			alert($i18n.t('Please select both start and end dates'));
			return;
		}

		// Check if start and end dates are the same
		if (startDate === endDate) {
			alert(
				$i18n.t(
					'Start and end dates cannot be the same. Please select a date range of at least one day.'
				)
			);
			return;
		}

		// Check if date range exceeds 90 days (using same logic as backend)
		const start = new Date(startDate);
		const end = new Date(endDate);
		const diffDays = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1; // +1 to include both start and end days

		if (diffDays > 90) {
			alert($i18n.t('Date range cannot exceed 90 days. Please select a shorter range.'));
			return;
		}

		// isExporting = true;
		// try {
		// 	const blob = await exportMetricsData(localStorage.token, startDate, endDate, exportDomain);

		// 	// Create download link
		// 	const url = window.URL.createObjectURL(blob);
		// 	const a = document.createElement('a');
		// 	a.href = url;
		// 	a.download = `metrics_export_${startDate}_to_${endDate}.csv`;
		// 	document.body.appendChild(a);
		// 	a.click();
		// 	window.URL.revokeObjectURL(url);
		// 	document.body.removeChild(a);

		// 	// Refresh export logs (for admin, global_analyst, and analyst users)
		// 	if (
		// 		$user?.role === 'admin' ||
		// 		$user?.role === 'global_analyst' ||
		// 		$user?.role === 'analyst'
		// 	) {
		// 		await loadExportLogs();
		// 	}
		// } catch (error) {
		// 	console.error('Export failed:', error);
		// 	alert($i18n.t('Export failed. Please try again.'));
		// } finally {
		// 	isExporting = false;
		// }
	}

	// async function loadExportLogs() {
	// 	try {
	// 		exportLogs = await getExportLogs(localStorage.token);
	// 	} catch (error) {
	// 		console.error('Failed to load export logs:', error);
	// 	}
	// }

	// function openExportLogs() {
	// 	showExportLogs = true;
	// 	loadExportLogs();
	// }

	// function closeExportLogs() {
	// 	showExportLogs = false;
	// }

	// Check if user can export (admin, global_analyst, or analyst)
	$: canExport = $user?.role === 'admin' || $user?.role === 'global_analyst';
</script>

{#if componentLoaded && $user}
	<div class="flex flex-col h-screen">
		<div class="p-4 lg:p-6 flex-shrink-0">
			<div class="mb-4 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
				<h2 class="text-2xl font-extrabold text-gray-900 dark:text-gray-100">
					{$i18n.t('Department Usage Dashboard')}
				</h2>
				<!-- Date Range Controls -->
				<div class="flex flex-wrap items-center gap-3">
					<div>
						<label
							class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
							for="date-range-select"
						>
							{$i18n.t('Date Range')}
						</label>
						<select
							id="date-range-select"
							bind:value={selectedDateRange}
							on:change={handleDateRangeChange}
							class="block w-36 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
						>
							{#each dateRangeOptions as option}
								<option value={option.value}>{$i18n.t(option.label)}</option>
							{/each}
						</select>
					</div>
					{#if showCustomDateRange}
						<div>
							<label
								class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
								for="start-date"
							>
								{$i18n.t('Start Date')}
							</label>
							<input
								type="date"
								id="start-date"
								bind:value={startDate}
								max={formatDate(new Date(Date.now() - 24 * 60 * 60 * 1000))}
								required
								on:change={handleStartDateChange}
								class="block w-40 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
							/>
						</div>
						<div>
							<label
								class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
								for="end-date"
							>
								{$i18n.t('End Date')}
							</label>
							<input
								type="date"
								id="end-date"
								bind:value={endDate}
								max={formatDate(new Date())}
								min={startDate}
								required
								on:change={() => updateCharts(selectedDomain)}
								class="block w-40 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
							/>
						</div>
					{/if}
					<!-- Domain Selector with better visibility for analyst's domain -->
					<div>
						<label
							class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
							for="domain-select"
						>
							{$i18n.t('Select Domain:')}
						</label>
						<select
							id="domain-select"
							bind:value={selectedDomain}
							on:change={(e) => {
								handleDomainChange(e);
							}}
							class="block w-36 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
						>
							<option value={null}>{$i18n.t('All')}</option>
							{#each domains as domain}
								<option value={domain}>
									{domain}
								</option>
							{/each}
						</select>
					</div>
					{#if canExport}
						<div class="flex flex-col">
							<div class="flex items-center gap-2 mt-6">
								<button
									on:click={handleExportData}
									disabled={isExporting || !startDate || !endDate}
									title="Export raw message metrics data including tokens, timestamps, and user information in CSV format"
									class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white text-sm font-medium rounded-md transition-colors duration-200 flex items-center gap-2"
								>
									{#if isExporting}
										<svg
											class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
										>
											<circle
												class="opacity-25"
												cx="12"
												cy="12"
												r="10"
												stroke="currentColor"
												stroke-width="4"
											></circle>
											<path
												class="opacity-75"
												fill="currentColor"
												d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
											></path>
										</svg>
										{$i18n.t('Exporting...')}
									{:else}
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
											/>
										</svg>
										{$i18n.t('Export Raw Data')}
									{/if}
								</button>
								{#if $user?.role === 'admin'}
									<button
										class="px-3 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium rounded-md transition-colors duration-200 flex items-center gap-2"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
											/>
										</svg>
										{$i18n.t('View Exports')}
									</button>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<div class="grid grid-cols-1 gap-6 mb-6">
				{#if isLoadingChartData}
					<div class="flex flex-col items-center text-center space-y-3">
						<Spinner className="size-8" />
						<div class="text-lg font-semibold dark:text-gray-200">
							{$i18n.t('Loading department users...')}
						</div>
					</div>
				{:else}
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Department Users Over Time')}
						</h5>
						<div>
							<canvas id="userEnrollmentsOverTimeChart"></canvas>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<!-- Export Logs Modal -->
	{#if showExportLogs}
		<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
			<div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-4xl mx-4 max-h-96">
				<div class="flex justify-between items-center mb-4">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
						{$i18n.t('Export History')}
					</h3>
					<button
						on:click={closeExportLogs}
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
					>
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					</button>
				</div>

				<div class="overflow-y-auto max-h-64">
					{#if exportLogs.length > 0}
						<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
							<thead
								class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400"
							>
								<tr>
									<th class="px-4 py-2">{$i18n.t('User')}</th>
									<th class="px-4 py-2">{$i18n.t('Domain')}</th>
									<th class="px-4 py-2">{$i18n.t('Export Date')}</th>
									<th class="px-4 py-2">{$i18n.t('Date Range')}</th>
									<th class="px-4 py-2">{$i18n.t('Records')}</th>
									<th class="px-4 py-2">{$i18n.t('File Size')}</th>
								</tr>
							</thead>
							<tbody>
								{#each exportLogs as log}
									<tr class="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
										<td class="px-4 py-2 font-medium text-gray-900 dark:text-white">
											{log.user_id}
										</td>
										<td class="px-4 py-2">{log.email_domain}</td>
										<td class="px-4 py-2">
											{new Date(log.export_timestamp * 1000).toLocaleDateString()}
										</td>
										<td class="px-4 py-2">
											{new Date(log.date_range_start * 1000).toLocaleDateString()} - {new Date(
												log.date_range_end * 1000
											).toLocaleDateString()}
										</td>
										<td class="px-4 py-2">{log.row_count.toLocaleString()}</td>
										<td class="px-4 py-2">{(log.file_size / 1024).toFixed(1)} KB</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{:else}
						<div class="text-center py-8 text-gray-500 dark:text-gray-400">
							{$i18n.t('No export history found')}
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
{:else}
	<div class="flex justify-center items-center h-64">
		<div class="text-gray-500 dark:text-gray-400">
			{$i18n.t('Loading metrics...')}
		</div>
	</div>
{/if}
