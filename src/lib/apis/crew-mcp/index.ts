import axiosInstance from "$lib/axiosInstance";
import { WEBUI_API_BASE_URL } from "$lib/constants";

export const getCrewMCPStatus = async (token: string = '') => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_URL}/crew-mcp/status`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			return res.data
		})
		.catch((err) => {
			error = `CrewAI MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getCrewMCPTools = async (token: string = '') => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_URL}/crew-mcp/tools`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			return res.data
		})
		.catch((err) => {
			error = `CrewAI MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const queryCrewMCP = async (
	token: string = '',
	query: string,
	model: string = '',
	selectedTools: string[] = [],
	chatId: string = '',
	sessionId: string = ''
) => {
	let error = null;

	const res = await axiosInstance(`${WEBUI_API_BASE_URL}/crew-mcp/query`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		data: {
			query: query,
			model: model,
			selected_tools: selectedTools,
			chat_id: chatId,
			session_id: sessionId
		}})
		.then(async (res) => {
			return res.data
		})
		.catch((err) => {
			error = `CrewAI MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
