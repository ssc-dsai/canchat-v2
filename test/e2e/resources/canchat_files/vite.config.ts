import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit(),
		{
			name: 'replace-webui-base-url',
			enforce: 'post',
			transform(code, id) {
				// Apply transformation to every file
				code = code.replace(/\${WEBUI_BASE_URL}\/static/g, '/static/');
				code = code.replace(/{WEBUI_BASE_URL}\/static/g, '/static/');
				code = code.replace(/WEBUI_BASE_URL \+ \"\/static/g, '\"/static/');
				return code;
			}
		},
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	build: {
		sourcemap: true
	},
	worker: {
		format: 'es'
	}
});
