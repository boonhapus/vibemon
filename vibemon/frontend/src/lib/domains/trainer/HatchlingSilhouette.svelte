<script lang="ts">
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';

	import TrainerPortrait from './TrainerPortrait.svelte';

	let {
		hovered = $bindable(false),
		disabled = false,
		onclick
	}: {
		hovered?: boolean;
		disabled?: boolean;
		onclick?: (event: MouseEvent) => void;
	} = $props();

	function showHint() {
		if (disabled) return;
		hovered = true;
	}

	function hideHint() {
		hovered = false;
	}
</script>

<div class="hatchling-silhouette">
	<TrainerPortrait spriteSrc="/game/sprites/hatchling-silhouette.png" class="hatchling-silhouette__portrait" />
	<FreeFormButton
		class="hatchling-silhouette__hit"
		ariaLabel="Hatch a new Vibemon from your selected vibes"
		{disabled}
		{onclick}
		onmouseenter={showHint}
		onmouseleave={hideHint}
		onfocus={showHint}
		onblur={hideHint}
	/>
</div>

<style>
	.hatchling-silhouette {
		position: relative;
		--hatchling-sprite-h: clamp(10.5rem, 25vh, 18rem);
		/* hatchling-silhouette.png is 961×672 — much wider than the trainer sprite */
		--hatchling-sprite-w: calc(var(--hatchling-sprite-h) * 961 / 672);
		--hatchling-platform-h: clamp(1.2rem, 2.8vw, 1.75rem);
	}

	.hatchling-silhouette :global(.hatchling-silhouette__portrait) {
		--sprite-h: var(--hatchling-sprite-h);
		--sprite-w: var(--hatchling-sprite-w);
		--platform-h: var(--hatchling-platform-h);
		--platform-w: calc(var(--sprite-h) * 0.82 * 1.5);
	}

	.hatchling-silhouette :global(.hatchling-silhouette__portrait .trainer-portrait__sprite) {
		filter: brightness(0);
		transform: translateY(-2%);
	}

	:global(.hatchling-silhouette__hit) {
		position: absolute;
		bottom: calc(var(--hatchling-platform-h) * 0.26);
		left: 50%;
		z-index: 2;
		width: var(--hatchling-sprite-w);
		height: var(--hatchling-sprite-h);
		transform: translateX(-50%) translateY(-2%);
		cursor: pointer;
		transition: transform 120ms ease;
	}

	:global(.hatchling-silhouette__hit:hover:not(:disabled)),
	:global(.hatchling-silhouette__hit:focus-visible:not(:disabled)) {
		transform: translateX(-50%) translateY(-2%) scale(1.03);
	}

	@media (max-width: 480px) {
		.hatchling-silhouette {
			--hatchling-sprite-h: clamp(7.75rem, 21vh, 12.5rem);
			--hatchling-platform-h: clamp(1rem, 2.4vw, 1.4rem);
		}
	}
</style>
