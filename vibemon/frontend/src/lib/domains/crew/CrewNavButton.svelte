<script lang="ts">
	import { goto } from '$app/navigation';

	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';

	const VIBE_DECK_ICON = '/game/icons/vibe-deck.png';

	let {
		disabled = false,
		href = '/deck/crew',
		onmouseenter,
		onmouseleave,
		onfocus,
		onblur
	}: {
		disabled?: boolean;
		href?: string;
		onmouseenter?: (event: MouseEvent) => void;
		onmouseleave?: (event: MouseEvent) => void;
		onfocus?: (event: FocusEvent) => void;
		onblur?: (event: FocusEvent) => void;
	} = $props();

	function openDeck() {
		if (disabled) return;
		void goto(href);
	}
</script>

<FreeFormButton
	class="crew-nav-button"
	ariaLabel="Open Vibe Deck"
	{disabled}
	onclick={openDeck}
	{onmouseenter}
	{onmouseleave}
	{onfocus}
	{onblur}
>
	<img class="crew-nav-button__icon" src={VIBE_DECK_ICON} alt="" decoding="async" />
</FreeFormButton>

<style>
	:global(.crew-nav-button) {
		display: grid;
		place-items: center;
		height: 100%;
		width: auto;
		aspect-ratio: var(--vm-hud-nav-icon-vibe-deck-aspect);
		padding: 0;
		transition: transform 120ms ease;
		transform-origin: center center;
	}

	:global(.crew-nav-button:hover:not(:disabled)),
	:global(.crew-nav-button:focus-visible:not(:disabled)) {
		transform: scale(1.06);
	}

	.crew-nav-button__icon {
		display: block;
		width: 100%;
		height: 100%;
		object-fit: contain;
		image-rendering: pixelated;
		image-rendering: crisp-edges;
		user-select: none;
		pointer-events: none;
		filter: drop-shadow(0 2px 0 rgb(42 30 22 / 0.22));
	}
</style>
