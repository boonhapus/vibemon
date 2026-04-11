import { env } from '$env/dynamic/public';

const SCOPES = 'user-read-recently-played user-top-read';

function generateRandomString(length: number): string {
	const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
	const values = crypto.getRandomValues(new Uint8Array(length));
	return Array.from(values, (v) => chars[v % chars.length]).join('');
}

async function sha256(plain: string): Promise<ArrayBuffer> {
	const encoder = new TextEncoder();
	return crypto.subtle.digest('SHA-256', encoder.encode(plain));
}

function base64url(buf: ArrayBuffer): string {
	return btoa(String.fromCharCode(...new Uint8Array(buf)))
		.replace(/\+/g, '-')
		.replace(/\//g, '_')
		.replace(/=+$/, '');
}

export async function startSpotifyAuth(): Promise<void> {
	const clientId = env.PUBLIC_SPOTIFY_CLIENT_ID;
	if (!clientId) {
		console.warn('PUBLIC_SPOTIFY_CLIENT_ID not set');
		return;
	}

	const codeVerifier = generateRandomString(64);
	const challengeBuf = await sha256(codeVerifier);
	const codeChallenge = base64url(challengeBuf);

	sessionStorage.setItem('spotify_code_verifier', codeVerifier);

	const redirectUri = `${window.location.origin}/callback/spotify`;

	const params = new URLSearchParams({
		client_id: clientId,
		response_type: 'code',
		redirect_uri: redirectUri,
		scope: SCOPES,
		code_challenge_method: 'S256',
		code_challenge: codeChallenge
	});

	window.location.href = `https://accounts.spotify.com/authorize?${params.toString()}`;
}

export async function exchangeSpotifyCode(code: string): Promise<{
	access_token: string;
	expires_in: number;
} | null> {
	const clientId = env.PUBLIC_SPOTIFY_CLIENT_ID;
	if (!clientId) return null;

	const codeVerifier = sessionStorage.getItem('spotify_code_verifier');
	if (!codeVerifier) return null;

	const redirectUri = `${window.location.origin}/callback/spotify`;

	const body = new URLSearchParams({
		grant_type: 'authorization_code',
		code,
		redirect_uri: redirectUri,
		client_id: clientId,
		code_verifier: codeVerifier
	});

	const res = await fetch('https://accounts.spotify.com/api/token', {
		method: 'POST',
		headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
		body
	});

	if (!res.ok) return null;

	const data = await res.json();
	sessionStorage.removeItem('spotify_code_verifier');
	return { access_token: data.access_token, expires_in: data.expires_in };
}
