import { execSync } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import { networkInterfaces, platform } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const certDir = path.join(root, '.certs');
const keyFile = path.join(certDir, 'dev-key.pem');
const certFile = path.join(certDir, 'dev-cert.pem');

function resolveMkcert() {
	try {
		return execSync('where mkcert', { encoding: 'utf8' }).trim().split(/\r?\n/)[0];
	} catch {
		if (platform() === 'win32') {
			const localAppData = process.env.LOCALAPPDATA;
			if (localAppData) {
				const wingetGlob = path.join(
					localAppData,
					'Microsoft',
					'WinGet',
					'Packages',
					'FiloSottile.mkcert_Microsoft.Winget.Source_8wekyb3d8bbwe',
					'mkcert.exe'
				);
				if (existsSync(wingetGlob)) return wingetGlob;
			}
		}
		throw new Error('mkcert not found. Install: winget install FiloSottile.mkcert');
	}
}

function lanIpv4Addresses() {
	const ips = [];
	for (const entries of Object.values(networkInterfaces())) {
		for (const entry of entries ?? []) {
			if (entry.family === 'IPv4' && !entry.internal) {
				ips.push(entry.address);
			}
		}
	}
	return ips;
}

const mkcert = resolveMkcert();
const hosts = [...new Set(['localhost', '127.0.0.1', '::1', ...lanIpv4Addresses()])];

mkdirSync(certDir, { recursive: true });

console.log('Installing mkcert local CA (may prompt for admin once)…');
execSync(`"${mkcert}" -install`, { stdio: 'inherit' });

console.log(`Generating dev cert for: ${hosts.join(', ')}`);
execSync(`"${mkcert}" -key-file "${keyFile}" -cert-file "${certFile}" ${hosts.map((host) => `"${host}"`).join(' ')}`, {
	stdio: 'inherit',
	shell: true
});

const rootCaHint =
	platform() === 'win32'
		? path.join(process.env.LOCALAPPDATA ?? '', 'mkcert', 'rootCA.pem')
		: '$(mkcert -CAROOT)/rootCA.pem';

console.log(`\nWrote:\n  ${certFile}\n  ${keyFile}`);
console.log(`\nPhone testing: copy ${rootCaHint} to your device and install it as a trusted CA.`);
console.log('Then open https://<your-lan-ip>:5173 on the same Wi‑Fi.');
console.log('\nRun: pnpm dev');
