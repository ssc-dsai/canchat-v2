import axiosInstance from '$lib/axiosInstance';
import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getGravatarUrl = async (email: string) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_URL}/utils/gravatar?email=${email}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		}
	})
		.then(async (res) => {
			return res.data
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	return res;
};

export const formatPythonCode = async (code: string) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_URL}/utils/code/format`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		data: {
			code: code
		}})
		.then(async (res) => {
			return res.data
		})
		.catch((err) => {
			console.log(err);

			error = err;
			if (err.detail) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const downloadChatAsPDF = async (title: string, messages: object[]) => {
	let error = null;

	const blob = await axiosInstance(`${WEBUI_API_BASE_URL}/utils/pdf`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		data: {
			title: title,
			messages: messages
		}})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	return blob;
};

export const getHTMLFromMarkdown = async (md: string) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_URL}/utils/markdown`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		data: {
			md: md
		}})
		.then(async (res) => {
			return res.data
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	return res.html;
};

export const downloadDatabase = async (token: string) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_URL}/utils/db/download`, {
		method: 'GET',
		responseType: 'blob'
	})
		.then(async (response) => {
			return response.data
		})
		.then((blob) => {
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'webui.db';
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}
};

export const downloadLiteLLMConfig = async (token: string) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_URL}/utils/litellm/config`, {
		method: 'GET',
		responseType: 'blob'
	})
		.then(async (response) => {
			return response.data;
		})
		.then((blob) => {
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'config.yaml';
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}
};
