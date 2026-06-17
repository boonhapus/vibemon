import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(frontendRoot, '../..');
const certDir = path.join(frontendRoot, '.certs');
const keyPath = path.join(certDir, 'dev-key.pem');
const certPath = path.join(certDir, 'dev-cert.pem');

const hasDevCert = fs.existsSync(keyPath) && fs.existsSync(certPath);

if (!hasDevCert) {
	console.warn('[vibemon] No dev TLS cert in .certs/. Run `pnpm certs` for HTTPS (required for mobile geolocation).');
}

export default defineConfig({
	logLevel: 'warn',
	plugins: [sveltekit()],
	// Pre-bundle SSR deps up front so mid-request re-optimization does not
	// invalidate in-flight browser chunks (throwOutdatedRequest on deps_ssr/*).
	optimizeDeps: {
		include: ['svelte', 'suncalc']
	},
	ssr: {
		optimizeDeps: {
			include: ['svelte', 'suncalc']
		}
	},
	server: {
		// Bind all interfaces so LAN phones can reach the dev server.
		host: true,
		port: 5173,
		strictPort: false,
		fs: {
			// Monorepo-linked assets outside the frontend package
			allow: [frontendRoot, repoRoot]
		},
		...(hasDevCert
			? {
					https: {
						key: fs.readFileSync(keyPath),
						cert: fs.readFileSync(certPath)
					}
				}
			: {}),
		proxy: {
			'/api': {
				target: 'http://127.0.0.1:8000',
				changeOrigin: true
			},
			'/lastfm': {
				target: 'http://127.0.0.1:8000',
				changeOrigin: true
			}
		}
	}
});
