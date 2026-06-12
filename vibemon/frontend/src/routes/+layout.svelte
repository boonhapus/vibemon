<script lang="ts">
	import { onMount } from 'svelte';

	import MobileViewportGuideModal from '$lib/domains/game/MobileViewportGuideModal.svelte';
	import { maybeAutoShowMobileViewportGuide } from '$lib/domains/game/mobileViewportGuideStore.svelte';
	import '../app.css';

	let { children } = $props();

	onMount(() => {
		maybeAutoShowMobileViewportGuide();
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
{@render children()}
