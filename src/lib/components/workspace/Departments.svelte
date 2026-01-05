<script lang="ts">
	import { MultiSelect } from 'svelte-multiselect';
	import { getContext, onMount, onDestroy } from 'svelte';
	import { getDomains } from '$lib/apis/metrics';
	import { getUserByDomain } from '$lib/apis/users';
	import { Chart, registerables } from 'chart.js';
	import { user } from '$lib/stores';
	import Spinner from '../common/Spinner.svelte';
	import ChartDataLabels from 'chartjs-plugin-datalabels';

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

		updateCharts(selectedDomains);
	}

	// Register all Chart.js components
	Chart.register(...registerables, ChartDataLabels);
	const i18n = getContext('i18n') as any;
	let unsubscribe: () => void;
	let componentLoaded = false;

	// Data variables
	let domains: string[] = [];
	let selectedDomains: string[] = [];

	// Chart objects
	let userByDepartmentChart: any;

	// Chart data
	let isLoadingChartData: boolean = false;
	let departmentUsageData: any[] = [];

	const chartOptions = {
		responsive: true,
		maintainAspectRatio: false,
		plugins: {
			legend: {
				display: true,
				labels: {
					color: document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#1f2937',
					font: { size: 14 }
				},
				onClick: null // Disable the default click behavior
			},
			tooltip: {
				mode: 'nearest',
				intersect: true,
				titleFont: { size: 14 },
				bodyFont: { size: 14 }
			},
			datalabels: {
				display: true,
				color: document.documentElement.classList.contains('dark') ? '#ffffff' : '#1f2937',
				anchor: 'center',
				align: 'center',
				offset: -4,
				formatter: (value) => (value === 0 ? null : value),
				font: {
					weight: 'bold',
					size: 14
				}
			}
		},
		scales: {
			x: {
				ticks: {
					color: document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#1f2937',
					font: { size: 14 }
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
					color: document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#1f2937',
					font: { size: 14 }
				},
				grid: {
					color: document.documentElement.classList.contains('dark')
						? 'rgba(255, 255, 255, 0.1)'
						: 'rgba(0, 0, 0, 0.1)'
				}
			}
		},
		hover: {
			mode: 'nearest',
			intersect: true
		}
	};

	function updateChartThemeColors() {
		const isDark = document.documentElement.classList.contains('dark');
		const textColor = isDark ? '#e5e7eb' : '#1f2937';
		const labelColor = isDark ? '#ffffff' : '#1f2937';
		const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

		// Update chart options
		chartOptions.plugins.legend.labels.color = textColor;
		chartOptions.plugins.datalabels.color = labelColor;
		// Ensure font sizes are consistent
		chartOptions.plugins.legend.labels.font = { size: 14 };
		chartOptions.plugins.datalabels.font = { weight: 'bold', size: 14 };
		chartOptions.plugins.tooltip = chartOptions.plugins.tooltip || {};
		chartOptions.plugins.tooltip.titleFont = { size: 14 };
		chartOptions.plugins.tooltip.bodyFont = { size: 14 };
		chartOptions.scales.x.ticks.color = textColor;
		chartOptions.scales.x.ticks.font = { size: 14 };
		chartOptions.scales.x.grid.color = gridColor;
		chartOptions.scales.y.ticks.color = textColor;
		chartOptions.scales.y.ticks.font = { size: 14 };
		chartOptions.scales.y.grid.color = gridColor;

		// Update existing charts with new theme colors
		const charts = [userByDepartmentChart];
		charts.forEach((chart) => {
			if (chart) {
				chart.options.plugins.datalabels.color = labelColor;
				if (!chart.options.plugins.datalabels.font) chart.options.plugins.datalabels.font = {};
				chart.options.plugins.datalabels.font.size = 14;
				chart.options.plugins.legend.labels.color = textColor;
				chart.options.plugins.legend.labels.font = { size: 14 };
				chart.options.scales.x.ticks.color = textColor;
				chart.options.scales.x.ticks.font = { size: 14 };
				chart.options.scales.x.grid.color = gridColor;
				chart.options.scales.y.ticks.color = textColor;
				chart.options.scales.y.ticks.font = { size: 14 };
				chart.options.scales.y.grid.color = gridColor;
				chart.options.plugins.tooltip = chart.options.plugins.tooltip || {};
				chart.options.plugins.tooltip.titleFont = { size: 14 };
				chart.options.plugins.tooltip.bodyFont = { size: 14 };
				chart.update();
			}
		});
	}

	function updateChartLabels() {
		if (userByDepartmentChart) {
			userByDepartmentChart.data.datasets[0].label = $i18n.t('Active Users');
			userByDepartmentChart.data.datasets[1].label = $i18n.t('Total Users');
			userByDepartmentChart.update();
		}
	}

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

	async function updateCharts(selectedDomain: string[]) {
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

	function initializeCharts() {
		const departmentChartId = 'departmentUsageChart';
		const departmentCanvas = document.getElementById(departmentChartId);
		const departmentCtx = departmentCanvas?.getContext('2d');
		if (departmentCtx) {
			if (userByDepartmentChart) {
				userByDepartmentChart.destroy();
			}

			// Calculate dynamic height: 60px per department + padding
			const chartHeight = Math.max(300, departmentUsageData.length * 100);
			if (departmentCanvas) {
				departmentCanvas.style.height = `${chartHeight}px`;
			}

			userByDepartmentChart = new Chart(departmentCtx, {
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
		updateCharts(selectedDomains);
	}

	onMount(() => {
		unsubscribe = i18n.subscribe(() => {
			updateChartLabels();
		});

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

		(async () => {
			try {
				domains = await getDomains(localStorage.token);
				await updateCharts(selectedDomains);
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
	});

	function handleDomainChange(event) {
		const changeType = event.detail.type;
		const newDomain = event.detail.option || null;
		const allLabel = $i18n.t('All');

		if (changeType === 'remove') {
			selectedDomains = selectedDomains.filter((domain) => domain !== newDomain);
		} else if (changeType === 'removeAll') {
			selectedDomains = [];
		} else if (changeType === 'add') {
			// If "All" is selected, populate all domains
			if (newDomain === allLabel) {
				selectedDomains = [...domains];
			} else if (!selectedDomains.includes(newDomain)) {
				selectedDomains = [...selectedDomains, newDomain];
			}
		}

		// Filter out "All" before sending to API
		const domainsToSend = selectedDomains.filter((d) => d !== allLabel);
		updateCharts(domainsToSend.length > 0 ? domainsToSend : selectedDomains);
	}
</script>

{#if componentLoaded && $user}
	<div class="flex flex-col h-screen">
		<div class="p-4 lg:p-6 flex-shrink-0">
			<div class="mb-4 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
				<h2 class="text-2xl min-w-[320px] font-extrabold text-gray-900 dark:text-gray-100">
					{$i18n.t('Department Usage Dashboard')}
				</h2>

				<div class="flex flex-nowrap items-center gap-3">
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
								on:change={() => updateCharts(selectedDomains)}
								class="block w-40 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
							/>
						</div>
					{/if}

					<div>
						<label
							class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
							for="domain-select"
						>
							{$i18n.t('Select Domain:')}
						</label>
						<div class="ms-wrapper">
							<MultiSelect
								bind:selected={selectedDomains}
								options={[$i18n.t('All'), ...domains]}
								allowUserOptions="append"
								placeholder={$i18n.t('Domains')}
								style="min-height: 36px; width: 100%;"
								on:change={(e) => {
									handleDomainChange(e);
								}}
							/>
						</div>
					</div>
				</div>
			</div>

			<div class="grid grid-cols-1 gap-6 mb-6">
				{#if isLoadingChartData}
					<div class="flex flex-col items-center text-center space-y-3">
						<Spinner className="size-8" />
						<div class="text-lg font-semibold dark:text-gray-200">
							{$i18n.t('Loading department usage...')}
						</div>
					</div>
				{:else}
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Department Users Over Time')}
						</h5>
						<div>
							<canvas id="departmentUsageChart"></canvas>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
{:else}
	<div class="flex justify-center items-center h-64">
		<div class="text-gray-500 dark:text-gray-400">
			{$i18n.t('Loading department usage...')}
		</div>
	</div>
{/if}

<style>
	/* MultiSelect styles */
	.ms-wrapper {
		border-width: 1px;
		border-color: rgba(180, 180, 180, 1);
		border-radius: 0.375rem;
	}
	:global(.dark) .ms-wrapper {
		background-color: var(--color-gray-800, #333);
		border-color: #4b5563;
	}

	/* MultiSelect dropdown options list */
	:global(.dark .multiselect > ul) {
		background-color: var(--color-gray-800, #333) !important;
		border-color: #4b5563 !important;
	}
</style>
