import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';

// Environment detection function
const getEnvironment = (hostname: string | undefined): string => {
	if (!hostname) return 'local';

	if (hostname.includes('prod')) return 'prod';
	if (hostname.includes('uat')) return 'uat';
	if (hostname.includes('dev')) return 'dev';

	return 'local';
};

export const POST: RequestHandler = async ({ request }) => {
	try {
		const formData = await request.formData();
		const email = formData.get('email') as string;
		const description = formData.get('description') as string;
		const username = formData.get('username') as string;
		const issueType = (formData.get('issueType') as string) || 'Bug';
		const stepsToReproduce = formData.get('stepsToReproduce') as string;

		// Get environment from HOSTNAME
		const environment = getEnvironment(env.HOSTNAME);

		// Log the report details for debugging
		console.log('Received incident report:', { email, username, description });

		const jiraApiUrl = env.JIRA_API_URL?.replace(/\/$/, '');
		const jiraUsername = env.JIRA_USERNAME;
		const jiraApiToken = env.JIRA_API_TOKEN;
		const jiraProjectKey = env.JIRA_PROJECT_KEY || 'CHAT';

		console.log('Jira config:', {
			apiUrl: jiraApiUrl ? 'set' : 'not set',
			username: jiraUsername ? 'set' : 'not set',
			token: jiraApiToken ? 'has token' : 'no token',
			projectKey: jiraProjectKey
		});

		if (!jiraApiUrl || !jiraUsername || !jiraApiToken) {
			throw new Error('Jira configuration is incomplete');
		}

		// Create Jira issue
		const jiraIssue = {
			fields: {
				project: {
					key: jiraProjectKey
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
${stepsToReproduce}
                    `
						: `
Environment: ${environment.toUpperCase()}
Reported by: ${username}
Email: ${email}

Suggestion:
${description}
                    `,
				issuetype: {
					name: issueType
				},
				labels: [issueType === 'Bug' ? 'client-issue' : 'client-suggestion', `env-${environment}`]
			}
		};

		// Create the full API URL with the correct path
		const jiraEndpoint = `${jiraApiUrl}/rest/api/2/issue`;
		console.log('Making request to:', jiraEndpoint);

		const base64Auth = Buffer.from(`${jiraUsername}:${jiraApiToken}`).toString('base64');
		const headers = {
			Authorization: `Basic ${base64Auth}`,
			Accept: 'application/json',
			'Content-Type': 'application/json'
		};

		const jiraResponse = await fetch(jiraEndpoint, {
			method: 'POST',
			headers,
			body: JSON.stringify(jiraIssue)
		});

		if (!jiraResponse.ok) {
			const errorText = await jiraResponse.text();
			console.error('Jira API error:', errorText);
			throw new Error(`Jira API error: ${jiraResponse.status} ${errorText}`);
		}

		const responseData = await jiraResponse.json();
		const issueKey = responseData.key;

		// Handle file attachments if present
		const files = formData.getAll('files');
		if (files.length > 0) {
			const attachmentEndpoint = `${jiraApiUrl}/rest/api/2/issue/${issueKey}/attachments`;

			for (const file of files) {
				if (file instanceof File) {
					const attachmentFormData = new FormData();
					attachmentFormData.append('file', file);

					await fetch(attachmentEndpoint, {
						method: 'POST',
						headers: {
							Authorization: `Basic ${base64Auth}`,
							'X-Atlassian-Token': 'no-check' // Required for file uploads
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
		console.error('Error creating Jira ticket:', error);
		return json(
			{
				success: false,
				error: error instanceof Error ? error.message : 'Failed to create Jira issue'
			},
			{
				status: 500
			}
		);
	}
};
