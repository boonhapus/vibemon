<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * Tactile pixel button (DESIGN.md §3.2). Three tiers:
	 * `primary` = the main action — filled Burnt Orange bevel.
	 * `secondary` = menu/list entries — parchment with a tobacco outline.
	 * `tertiary` = inline/low-stakes — flat text with the mustard ▶ cursor.
	 *
	 * State hooks for consumers: --btn-surface, --btn-text, --btn-accent.
	 */
	export type GameButtonVariant = 'primary' | 'secondary' | 'tertiary';

	let {
		variant = 'secondary',
		selected = false,
		disabled = false,
		forceState,
		ariaLabel,
		class: className = '',
		onclick,
		onpointerdown,
		onpointerup,
		onpointerleave,
		onpointercancel,
		onmouseenter,
		onmouseleave,
		onfocus,
		onblur,
		oncontextmenu,
		children
	}: {
		variant?: GameButtonVariant;
		selected?: boolean;
		disabled?: boolean;
		forceState?: 'hover' | 'active' | 'focus';
		ariaLabel?: string;
		class?: string;
		onclick?: (event: MouseEvent) => void;
		onpointerdown?: (event: PointerEvent) => void;
		onpointerup?: (event: PointerEvent) => void;
		onpointerleave?: (event: PointerEvent) => void;
		onpointercancel?: (event: PointerEvent) => void;
		onmouseenter?: (event: MouseEvent) => void;
		onmouseleave?: (event: MouseEvent) => void;
		onfocus?: (event: FocusEvent) => void;
		onblur?: (event: FocusEvent) => void;
		oncontextmenu?: (event: MouseEvent) => void;
		children: Snippet;
	} = $props();
</script>

<button
	type="button"
	class={['game-button', `game-button--${variant}`, className]}
	class:game-button--selected={selected}
	class:game-button--force-hover={forceState === 'hover'}
	class:game-button--force-active={forceState === 'active'}
	class:game-button--force-focus={forceState === 'focus'}
	{onclick}
	{onpointerdown}
	{onpointerup}
	{onpointerleave}
	{onpointercancel}
	{onmouseenter}
	{onmouseleave}
	{onfocus}
	{onblur}
	{oncontextmenu}
	{disabled}
	aria-label={ariaLabel}
	aria-pressed={selected || undefined}
>
	<span class="game-button__face">
		<span class="game-button__cursor" aria-hidden="true">▶</span>
		<span class="game-button__label">{@render children()}</span>
	</span>
</button>

