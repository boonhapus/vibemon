<script lang="ts">
	import type { Snippet } from 'svelte';

	/** Where the wood rail sits relative to the parchment plate. */
	export type ProviderPatchMount = 'edge-left' | 'corner-tl';

	/**
	 * Provider patch panel on the hatch console (ui-cohesion-plan §3): a parchment
	 * plate mounted flush on a HUD rail — wood-grain lip on the open edge(s) so it
	 * reads as cabinet hardware, not a floating island.
	 *
	 * `edge-left` — right-side stack (hatch candidate / provider jacks): left rail.
	 * `corner-tl` — top-left dock: top/left open into the cabinet bezel; rails on right + bottom.
	 */
	let {
		children,
		title = 'Vibe sources',
		fill = false,
		mount = 'edge-left',
		ariaLabel = 'Vibe providers',
		class: className = ''
	}: {
		children: Snippet;
		title?: string | false;
		fill?: boolean;
		mount?: ProviderPatchMount;
		ariaLabel?: string;
		class?: string;
	} = $props();

	let panelClass = $derived(
		[
			'provider-patch-panel',
			fill && 'provider-patch-panel--fill',
			mount === 'corner-tl' && 'provider-patch-panel--corner-tl',
			className
		]
			.filter(Boolean)
			.join(' ')
	);
</script>

{#snippet plateBody()}
	<div class="provider-patch-panel__body">
		{#if title}
			<span class="provider-patch-panel__title" aria-hidden="true">{title}</span>
		{/if}
		<div class="provider-patch-panel__rows">
			{@render children()}
		</div>
	</div>
{/snippet}

<div class={panelClass} role="group" aria-label={ariaLabel}>
	{#if mount === 'corner-tl'}
		{@render plateBody()}
		<div class="provider-patch-panel__rail provider-patch-panel__rail--right" aria-hidden="true"></div>
		<div class="provider-patch-panel__rail provider-patch-panel__rail--bottom" aria-hidden="true"></div>
	{:else}
		<div class="provider-patch-panel__rail" aria-hidden="true"></div>
		{@render plateBody()}
	{/if}
</div>

<style>
	.provider-patch-panel {
		box-sizing: border-box;
		display: grid;
		grid-template-columns: var(--vm-hud-panel-rail-thickness) minmax(0, 1fr);
		width: 100%;
		min-width: 0;
		min-height: 100%;
		background: transparent;
		border-bottom: var(--vm-hud-panel-rail-thickness) solid rgb(42 30 22 / 0.55);
	}

	.provider-patch-panel--corner-tl {
		grid-template-columns: minmax(0, 1fr) var(--vm-hud-panel-rail-thickness);
		grid-template-rows: minmax(0, 1fr) var(--vm-hud-panel-rail-thickness);
		border-bottom: 0;
	}

	.provider-patch-panel--fill {
		flex: 1;
		height: 100%;
		min-height: var(--vm-hud-candidate-panel-min-height);
	}

	.provider-patch-panel--fill .provider-patch-panel__body,
	.provider-patch-panel--fill .provider-patch-panel__rows {
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.provider-patch-panel--fill .provider-patch-panel__body {
		height: 100%;
	}

	.provider-patch-panel--fill .provider-patch-panel__rows {
		flex: 1;
	}

	.provider-patch-panel__rail {
		background: var(--vm-cabinet-wood-grain);
		box-shadow:
			inset -2px 0 6px rgb(20 12 8 / 0.35),
			inset 0 1px 0 rgb(240 231 206 / 0.12);
	}

	.provider-patch-panel--corner-tl .provider-patch-panel__rail--right {
		grid-column: 2;
		grid-row: 1;
		box-shadow:
			inset 2px 0 6px rgb(20 12 8 / 0.35),
			inset 0 -1px 0 rgb(240 231 206 / 0.12);
	}

	.provider-patch-panel--corner-tl .provider-patch-panel__rail--bottom {
		grid-column: 1 / -1;
		grid-row: 2;
		box-shadow:
			inset 0 2px 6px rgb(20 12 8 / 0.35),
			inset -1px 0 0 rgb(240 231 206 / 0.12);
	}

	.provider-patch-panel--corner-tl .provider-patch-panel__body {
		grid-column: 1;
		grid-row: 1;
		border-top: 0;
	}

	.provider-patch-panel__body {
		box-sizing: border-box;
		padding:
			var(--provider-patch-pad-top, var(--provider-patch-pad, var(--vm-space-sm)))
			var(--provider-patch-pad-inline, var(--provider-patch-pad, var(--vm-space-sm)))
			var(--provider-patch-pad-bottom, var(--provider-patch-pad, var(--vm-space-sm)));
		background-color: var(--vm-panel-command-bg);
		background-image: radial-gradient(circle at 25% 30%, rgb(61 43 31 / 0.05) 1px, transparent 1px);
		background-size: 7px 7px;
		border-top: 2px solid rgb(42 30 22 / 0.55);
		box-shadow:
			inset 0 0 0 1px color-mix(in srgb, var(--vm-parchment) 60%, transparent),
			inset 0 2px 10px rgb(42 30 22 / 0.08);
	}

	/* Engraved plate label. */
	.provider-patch-panel__title {
		display: block;
		margin: 0 0 var(--vm-space-xs);
		font-family: var(--vm-font-ui);
		font-size: 0.5rem;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-panel-command-bg));
		text-shadow: 0 1px 0 rgb(240 231 206 / 0.45);
	}

	.provider-patch-panel__rows {
		display: flex;
		flex-direction: column;
	}
</style>
