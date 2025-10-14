import axiosInstance from '$lib/axiosInstance';
import { WEBUI_API_BASE_PATH } from '$lib/constants';
import type { Banner } from '$lib/types';

export const importConfig = async (token: string, config) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_PATH}/configs/import`, {
		method: 'POST',
		data: {
			config: config
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const exportConfig = async (token: string) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_PATH}/configs/export`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getModelsConfig = async (token: string) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_PATH}/configs/models`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setModelsConfig = async (token: string, config: object) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_PATH}/configs/models`, {
		method: 'POST',
		data: {
			...config
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setDefaultPromptSuggestions = async (token: string, promptSuggestions: string) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_PATH}/configs/suggestions`, {
		method: 'POST',
		data: {
			suggestions: promptSuggestions
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getBanners = async (token: string): Promise<Banner[]> => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_PATH}/configs/banners`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setBanners = async (token: string, banners: Banner[]) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_PATH}/configs/banners`, {
		method: 'POST',
		data: {
			banners: banners
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
