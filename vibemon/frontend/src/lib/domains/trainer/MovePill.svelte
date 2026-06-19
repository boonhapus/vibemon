<script lang="ts">
	import ElementBadge from '$lib/ui/ElementBadge.svelte';

	import type { MoveSummary } from './hatchApi';

	/** Category chip colors — mirrors the battle move menu (moveCategoryStyles.ts). */
	const CATEGORY_STYLES: Record<string, { label: string; bg: string; fg: string }> = {
		physical: { label: 'PHYSICAL', bg: '#8b3a2a', fg: 'var(--vm-parchment)' },
		special: { label: 'SPECIAL', bg: 'var(--vm-plum)', fg: 'var(--vm-parchment)' },
		status: { label: 'STATUS', bg: 'var(--vm-status-amber)', fg: 'var(--vm-tobacco)' }
	};

	let {
		move,
		review = false
	}: {
		move: MoveSummary;
		/** Hatch review card — name, type, category, PP/PWR; lore on hover. */
		review?: boolean;
	} = $props();

	let category = $derived(
		CATEGORY_STYLES[move.category.toLowerCase()] ?? {
			label: move.category.toUpperCase(),
			bg: 'var(--vm-tobacco)',
			fg: 'var(--vm-parchment)'
		}
	);
	let powerLabel = $derived(move.power == null ? '—' : String(move.power).padStart(2, '0'));
	let ppLabel = $derived(String(move.pp ?? 10).padStart(2, '0'));
</script>

<div class="move-pill" class:move-pill--review={review}>
	<span class="move-pill__name">{move.name}</span>
	<div class="move-pill__badge-row">
		<ElementBadge type={move.element} class="move-pill__element" />
		<span
			class="move-pill__category"
			style:--badge-bg={category.bg}
			style:--badge-fg={category.fg}
		>
			{category.label}
		</span>
	</div>
	<div class="move-pill__stats" aria-label="Move power and PP">
		<span>PP {ppLabel}</span>
		<span>PWR {powerLabel}</span>
	</div>
</div>

<style>
	.move-pill {
		display: grid;
		gap: 0.34rem;
		padding: 0.5rem 0.55rem;
		border: 2px solid var(--vm-crew-readout-inset-border);
		border-radius: var(--vm-radius-sm);
		background: var(--vm-crew-readout-inset-surface);
		background-image: radial-gradient(circle at 22% 28%, rgb(61 43 31 / 0.06) 1px, transparent 1px);
		background-size: 6px 6px;
		box-shadow: inset 0 0 0 1px var(--vm-crew-readout-inset-border);
		min-width: 0;
		height: 100%;
		box-sizing: border-box;
	}

	.move-pill__name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-family: var(--vm-font-body);
		font-size: var(--vm-crew-readout-value);
		font-weight: 600;
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.02em;
		color: var(--vm-tobacco-black);
	}

	.move-pill__badge-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.3rem;
		min-width: 0;
	}

	/* Category chip — sized to match ElementBadge so the element and category
	   badges read as the same size (mirrors the battle move menu). */
	.move-pill__category {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.2rem 0.45rem;
		border: 2px solid color-mix(in srgb, var(--badge-fg) 28%, var(--vm-tobacco));
		border-radius: var(--vm-radius-sm);
		background: var(--badge-bg);
		color: var(--badge-fg);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1.35;
		letter-spacing: 0.06em;
		white-space: nowrap;
	}

	.move-pill__stats {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.5rem;
		margin-top: auto;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.5vw, 0.6875rem);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.04em;
		color: var(--vm-crew-readout-muted-color);
		font-variant-numeric: tabular-nums;
	}

	.move-pill--review {
		grid-template-rows: auto auto 1fr;
		min-height: 5.5rem;
	}
</style>
