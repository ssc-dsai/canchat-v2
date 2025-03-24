import { env } from '$env/dynamic/private';

export interface Config {
	hostname: string;
	jira: {
		apiUrl: string;
		username: string;
		apiToken: string;
		projectKey: string;
	};
}

export function getConfig(): Config {
	return {
		hostname: env.HOSTNAME || 'localhost',
		jira: {
			apiUrl: env.JIRA_API_URL || '',
			username: env.JIRA_USERNAME || '',
			apiToken: env.JIRA_API_TOKEN || '',
			projectKey: env.JIRA_PROJECT_KEY || 'CHAT'
		}
	};
}
