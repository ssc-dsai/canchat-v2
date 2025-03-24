import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { getConfig } from '$lib/server/config';

const getEnvironment = (hostname: string | undefined): string => {
	if (!hostname) return 'local';
	if (hostname.includes('prod')) return 'prod';
	if (hostname.includes('uat')) return 'uat';
	if (hostname.includes('dev')) return 'dev';
	return 'local';
};

export const POST: RequestHandler = async ({ request }) => {
	try {
		const config = getConfig();
		if (!config.jira.apiUrl || !config.jira.username || !config.jira.apiToken) {
			throw new Error('Jira configuration is incomplete');
		}

		const formData = await request.formData();
		const email = formData.get('email') as string;
		const description = formData.get('description') as string;
		const username = formData.get('username') as string;
		const issueType = (formData.get('issueType') as string) || 'Bug';
		const stepsToReproduce = formData.get('stepsToReproduce') as string;

		const environment = getEnvironment(config.hostname);

		const jiraEndpoint = `${config.jira.apiUrl.replace(/\/$/, '')}/rest/api/2/issue`;
		const base64Auth = Buffer.from(`${config.jira.username}:${config.jira.apiToken}`).toString(
			'base64'
		);

		const jiraIssue = {
			fields: {
				project: {
					key: config.jira.projectKey
				},
				summary: `[${environment.toUpperCase()}] ${issueType === 'Bug' ? 'Issue' : 'Suggestion'} from ${username}`,
				description:
					issueType === 'Bug'
						? `
Environment: ${environment.toUpperCase()}
Reported by: ${username}
Email: ${email}

Description:
${description}

Steps to Reproduce:
${stepsToReproduce}`
						: `
Environment: ${environment.toUpperCase()}
Reported by: ${username}
Email: ${email}

Suggestion:
${description}`,
				issuetype: {
					name: issueType
				},
				labels: [issueType === 'Bug' ? 'client-issue' : 'client-suggestion', `env-${environment}`]
			}
		};

		const jiraResponse = await fetch(jiraEndpoint, {
			method: 'POST',
			headers: {
				Authorization: `Basic ${base64Auth}`,
				Accept: 'application/json',
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(jiraIssue)
		});

		if (!jiraResponse.ok) {
			const errorText = await jiraResponse.text();
			throw new Error(`Jira API error: ${jiraResponse.status} ${errorText}`);
		}

		const responseData = await jiraResponse.json();
		const issueKey = responseData.key;

		// Handle file attachments if present
		const files = formData.getAll('files');
		if (files.length > 0) {
			const attachmentEndpoint = `${config.jira.apiUrl.replace(/\/$/, '')}/rest/api/2/issue/${issueKey}/attachments`;

			for (const file of files) {
				if (file instanceof File) {
					const attachmentFormData = new FormData();
					attachmentFormData.append('file', file);

					await fetch(attachmentEndpoint, {
						method: 'POST',
						headers: {
							Authorization: `Basic ${base64Auth}`,
							'X-Atlassian-Token': 'no-check'
						},
						body: attachmentFormData
					});
				}
			}
		}

		return json({
			success: true,
			ticketId: issueKey,
			message: `Issue created in Jira: ${issueKey}`
		});
	} catch (error) {
		return json(
			{
				success: false,
				error: error instanceof Error ? error.message : 'Failed to create Jira issue'
			},
			{ status: 500 }
		);
	}
};
