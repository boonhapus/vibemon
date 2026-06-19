<script lang="ts">
	import {
		cabinetMetaStore,
		toggleCabinetMeta
	} from '$lib/domains/game/cabinetMetaStore.svelte';
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';
	import PixelIcon from '$lib/ui/PixelIcon.svelte';

	let { disabled = false }: { disabled?: boolean } = $props();

	function toggleGuide() {
		if (disabled) return;
		toggleCabinetMeta();
	}
</script>

<div class="guide-nav" class:guide-nav--open={cabinetMetaStore.expanded}>
	<FreeFormButton
		class="guide-nav-button"
		ariaLabel={cabinetMetaStore.expanded ? 'Hide guide panel' : 'Show guide panel'}
		{disabled}
		onclick={toggleGuide}
	>
		<span class="guide-nav-button__ridge" aria-hidden="true"></span>
		<PixelIcon name="note" class="vm-icon--raised guide-nav-button__icon" />
	</FreeFormButton>
	<span class="guide-nav__label" aria-hidden="true">Guide</span>
</div>

<style>
	.guide-nav {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: flex-end;
		gap: var(--vm-space-xs);
		height: 100%;
	}

	.guide-nav__label {
		flex: 0 0 auto;
		font-family: var(--vm-font-ui);
		font-size: 0.5rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		white-space: nowrap;
		color: var(--vm-parchment);
		opacity: 0.92;
		text-shadow:
			0 1px 0 rgb(20 12 8 / 0.75),
			0 -1px 0 rgb(240 231 206 / 0.15);
		pointer-events: none;
	}

	/* Brass ring only — bezel wood shows through the face. */
	:global(.guide-nav-button) {
		position: relative;
		display: grid;
		place-items: center;
		flex: 0 0 auto;
		height: clamp(2.35rem, 5.2vh, 3rem);
		width: clamp(2.35rem, 5.2vh, 3rem);
		padding: 0;
		border-radius: 50%;
		background: transparent;
		box-shadow: none;
		transform: rotate(0deg);
		transform-origin: center center;
		transition:
			transform var(--vm-guide-reveal-duration) steps(var(--anim-ui-reveal-steps), jump-none)
			var(--vm-guide-stagger);
	}

	.guide-nav--open :global(.guide-nav-button) {
		transform: rotate(90deg);
		transition:
			transform var(--vm-guide-reveal-duration) steps(var(--anim-ui-reveal-steps), jump-none) 0ms;
	}

	.guide-nav-button__ridge {
		position: absolute;
		inset: 0;
		border-radius: 50%;
		border: 2px solid var(--vm-brass);
		box-shadow: inset 0 0 0 1px rgb(20 12 8 / 0.28);
		background: transparent;
		pointer-events: none;
	}

	:global(.guide-nav-button:active:not(:disabled)) .guide-nav-button__ridge {
		box-shadow:
			inset 0 0 0 1px rgb(20 12 8 / 0.32),
			inset 0 1px 2px rgb(20 12 8 / 0.28);
	}

	:global(.guide-nav-button:hover:not(:disabled)),
	:global(.guide-nav-button:focus-visible:not(:disabled)) {
		animation: guide-nav-lift 240ms steps(2, jump-none) forwards;
	}

	.guide-nav--open :global(.guide-nav-button:hover:not(:disabled)),
	.guide-nav--open :global(.guide-nav-button:focus-visible:not(:disabled)) {
		animation: guide-nav-lift-open 240ms steps(2, jump-none) forwards;
	}

	:global(.guide-nav-button:active:not(:disabled)) {
		animation: none;
		transform: rotate(0deg) translateY(1px);
	}

	.guide-nav--open :global(.guide-nav-button:active:not(:disabled)) {
		transform: rotate(90deg) translateY(1px);
	}

	@keyframes guide-nav-lift {
		from {
			transform: rotate(0deg) translateY(0);
		}
		to {
			transform: rotate(0deg) translateY(-3px);
		}
	}

	@keyframes guide-nav-lift-open {
		from {
			transform: rotate(90deg) translateY(0);
		}
		to {
			transform: rotate(90deg) translateY(-3px);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		:global(.guide-nav-button) {
			transition: none;
		}

		:global(.guide-nav-button:hover:not(:disabled)),
		:global(.guide-nav-button:focus-visible:not(:disabled)) {
			animation: none;
		}
	}

	:global(.guide-nav-button__icon) {
		width: 56%;
		height: 56%;
		color: var(--vm-cabinet-knob-icon-guide);
		user-select: none;
		pointer-events: none;
		filter: drop-shadow(0 1px 0 rgb(20 12 8 / 0.45));
	}
</style>
