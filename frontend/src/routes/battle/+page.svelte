<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { generation } from '$lib/stores/generation.svelte';

	let raw = $state('');

	onMount(() => {
		if (!generation.payload) {
			void goto('/');
			return;
		}
		raw = JSON.stringify(generation.payload, null, 2);
	});
</script>

<div class="layout">
	<h1>Battle (preview)</h1>
	<p class="muted">Raw generation payload for player and enemy.</p>
	{#if raw}
		<pre>{raw}</pre>
		<p><a href="/">Back</a></p>
	{:else}
		<p class="muted">Redirecting…</p>
	{/if}
</div>
