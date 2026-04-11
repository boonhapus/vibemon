<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { generation } from '$lib/stores/generation.svelte';
	import { startSpotifyAuth } from '$lib/auth/spotify';
	import type { GenerateResponse } from '$lib/types';

	type UiPhase = 'geo' | 'city' | 'ready' | 'loading';

	let phase = $state<UiPhase>('geo');
	let submitting = $state(false);
	let errMsg = $state('');
	let city = $state('');
	let lat = $state<number | null>(null);
	let lon = $state<number | null>(null);

	onMount(() => {
		if (typeof navigator === 'undefined' || !navigator.geolocation) {
			phase = 'city';
			return;
		}
		navigator.geolocation.getCurrentPosition(
			(p) => {
				lat = p.coords.latitude;
				lon = p.coords.longitude;
				phase = 'ready';
			},
			() => {
				phase = 'city';
			},
			{ enableHighAccuracy: false, timeout: 10000, maximumAge: 60_000 }
		);
	});

	async function geocodeCity() {
		if (!city.trim()) {
			errMsg = 'Enter a city name';
			return;
		}
		submitting = true;
		phase = 'loading';
		errMsg = '';
		try {
			const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city.trim())}&count=1`;
			const r = await fetch(url);
			const j = (await r.json()) as { results?: { latitude: number; longitude: number }[] };
			const first = j.results?.[0];
			if (!first) {
				errMsg = 'City not found';
				phase = 'city';
				return;
			}
			lat = first.latitude;
			lon = first.longitude;
			phase = 'ready';
		} catch {
			errMsg = 'Geocoding failed';
			phase = 'city';
		} finally {
			submitting = false;
		}
	}

	function connectSpotify() {
		if (generation.spotifyExpired) {
			generation.clearSpotify();
		}
		startSpotifyAuth();
	}

	function disconnectSpotify() {
		generation.clearSpotify();
	}

	async function doGenerate() {
		if (lat === null || lon === null) {
			errMsg = 'Location required';
			return;
		}

		if (generation.spotifyToken && generation.spotifyExpired) {
			generation.clearSpotify();
			errMsg = 'Spotify token expired — please reconnect or generate without it.';
			return;
		}

		submitting = true;
		phase = 'loading';
		errMsg = '';

		const authTokens: Record<string, string> = {};
		if (generation.spotifyConnected && generation.spotifyToken) {
			authTokens.spotify = generation.spotifyToken;
		}

		try {
			const res = await fetch('/api/v1/generate', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					user_id: generation.spotifyConnected ? `spotify-user` : `web-${crypto.randomUUID()}`,
					latitude: lat,
					longitude: lon,
					auth_tokens: authTokens
				})
			});
			if (res.status === 422) {
				errMsg = 'Location required';
				phase = 'city';
				return;
			}
			if (!res.ok) {
				errMsg = `Request failed (${res.status})`;
				phase = 'ready';
				return;
			}
			generation.payload = (await res.json()) as GenerateResponse;
			await goto('/battle');
		} catch {
			errMsg = 'Network error';
			phase = 'ready';
		} finally {
			submitting = false;
		}
	}
</script>

<div class="layout">
	<h1>Vibemon</h1>
	<p class="muted">Share your location and connect your accounts to generate a unique creature.</p>

	<div class="auth-section">
		<h2>Data Sources</h2>
		<div class="auth-row">
			{#if generation.spotifyConnected}
				<span class="auth-status connected">✓ Spotify connected</span>
				<button type="button" class="btn-small" onclick={disconnectSpotify}>Disconnect</button>
			{:else}
				<button type="button" onclick={connectSpotify}>Connect Spotify</button>
				<span class="auth-hint">Optional — enriches your Vibemon with listening data</span>
			{/if}
		</div>
	</div>

	{#if phase === 'loading'}
		<p class="muted">Working…</p>
		<div class="spinner" aria-hidden="true"></div>
	{/if}

	{#if phase === 'geo'}
		<p class="muted">Requesting browser location…</p>
		<div class="spinner" aria-hidden="true"></div>
	{/if}

	{#if phase === 'city'}
		<p class="muted">Geolocation unavailable or denied. Enter a city name to look up coordinates.</p>
		<p>
			<input type="text" bind:value={city} placeholder="e.g. London" />
		</p>
		<p>
			<button type="button" onclick={geocodeCity} disabled={submitting}>Use city</button>
		</p>
	{/if}

	{#if phase === 'ready'}
		<p class="muted">Ready — lat {lat?.toFixed(4)}, lon {lon?.toFixed(4)}</p>
		<p>
			<button type="button" onclick={doGenerate} disabled={submitting}>Generate</button>
		</p>
	{/if}

	{#if errMsg}
		<p class="error">{errMsg}</p>
	{/if}
</div>

<style>
	.auth-section {
		margin: 1.5rem 0;
		padding: 1rem 1.25rem;
		border: 1px solid #222836;
		border-radius: 10px;
		background: #13161d;
		text-align: left;
	}
	.auth-section h2 {
		margin: 0 0 0.75rem;
		font-size: 1rem;
		color: #9aa3b2;
	}
	.auth-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
	}
	.auth-status.connected {
		color: #6ddf8b;
		font-weight: 500;
	}
	.auth-hint {
		color: #6b7385;
		font-size: 0.85rem;
	}
	.btn-small {
		padding: 0.3rem 0.7rem;
		font-size: 0.85rem;
	}
</style>
