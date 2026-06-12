<script lang="ts">
	import { elementBadgeTextColor, elementTypeColor, elementTypeLabel } from '$lib/ui/elementTypes';

	import type { MoveSummary } from './hatchApi';

	const CATEGORY_LABEL: Record<string, string> = {
		physical: 'PHYSICAL',
		special: 'SPECIAL',
		status: 'STATUS'
	};

	let {
		move,
		review = false
	}: {
		move: MoveSummary;
		/** Hatch review card — name, type, category, PP/PWR; lore on hover. */
		review?: boolean;
	} = $props();

	let chipBg = $derived(elementTypeColor(move.element));
	let chipFg = $derived(elementBadgeTextColor(move.element));
	let typeLabel = $derived(elementTypeLabel(move.element));
	let categoryLabel = $derived(
		CATEGORY_LABEL[move.category.toLowerCase()] ?? move.category.toUpperCase()
	);
	let powerLabel = $derived(move.power == null ? '—' : String(move.power).padStart(2, '0'));
	let ppLabel = $derived(String(move.pp ?? 10).padStart(2, '0'));
</script>

<div class="move-pill" class:move-pill--review={review}>
	<span class="move-pill__name">{move.name}</span>
	<div class="move-pill__type-row">
		<span
			class="move-pill__type"
			style:--move-chip-bg={chipBg}
			style:--move-chip-fg={chipFg}
		>
			{typeLabel}
		</span>
	</div>
	<span class="move-pill__category">{categoryLabel}</span>
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
		border: 2px solid color-mix(in srgb, var(--vm-tobacco) 22%, transparent);
		border-radius: var(--vm-radius-sm);
		background: color-mix(in srgb, var(--vm-parchment) 88%, var(--vm-panel-command-bg));
		background-image: radial-gradient(circle at 22% 28%, rgb(61 43 31 / 0.06) 1px, transparent 1px);
		background-size: 6px 6px;
		min-width: 0;
		height: 100%;
		box-sizing: border-box;
	}

	.move-pill__name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: clamp(0.625rem, 1.8vw, 0.75rem);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.04em;
		color: var(--vm-tobacco-black);
	}

	.move-pill__type-row {
		display: flex;
		align-items: center;
	}

	.move-pill__type {
		display: inline-flex;
		align-items: center;
		padding: 0.14rem 0.44rem;
		border: 1px solid color-mix(in srgb, var(--move-chip-fg) 28%, var(--vm-tobacco));
		border-radius: var(--vm-radius-sm);
		background: var(--move-chip-bg);
		color: var(--move-chip-fg);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1.35;
		letter-spacing: 0.06em;
	}

	.move-pill__category {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5rem, 1.45vw, 0.625rem);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.08em;
		color: color-mix(in srgb, var(--vm-tobacco) 68%, var(--vm-brass));
	}

	.move-pill__stats {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.5rem;
		margin-top: auto;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1;
		letter-spacing: 0.04em;
		color: color-mix(in srgb, var(--vm-tobacco) 78%, var(--vm-brass));
		font-variant-numeric: tabular-nums;
	}

	.move-pill--review {
		grid-template-rows: auto auto auto 1fr;
		min-height: 5.5rem;
	}
</style>
