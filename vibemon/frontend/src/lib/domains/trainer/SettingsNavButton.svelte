<script lang="ts">
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';
	import PixelIcon from '$lib/ui/PixelIcon.svelte';

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
	<span class="settings-nav__label" aria-hidden="true">Settings</span>
	<FreeFormButton class="settings-nav-button" ariaLabel="Settings" {disabled} onclick={toggleMenu}>
		<span class="settings-nav-button__ridge" aria-hidden="true"></span>
		<PixelIcon name="gear" class="vm-icon--raised settings-nav-button__icon" />
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

	/* Micro-label so the knob reads as the settings control at first glance. */
	.settings-nav__label {
		position: absolute;
		bottom: calc(100% + var(--vm-space-xs));
		left: 50%;
		transform: translateX(-50%);
		font-family: var(--vm-font-ui);
		font-size: 0.5rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		white-space: nowrap;
		/* Stamped brass label — readable on the dark wood corner plate. */
		color: var(--vm-parchment);
		opacity: 0.92;
		text-shadow:
			0 1px 0 rgb(20 12 8 / 0.75),
			0 -1px 0 rgb(240 231 206 / 0.15);
		pointer-events: none;
	}

	/* Machined cabinet knob — mounted at the bezel corner (DESIGN.md §5.2).
	   Brass ring + knurled edge + top-light so it reads as a raised, turnable control. */
	:global(.settings-nav-button) {
		position: relative;
		display: grid;
		place-items: center;
		height: 100%;
		width: auto;
		aspect-ratio: 1;
		padding: 0;
		border-radius: 50%;
		background:
			radial-gradient(circle at 35% 28%, rgb(240 231 206 / 0.16), transparent 42%),
			var(--vm-cabinet-wood-grain-corner);
		box-shadow:
			inset 0 0 0 2px var(--vm-brass),
			inset 0 0 0 4px rgb(20 12 8 / 0.4),
			inset 0 -3px 4px rgb(20 12 8 / 0.45),
			0 3px 0 rgb(42 30 22 / 0.5),
			0 4px 6px rgb(20 12 8 / 0.35);
		color: var(--vm-parchment);
		transform-origin: center bottom;
	}

	/* Knurled rim — ticks masked to the outer ring only. */
	.settings-nav-button__ridge {
		position: absolute;
		inset: 4px;
		border-radius: 50%;
		background: repeating-conic-gradient(
			rgb(240 231 206 / 0.18) 0deg 5deg,
			transparent 5deg 15deg
		);
		-webkit-mask: radial-gradient(circle, transparent 60%, #fff 62%);
		mask: radial-gradient(circle, transparent 60%, #fff 62%);
		pointer-events: none;
	}

	/* Stepped two-frame lift — smooth eased scaling reads modern (DESIGN.md §6.1) */
	:global(.settings-nav-button:hover:not(:disabled)),
	:global(.settings-nav-button:focus-visible:not(:disabled)) {
		animation: settings-nav-lift 240ms steps(2, jump-none) forwards;
	}

	/* Press: the knob turns and seats instead of only lifting. */
	:global(.settings-nav-button:active:not(:disabled)) {
		animation: none;
		transform: translateY(1px) rotate(14deg);
		box-shadow:
			inset 0 0 0 2px var(--vm-brass),
			inset 0 0 0 4px rgb(20 12 8 / 0.4),
			inset 0 -3px 4px rgb(20 12 8 / 0.45),
			0 1px 0 rgb(42 30 22 / 0.5);
	}

	@keyframes settings-nav-lift {
		from {
			transform: translateY(0);
		}
		to {
			transform: translateY(-3px);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		:global(.settings-nav-button:hover:not(:disabled)),
		:global(.settings-nav-button:focus-visible:not(:disabled)) {
			animation: none;
		}

		:global(.settings-nav-button:active:not(:disabled)) {
			transform: translateY(1px);
		}
	}

	/* :global — the svg root lives inside PixelIcon, outside this component's scope. */
	:global(.settings-nav-button__icon) {
		width: 62%;
		height: 62%;
		user-select: none;
		pointer-events: none;
		filter: drop-shadow(0 1px 0 rgb(20 12 8 / 0.6));
	}
</style>
