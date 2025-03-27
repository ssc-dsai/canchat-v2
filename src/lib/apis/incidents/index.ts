import { WEBUI_API_BASE_URL } from '$lib/constants';

type IncidentItem = {
	email: string;
	description: string;
	stepsToReproduce: string;
	files?: null | FileList;
};

export const createIncident = async (token: string, incident: IncidentItem) => {
	let error = null;
	const formData = new FormData();

	formData.append('email', incident.email);
	formData.append('description', incident.description);
	formData.append('stepsToReproduce', incident.stepsToReproduce);

	if (incident.files) {
		Array.from(incident.files).forEach((file) => {
			formData.append('files', file);
		});
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/incidents/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		},
		body: formData
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}
	return res;
};
