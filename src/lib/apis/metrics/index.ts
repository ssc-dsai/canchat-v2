import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getTotalUsers = async (token: string, domain: string): Promise<number> => {
	try {
		if (!domain) {
			throw new Error('Domain is required');
		}
		const encodedDomain = encodeURIComponent(domain);
		const url = domain === '*' ? '/metrics/users' : '/metrics/users/' + encodedDomain;
		const res = await fetch(`${WEBUI_API_BASE_URL + url}`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get Users'}`);
		}
		const data = await res.json();
		return data.total_users;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getDomains = async (token: string): Promise<string[]> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/metrics/domains`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get domains'}`);
		}
		const data = await res.json();
		return data.domains;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};

export const getDailyActiveUsers = async (token: string, domain: string): Promise<number> => {
	try {
		if (!domain) {
			throw new Error('Domain is required');
		}
		const encodedDomain = encodeURIComponent(domain);
		const url = domain === '*' ? '/metrics/daily/users' : '/metrics/daily/users/' + encodedDomain;
		const res = await fetch(`${WEBUI_API_BASE_URL + url}`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(`Error ${res.status}: ${error.detail || 'Failed to get Users'}`);
		}
		const data = await res.json();
		return data.daily_active_users;
	} catch (err) {
		throw new Error(err.message || 'An unexpected error occurred');
	}
};
