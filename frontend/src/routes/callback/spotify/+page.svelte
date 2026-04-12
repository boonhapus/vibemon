<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { exchangeSpotifyCode } from '$lib/auth/spotify';
	import { generation } from '$lib/stores/generation.svelte';

	let status = $state<'exchanging' | 'success' | 'error'>('exchanging');
	let errMsg = $state('');

	onMount(async () => {
		const code = page.url.searchParams.get('code');
		const error = page.url.searchParams.get('error');

		if (error || !code) {
			errMsg = error || 'No authorization code received';
			status = 'error';
			setTimeout(() => goto('/'), 3000);
			return;
		}

		try {
			const result = await exchangeSpotifyCode(code);
			if (!result) {
				errMsg = 'Token exchange failed';
				status = 'error';
				setTimeout(() => goto('/'), 3000);
				return;
			}

			generation.spotifyToken = result.access_token;
			generation.spotifyExpiresAt = Date.now() + result.expires_in * 1000;
			status = 'success';
			await goto('/');
		} catch {
			errMsg = 'Token exchange error';
			status = 'error';
			setTimeout(() => goto('/'), 3000);
		}
	});
</script>

<div class="layout">
	<h1 class="callback-title">Spotify</h1>
	{#if status === 'exchanging'}
		<p class="muted">Exchanging authorization code…</p>
		<div class="spinner" aria-hidden="true"></div>
	{:else if status === 'success'}
		<p class="muted">Connected! Redirecting…</p>
	{:else}
		<p class="error">{errMsg}</p>
		<p class="muted">Redirecting back…</p>
	{/if}
</div>

<style>
	.callback-title {
		font-family: var(--f-px);
		font-size: 10px;
		font-weight: 400;
		letter-spacing: 0.04em;
	}
</style>