<style>
	.game-button {
		--btn-surface: var(--vm-panel-command-bg);
		--btn-text: var(--vm-tobacco-black);
		--btn-accent: var(--vm-tobacco);
		--btn-bevel-w: 3px;
		--btn-chamfer: 8px;
		--btn-step: calc(var(--btn-chamfer) / 2);
		--btn-shadow-h: 3px;
		--btn-press-travel: 2px;

		display: inline-block;
		margin: 0;
		padding: 0;
		border: 0;
		background: transparent;
		color: var(--btn-text);
		font-family: var(--vm-font-ui);
		font-size: 0.8125rem;
		line-height: 1.5;
		letter-spacing: 0.06em;
		cursor: pointer;
		-webkit-tap-highlight-color: transparent;
		transition:
			transform 120ms ease,
			filter 120ms ease;
		/* drop-shadow (not box-shadow) so the shadow follows the stepped clip.
		   --btn-state-filter lets status consumers (e.g. grayscale) compose with it. */
		filter: var(--btn-state-filter, none) drop-shadow(0 var(--btn-shadow-h) 0 rgb(42 30 22 / 0.28));
	}

	.game-button__face {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--vm-space-xs);
		box-sizing: border-box;
		width: 100%;
		min-height: 44px; /* touch target floor (DESIGN.md §5.4) */
		padding: var(--vm-space-sm) var(--vm-space-md);
		background-color: var(--btn-surface);
		/* dither grain + two-tone bevel: light top, dark bottom (§3.2) */
		background-image:
			radial-gradient(circle at 25% 30%, rgb(61 43 31 / 0.05) 1px, transparent 1px),
			linear-gradient(var(--btn-bevel-light, transparent), var(--btn-bevel-light, transparent)),
			linear-gradient(var(--btn-bevel-dark, transparent), var(--btn-bevel-dark, transparent));
		background-repeat: repeat, no-repeat, no-repeat;
		background-position:
			0 0,
			0 0,
			0 100%;
		background-size:
			7px 7px,
			100% var(--btn-bevel-w),
			100% var(--btn-bevel-w);
		box-shadow: inset 0 0 0 var(--btn-outline-w, 0) var(--btn-accent);
		clip-path: polygon(
			calc(var(--btn-step) * 2) 0,
			calc(100% - var(--btn-step) * 2) 0,
			calc(100% - var(--btn-step) * 2) var(--btn-step),
			calc(100% - var(--btn-step)) var(--btn-step),
			calc(100% - var(--btn-step)) calc(var(--btn-step) * 2),
			100% calc(var(--btn-step) * 2),
			100% calc(100% - var(--btn-step) * 2),
			calc(100% - var(--btn-step)) calc(100% - var(--btn-step) * 2),
			calc(100% - var(--btn-step)) calc(100% - var(--btn-step)),
			calc(100% - var(--btn-step) * 2) calc(100% - var(--btn-step)),
			calc(100% - var(--btn-step) * 2) 100%,
			calc(var(--btn-step) * 2) 100%,
			calc(var(--btn-step) * 2) calc(100% - var(--btn-step)),
			var(--btn-step) calc(100% - var(--btn-step)),
			var(--btn-step) calc(100% - var(--btn-step) * 2),
			0 calc(100% - var(--btn-step) * 2),
			0 calc(var(--btn-step) * 2),
			var(--btn-step) calc(var(--btn-step) * 2),
			var(--btn-step) var(--btn-step),
			calc(var(--btn-step) * 2) var(--btn-step)
		);
	}

	/* ---- tiers ---- */

	.game-button--primary {
		--btn-surface: var(--vm-burnt-orange);
		--btn-text: var(--vm-parchment);
		--btn-bevel-light: color-mix(in srgb, var(--vm-burnt-orange) 70%, var(--vm-parchment));
		--btn-bevel-dark: color-mix(in srgb, var(--vm-burnt-orange) 72%, var(--vm-tobacco));
	}

	.game-button--secondary {
		--btn-surface: var(--vm-panel-command-bg);
		--btn-text: var(--vm-tobacco-black);
		--btn-outline-w: 2px;
		/* Bevels track --btn-surface so status tints (sage/amber/gray) carry through. */
		--btn-bevel-light: color-mix(in srgb, var(--btn-surface) 55%, var(--vm-parchment));
		--btn-bevel-dark: color-mix(in srgb, var(--btn-surface) 68%, var(--vm-tobacco));
	}

	.game-button--tertiary {
		--btn-surface: transparent;
		--btn-text: var(--vm-tobacco);
		filter: none;
	}

	.game-button--tertiary .game-button__face {
		min-height: 0;
		padding: var(--vm-space-xs) var(--vm-space-sm);
		background-image: none;
		justify-content: flex-start;
	}

	/* ---- cursor (tertiary + selected) ---- */

	.game-button__cursor {
		display: none;
		color: var(--vm-mustard);
		font-size: 0.75em;
	}

	.game-button--tertiary .game-button__cursor {
		display: inline-block;
		visibility: hidden; /* reserve the slot so labels don't shift */
	}

	.game-button--tertiary:hover:not(:disabled) .game-button__cursor,
	.game-button--tertiary:focus-visible:not(:disabled) .game-button__cursor,
	.game-button--selected .game-button__cursor {
		display: inline-block;
		visibility: visible;
		animation: vm-cursor-blink 1.1s steps(1) infinite;
	}

	/* ---- states ---- */

	.game-button--selected {
		--btn-accent: var(--vm-mustard);
		--btn-outline-w: 2px;
	}

	/* tertiary stays flat when selected — the cursor alone marks it */
	.game-button--tertiary.game-button--selected {
		--btn-outline-w: 0;
	}

	.game-button:hover:not(:disabled):not(.game-button--tertiary):not(:active),
	.game-button.game-button--force-hover:not(:disabled):not(.game-button--tertiary) {
		--btn-bevel-light: color-mix(in srgb, var(--btn-bevel-light, var(--vm-parchment)) 68%, var(--vm-parchment));
		transform: translateY(var(--btn-hover-lift, -1px));
		filter: var(--btn-state-filter, none)
			drop-shadow(0 calc(var(--btn-shadow-h) + 1px) 0 rgb(42 30 22 / 0.3));
	}

	.game-button--primary:hover:not(:disabled):not(:active),
	.game-button--primary.game-button--force-hover:not(:disabled) {
		--btn-bevel-light: color-mix(in srgb, var(--vm-burnt-orange) 52%, var(--vm-parchment));
	}

	/* tactile press: travel down, shadow collapses underneath (§3.2) */
	.game-button:active:not(:disabled),
	.game-button.game-button--force-active:not(:disabled) {
		transform: translateY(var(--btn-press-travel));
		filter: var(--btn-state-filter, none) drop-shadow(0 1px 0 rgb(42 30 22 / 0.28));
	}

	.game-button--tertiary:active:not(:disabled) {
		transform: translateY(1px);
		filter: none;
	}

	.game-button:disabled {
		cursor: not-allowed;
		opacity: 0.48;
		filter: grayscale(0.45) drop-shadow(0 var(--btn-shadow-h) 0 rgb(42 30 22 / 0.18));
	}

	.game-button:focus-visible,
	.game-button.game-button--force-focus:not(:disabled) {
		outline: 2px solid var(--vm-mustard);
		outline-offset: 3px;
	}
</style>
