<script lang="ts">
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';

	const SETTINGS_ICON = '/game/icons/settings.png';

	let {
		open = $bindable(false),
		disabled = false
	}: {
		open?: boolean;
		disabled?: boolean;
	} = $props();

	function toggleMenu() {
		if (disabled) return;
		open = !open;
	}
</script>

<div class="settings-nav">
	<FreeFormButton class="settings-nav-button" ariaLabel="Settings" {disabled} onclick={toggleMenu}>
		<img class="settings-nav-button__icon" src={SETTINGS_ICON} alt="" decoding="async" />
	</FreeFormButton>
</div>

<style>
	.settings-nav {
		position: relative;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	:global(.settings-nav-button) {
		display: grid;
		place-items: center;
		height: 100%;
		width: auto;
		aspect-ratio: 1;
		padding: 0;
		transition: transform 120ms ease;
		transform-origin: center center;
	}

	:global(.settings-nav-button:hover:not(:disabled)),
	:global(.settings-nav-button:focus-visible:not(:disabled)) {
		transform: scale(1.06);
	}

	.settings-nav-button__icon {
		display: block;
		width: calc(100% * var(--vm-hud-nav-icon-settings-visual-scale));
		height: calc(100% * var(--vm-hud-nav-icon-settings-visual-scale));
		object-fit: contain;
		image-rendering: pixelated;
		image-rendering: crisp-edges;
		user-select: none;
		pointer-events: none;
		filter: drop-shadow(0 2px 0 rgb(42 30 22 / 0.22));
	}
</style>
