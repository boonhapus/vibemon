<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * Provider patch panel on the hatch console (ui-cohesion-plan §3): a parchment
	 * plate of input jacks mounted flush on the right HUD rail — wood-grain lip
	 * on the left so it reads as cabinet hardware, not a floating island.
	 */
	let {
		children,
		title = 'Vibe sources',
		fill = false,
		ariaLabel = 'Vibe providers',
		class: className = ''
	}: {
		children: Snippet;
		title?: string | false;
		fill?: boolean;
		ariaLabel?: string;
		class?: string;
	} = $props();

	let panelClass = $derived(
		['provider-patch-panel', fill && 'provider-patch-panel--fill', className].filter(Boolean).join(' ')
	);
</script>

<div class={panelClass} role="group" aria-label={ariaLabel}>
	<div class="provider-patch-panel__rail" aria-hidden="true"></div>
	<div class="provider-patch-panel__body">
		{#if title}
			<span class="provider-patch-panel__title" aria-hidden="true">{title}</span>
		{/if}
		<div class="provider-patch-panel__rows">
			{@render children()}
		</div>
	</div>
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
