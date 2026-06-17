<script lang="ts">
	import PixelIcon, { type PixelIconName } from '$lib/ui/PixelIcon.svelte';

	/**
	 * One signal input on the hatch console's patch panel (ui-cohesion-plan §3).
	 * Visibly an *input* jack, not storage: pewter socket, mustard plug, status lamp.
	 */
	export type ProviderPatchState = 'connected' | 'needs-config' | 'disabled';

	let {
		label,
		icon,
		state,
		fetching = false,
		blocked = false,
		ariaLabel,
		testId,
		onclick,
		onpointerdown,
		onpointerup,
		onpointerleave,
		onpointercancel,
		onmouseenter,
		onmouseleave,
		onfocus,
		onblur,
		oncontextmenu
	}: {
		label: string;
		icon: PixelIconName;
		state: ProviderPatchState;
		fetching?: boolean;
		blocked?: boolean;
		ariaLabel?: string;
		testId?: string;
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
	} = $props();
</script>

<button
	type="button"
	class={['provider-patch-row', `provider-patch-row--${state}`]}
	class:provider-patch-row--fetching={fetching}
	class:provider-patch-row--blocked={blocked}
	aria-label={ariaLabel}
	aria-pressed={state === 'connected' || undefined}
	data-testid={testId}
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
>
	<span class="provider-patch-row__jack" aria-hidden="true">
		<span class="provider-patch-row__plug"></span>
	</span>
	<PixelIcon name={icon} class="provider-patch-row__glyph" />
	<span class="provider-patch-row__label">{label}</span>
	<span class="provider-patch-row__lamp" aria-hidden="true"></span>
</button>

<style>
	.provider-patch-row {
		--patch-lamp: color-mix(in srgb, var(--vm-tobacco) 30%, var(--vm-panel-command-bg));
		--patch-text: var(--vm-tobacco-black);

		display: grid;
		grid-template-columns: auto auto 1fr auto;
		align-items: center;
		gap: clamp(0.4rem, 1.2vw, 0.6rem);
		box-sizing: border-box;
		width: 100%;
		min-height: 44px; /* touch target floor (DESIGN.md §5.4) */
		margin: 0;
		padding: var(--vm-space-xs) var(--vm-space-sm);
		border: 0;
		border-bottom: 2px solid color-mix(in srgb, var(--vm-tobacco) 18%, transparent);
		background: transparent;
		color: var(--patch-text);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.625rem, 1.9vw, 0.8125rem);
		letter-spacing: 0.06em;
		text-align: left;
		cursor: pointer;
		-webkit-tap-highlight-color: transparent;
	}

	.provider-patch-row:last-child {
		border-bottom: 0;
	}

	.provider-patch-row:hover:not(.provider-patch-row--disabled),
	.provider-patch-row:focus-visible:not(.provider-patch-row--disabled) {
		background: color-mix(in srgb, var(--vm-parchment) 55%, transparent);
	}

	/* Pressed state: the row seats into the panel (touch has no hover). */
	.provider-patch-row:active:not(.provider-patch-row--disabled) {
		transform: translateY(1px);
		background: color-mix(in srgb, var(--vm-tobacco) 10%, transparent);
	}

	.provider-patch-row:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: -2px;
	}

	/* ---- jack: pewter-rimmed socket recessed into the plate ---- */

	.provider-patch-row__jack {
		position: relative;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: var(--vm-tobacco-black);
		box-shadow:
			inset 0 1px 2px rgb(20 12 8 / 0.7),
			0 0 0 2px var(--vm-pewter),
			0 1px 0 rgb(240 231 206 / 0.4);
	}

	/* Plug: soft mustard tip, seated only when the source is connected. */
	.provider-patch-row__plug {
		position: absolute;
		inset: 4px;
		border-radius: 50%;
		background: radial-gradient(
			circle at 35% 30%,
			color-mix(in srgb, var(--vm-mustard) 70%, var(--vm-parchment)),
			var(--vm-mustard) 60%,
			color-mix(in srgb, var(--vm-mustard) 70%, var(--vm-tobacco))
		);
		opacity: 0;
	}

	.provider-patch-row--connected .provider-patch-row__plug {
		opacity: 1;
	}

	/* Unimplemented: dashed empty recess, no plug, plate text recedes. */
	.provider-patch-row--disabled {
		--patch-text: color-mix(in srgb, var(--vm-tobacco) 45%, var(--vm-panel-command-bg));
		cursor: not-allowed;
	}

	.provider-patch-row--blocked:not(.provider-patch-row--disabled) {
		opacity: 0.72;
		cursor: not-allowed;
	}

	.provider-patch-row--disabled .provider-patch-row__jack {
		background: color-mix(in srgb, var(--vm-tobacco) 14%, var(--vm-panel-command-bg));
		box-shadow: none;
		border: 2px dashed color-mix(in srgb, var(--vm-tobacco) 40%, transparent);
	}

	/* ---- glyph + label ---- */

	:global(.provider-patch-row__glyph) {
		width: 16px;
		height: 16px;
		color: color-mix(in srgb, var(--vm-tobacco) 80%, var(--vm-brass));
	}

	.provider-patch-row--disabled :global(.provider-patch-row__glyph) {
		color: var(--patch-text);
	}

	.provider-patch-row__label {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	/* ---- status lamp (DESIGN.md §2.3) ---- */

	.provider-patch-row__lamp {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--patch-lamp);
		box-shadow:
			inset 0 -1px 1px rgb(20 12 8 / 0.4),
			0 0 0 1px color-mix(in srgb, var(--vm-tobacco) 50%, transparent);
	}

	.provider-patch-row--connected {
		--patch-lamp: var(--vm-status-sage);
	}

	.provider-patch-row--needs-config {
		--patch-lamp: var(--vm-status-amber);
	}

	.provider-patch-row--connected .provider-patch-row__lamp {
		box-shadow:
			inset 0 -1px 1px rgb(20 12 8 / 0.4),
			0 0 0 1px color-mix(in srgb, var(--vm-tobacco) 50%, transparent),
			0 0 6px color-mix(in srgb, var(--vm-status-sage) 60%, transparent);
	}

	.provider-patch-row--fetching {
		--patch-lamp: var(--vm-status-amber);
	}

	.provider-patch-row--fetching .provider-patch-row__lamp {
		animation: provider-patch-lamp-blink 900ms steps(2, jump-none) infinite;
	}

	@keyframes provider-patch-lamp-blink {
		0% {
			opacity: 1;
		}
		100% {
			opacity: 0.35;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.provider-patch-row--fetching .provider-patch-row__lamp {
			animation: none;
		}
	}
</style>
