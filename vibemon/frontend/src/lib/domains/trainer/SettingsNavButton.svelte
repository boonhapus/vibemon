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
	<FreeFormButton class="settings-nav-button" ariaLabel="Settings" {disabled} onclick={toggleMenu}>
		<span class="settings-nav-button__ridge" aria-hidden="true"></span>
		<PixelIcon name="gear" class="vm-icon--raised settings-nav-button__icon" />
	</FreeFormButton>
	<span class="settings-nav__label" aria-hidden="true">Settings</span>
</div>

<style>
	.settings-nav {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: flex-end;
		gap: var(--vm-space-xs);
		height: 100%;
	}

	/* Micro-label tucked under the knob on the corner plate. */
	.settings-nav__label {
		flex: 0 0 auto;
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

	/* Brass ring only — bezel wood shows through the face. */
	:global(.settings-nav-button) {
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
		transform-origin: center bottom;
	}

	.settings-nav-button__ridge {
		position: absolute;
		inset: 0;
		border-radius: 50%;
		border: 2px solid var(--vm-brass);
		box-shadow: inset 0 0 0 1px rgb(20 12 8 / 0.28);
		background: transparent;
		pointer-events: none;
	}

	:global(.settings-nav-button:active:not(:disabled)) .settings-nav-button__ridge {
		box-shadow:
			inset 0 0 0 1px rgb(20 12 8 / 0.32),
			inset 0 1px 2px rgb(20 12 8 / 0.28);
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
		width: 56%;
		height: 56%;
		color: var(--vm-cabinet-knob-icon-settings);
		user-select: none;
		pointer-events: none;
		filter: drop-shadow(0 1px 0 rgb(20 12 8 / 0.45));
	}
</style>
