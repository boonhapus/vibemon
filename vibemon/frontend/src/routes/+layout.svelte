<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';

	import {
		applyGameSolarDevOverride,
		startGameSolarClock,
		stopGameSolarClock
	} from '$lib/domains/game/gameSolarContext.svelte';
	import MobileViewportGuideModal from '$lib/domains/game/MobileViewportGuideModal.svelte';
	import { maybeAutoShowMobileViewportGuide } from '$lib/domains/game/mobileViewportGuideStore.svelte';
	import SettingsModal from '$lib/domains/trainer/SettingsModal.svelte';
	import { settingsStore } from '$lib/domains/trainer/settingsStore.svelte';
	import GameToast from '$lib/ui/GameToast.svelte';
	import '../app.css';

	let { children } = $props();

	$effect(() => {
		applyGameSolarDevOverride(page.url.searchParams);
	});

	onMount(() => {
		maybeAutoShowMobileViewportGuide();
		startGameSolarClock();
		return () => stopGameSolarClock();
	});
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link
		href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Pixelify+Sans:wght@400;500;600&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

<MobileViewportGuideModal />
<GameToast />
<SettingsModal bind:open={settingsStore.open} />
{@render children()}
