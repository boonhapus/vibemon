<script lang="ts">
	import type { Snippet } from 'svelte';

	import { cabinetMetaStore } from '$lib/domains/game/cabinetMetaStore.svelte';
	import { gameSolarContext } from '$lib/domains/game/gameSolarContext.svelte';

	let {
		meta
	}: {
		meta?: Snippet;
	} = $props();

	const phaseLabel = $derived(gameSolarContext.phase.toUpperCase());

	function formatClock(at: Date): string {
		return at.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
	}

	let clock = $state(formatClock(new Date()));

	$effect(() => {
		const id = setInterval(() => {
			clock = formatClock(new Date());
		}, 30_000);
		return () => clearInterval(id);
	});
</script>

<div
	class="cabinet-guide-panel"
	class:cabinet-guide-panel--open={cabinetMetaStore.expanded}
	role="region"
	aria-label="Guide readout"
	aria-hidden={!cabinetMetaStore.expanded}
>
	<div class="cabinet-guide-panel__drop">
		<div class="cabinet-guide-panel__surface">
			{#if meta}
				<div class="cabinet-guide-panel__custom">
					{@render meta()}
				</div>
			{:else}
				<dl class="cabinet-guide-panel__grid">
					<div class="cabinet-guide-panel__item">
						<dt class="cabinet-guide-panel__label">Trainer</dt>
						<dd class="cabinet-guide-panel__value">—</dd>
					</div>
					<div class="cabinet-guide-panel__item">
						<dt class="cabinet-guide-panel__label">Online</dt>
						<dd class="cabinet-guide-panel__value">—</dd>
					</div>
					<div class="cabinet-guide-panel__item">
						<dt class="cabinet-guide-panel__label">Nearby</dt>
						<dd class="cabinet-guide-panel__value">—</dd>
					</div>
					<div class="cabinet-guide-panel__item">
						<dt class="cabinet-guide-panel__label">Time</dt>
						<dd class="cabinet-guide-panel__value">{phaseLabel}</dd>
						<dd class="cabinet-guide-panel__value cabinet-guide-panel__value--sub">{clock}</dd>
					</div>
					<div class="cabinet-guide-panel__item cabinet-guide-panel__item--wide">
						<dt class="cabinet-guide-panel__label">Keys</dt>
						<dd class="cabinet-guide-panel__value">—</dd>
					</div>
				</dl>
			{/if}
		</div>
		<div class="cabinet-guide-panel__wood-lip" aria-hidden="true"></div>
	</div>
</div>

<style>
	/* Collapsed: hidden — expanding top rail is pure wood (SceneFrame bezel).
	   Open: bezel descends first; parchment trails; bottom wood lip matches --vm-bezel-w. */
	.cabinet-guide-panel {
		position: absolute;
		top: 0;
		left: var(--vm-bezel-w);
		right: var(--vm-bezel-w);
		z-index: 3;
		height: 0;
		overflow: hidden;
		pointer-events: none;
	}

	.cabinet-guide-panel--open {
		height: var(--vm-bezel-guide-h);
		transition: height var(--vm-guide-reveal-duration) steps(var(--anim-ui-reveal-steps), jump-none)
			0ms;
	}

	.cabinet-guide-panel:not(.cabinet-guide-panel--open) {
		transition: height var(--vm-guide-reveal-duration) steps(var(--anim-ui-reveal-steps), jump-none)
			var(--vm-guide-stagger);
	}

	.cabinet-guide-panel__drop {
		display: flex;
		flex-direction: column;
		height: var(--vm-bezel-guide-h);
		min-height: var(--vm-bezel-guide-h);
	}

	.cabinet-guide-panel__surface {
		flex: 1;
		min-height: 0;
		display: flex;
		align-items: stretch;
		padding: var(--vm-guide-surface-pad-top) var(--vm-space-sm) var(--vm-space-xs);
		box-sizing: border-box;
		background: var(--vm-cabinet-guide-surface);
		box-shadow: inset 0 0 0 1px rgb(42 30 22 / 0.08);
		transform: translateY(-100%);
	}

	.cabinet-guide-panel--open .cabinet-guide-panel__surface {
		transform: translateY(0);
		transition: transform var(--vm-guide-reveal-duration) steps(var(--anim-ui-reveal-steps), jump-none)
			var(--vm-guide-stagger);
	}

	.cabinet-guide-panel:not(.cabinet-guide-panel--open) .cabinet-guide-panel__surface {
		transition: transform var(--vm-guide-reveal-duration) steps(var(--anim-ui-reveal-steps), jump-none)
			0ms;
	}

	.cabinet-guide-panel__wood-lip {
		flex: 0 0 var(--vm-bezel-w);
		background: var(--vm-cabinet-wood-grain-flat);
		box-shadow: inset 0 1px 0 rgb(240 231 206 / 0.12);
	}

	.cabinet-guide-panel__custom {
		display: flex;
		align-items: center;
		width: 100%;
		min-width: 0;
		padding: var(--vm-space-xs) var(--vm-space-sm);
		box-sizing: border-box;
		color: var(--vm-tobacco-black);
	}

	.cabinet-guide-panel__grid {
		margin: 0;
		width: 100%;
		min-width: 0;
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: var(--vm-space-xs) var(--vm-space-md);
		padding: 0 clamp(var(--vm-space-sm), 2vw, var(--vm-space-md))
			var(--vm-space-xs);
		align-content: start;
		color: var(--vm-tobacco-black);
	}

	.cabinet-guide-panel__item {
		display: flex;
		flex-direction: column;
		gap: 3px;
		min-width: 0;
	}

	.cabinet-guide-panel__item--wide {
		grid-column: span 1;
	}

	.cabinet-guide-panel__label {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.4375rem, 1.4vw, 0.5625rem);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: color-mix(in srgb, var(--vm-tobacco) 78%, var(--vm-plum));
	}

	.cabinet-guide-panel__value {
		margin: 0;
		font-family: var(--vm-font-body);
		font-size: clamp(0.8125rem, 2.2vw, var(--vm-text-caption));
		line-height: var(--vm-leading-tight);
		color: var(--vm-tobacco-black);
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.cabinet-guide-panel__value--sub {
		font-size: clamp(0.75rem, 2vw, 0.875rem);
		color: color-mix(in srgb, var(--vm-tobacco-black) 82%, var(--vm-brass));
	}

	@media (max-width: 720px) {
		.cabinet-guide-panel__grid {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}

		.cabinet-guide-panel__item--wide {
			grid-column: 1 / -1;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.cabinet-guide-panel,
		.cabinet-guide-panel--open,
		.cabinet-guide-panel__surface {
			transition: none;
		}
	}
</style>
