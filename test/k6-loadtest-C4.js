import http from 'k6/http';
import { Trend } from 'k6/metrics';
import { check, sleep } from 'k6';

/*
Install k6 https://grafana.com/docs/k6/latest/set-up/install-k6/
Run command: 

k6 run k6-loadtest-C4.js
k6 run k6-loadtest-C4.js --summary-mode full
K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_EXPORT=html-report.html k6 run k6-loadtest-c4.js

Scenario :
FOR LOCAL DEV ONLY!
A user connects to the application, sends a message that is saved to the chat history using wiki grounding.
All virtual users use the same credential using a token (to reduce load on the auth service).
The LLM provide an answer that is saved to the chat history.
The user deletes the history of the message he just sent.
Success!
*/

// Global Configuration
const BASE_URL = 'http://localhost:8080';
const USER_EMAIL = 'user@canchat.ca';
const USER_PASS = 'user';
const MODEL_ID = 'llama3.2:1b'; //chatgpt-4o-latest, tinyllama:latest
const TEARDOWN = true; //remove the chat from the user history
const DEBUG = false; //add more log info

const inferenceTrend = new Trend('llm_inference_time', true); // Track GPU/LLM latency
const dbSaveTrend = new Trend('db_save_time', true); // Track DB write latency

/**
 * The test parameters
 * Current setup would fit an "Average Load" test scenario
 * Load test types : https://grafana.com/docs/k6/latest/testing-guides/test-types/
 */
export const options = {
	stages: [
		{ duration: '1m', target: 5 }, //user ramp up from 1 to 5 over 1m
		{ duration: '3m', target: 5 }, //concurrent load, stays at 5
		{ duration: '1m', target: 0 } //user ramp down from 5 to 1 over 1m
	],
	thresholds: {
		http_req_failed: ['rate<0.01']
	}
};

/**
 * Create a uuid for chat history
 * @returns a formatted uuid
 */
function uuidv4() {
	return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
		var r = (Math.random() * 16) | 0,
			v = c == 'x' ? r : (r & 0x3) | 0x8;
		return v.toString(16);
	});
}

/**
 * Authenticate to the system and create an authentication token
 * @returns The authentication token
 */
export function setup() {
	const loginRes = http.post(
		`${BASE_URL}/api/v1/auths/signin`,
		JSON.stringify({
			email: USER_EMAIL,
			password: USER_PASS
		}),
		{ headers: { 'Content-Type': 'application/json' } }
	);

	check(loginRes, { 'Login Setup Success': (r) => r.status === 200 });
	return { token: loginRes.json('token') };
}

/**
 * Create the json payload, send it to the model, save history, and clean up.
 * @param {*} data The test data from setup
 */
export default function (data) {
	const authHeaders = {
		'Content-Type': 'application/json',
		Authorization: `Bearer ${data.token}`
	};

	// Prepare the data
	const chatId = uuidv4();
	const userMessageId = uuidv4();
	const aiMessageId = uuidv4();

	const promptText = `${Math.random()} Current prime minister of Canada? Only provide the name.`;
	const timestamp = Math.floor(Date.now() / 1000);

	// Define the object LOCALLY first to keep the history
	const myChatObj = {
		id: chatId,
		title: `K6 Save Test ${timestamp}`,
		models: [MODEL_ID],
		params: {},
		history: {
			messages: {
				[userMessageId]: {
					id: userMessageId,
					parentId: null,
					childrenIds: [],
					role: 'user',
					content: promptText,
					timestamp: timestamp,
					models: [MODEL_ID]
				}
			},
			currentId: userMessageId
		}
	};

	// Create the chat
	const createRes = http.post(`${BASE_URL}/api/v1/chats/new`, JSON.stringify({ chat: myChatObj }), {
		headers: authHeaders
	});

	if (createRes.status !== 200) {
		console.error(`Create Failed: ${createRes.body}`);
		return;
	}

	// Merge the Server ID (permissions) with the Local Object
	const serverResponse = createRes.json();
	const realChatId = serverResponse.id;

	myChatObj.id = realChatId;
	myChatObj.user_id = serverResponse.user_id;

	// Sync timestamps
	if (serverResponse.created_at) myChatObj.created_at = serverResponse.created_at;
	if (serverResponse.updated_at) myChatObj.updated_at = serverResponse.updated_at;

	if (DEBUG) console.log(`Chat Created: ${realChatId} (Owner: ${myChatObj.user_id})`);

	// Send the prompt to the model
	const chatPayload = JSON.stringify({
		model: MODEL_ID,
		messages: [{ role: 'user', content: promptText }],
		chat_id: realChatId,
		stream: false,
		features: { wiki_grounding: true }
	});

	if (DEBUG) console.log(`Sending RAG request...`);
	const chatRes = http.post(`${BASE_URL}/api/chat/completions`, chatPayload, {
		headers: authHeaders,
		timeout: '180s'
	});

	// Track time to get the reply
	inferenceTrend.add(chatRes.timings.duration);

	const ragSuccess = check(chatRes, {
		'RAG Response 200': (r) => r.status === 200,
		'Answer Generated': (r) => r.body && r.body.length > 0
	});

	if (!ragSuccess) return;

	const body = chatRes.json();
	// Only get the content param from the answer
	const answerContent = body.choices?.[0]?.message?.content || 'No content found';
	console.log(`Answer Received: ${answerContent}`);

	// Save to the database

	// Update local history structure to include the response
	myChatObj.history.messages[userMessageId].childrenIds = [aiMessageId];

	// Create the response message
	myChatObj.history.messages[aiMessageId] = {
		id: aiMessageId,
		parentId: userMessageId,
		childrenIds: [],
		role: 'assistant',
		content: answerContent,
		timestamp: Math.floor(Date.now() / 1000),
		models: [MODEL_ID]
	};

	myChatObj.history.currentId = aiMessageId;

	// Send the update to the DB
	const updateRes = http.post(
		`${BASE_URL}/api/v1/chats/${realChatId}`,
		JSON.stringify({ chat: myChatObj }),
		{ headers: authHeaders }
	);

	// Track DB write time
	dbSaveTrend.add(updateRes.timings.duration);

	check(updateRes, {
		'History Saved': (r) => r.status === 200
	});

	if (updateRes.status === 200) {
		if (DEBUG) console.log(`Answer saved to DB`);
	} else {
		console.error(`Save Failed: ${updateRes.body}`);
	}

	// Simulate the user reading the reply
	sleep(Math.random() * 2 + 1);

	// Teardown
	if (TEARDOWN) {
		if (DEBUG) console.log(`Teardown: Deleting chat ${realChatId}...`);
		const delRes = http.del(`${BASE_URL}/api/v1/chats/${realChatId}`, null, {
			headers: authHeaders
		});

		if (delRes.status === 200) {
			if (DEBUG) console.log(`Deleted chat ${realChatId}`);
		} else {
			console.error(`Delete Failed: ${delRes.status} - ${delRes.body}`);
		}
	}
}
