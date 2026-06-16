<script lang="ts">
	const BLOCK_COUNT = 4;

	let {
		current,
		max,
		label = 'HP',
		compact = false
	}: {
		current: number;
		max: number;
		label?: string;
		/** Roster bench: blocks + values only. */
		compact?: boolean;
	} = $props();

	let ratio = $derived(max > 0 ? Math.max(0, Math.min(1, current / max)) : 0);
	let filledBlocks = $derived(Math.round(ratio * BLOCK_COUNT));
	let tone = $derived(ratio <= 0.2 ? 'critical' : ratio <= 0.5 ? 'caution' : 'healthy');
</script>

<div
	class={['segmented-hp', compact && 'segmented-hp--compact'].filter(Boolean).join(' ')}
	aria-label="{label} {current} of {max}"
>
	{#if !compact}
		<span class="segmented-hp__label">{label}</span>
	{/if}
	<span class="segmented-hp__blocks" aria-hidden="true">
		{#each Array.from({ length: BLOCK_COUNT }, (_, index) => index) as block (block)}
			<span
				class={[
					'segmented-hp__block',
					block < filledBlocks && 'segmented-hp__block--filled',
					block < filledBlocks && `segmented-hp__block--${tone}`
				]
					.filter(Boolean)
					.join(' ')}
			></span>
		{/each}
	</span>
	<span class="segmented-hp__values">{current}/{max}</span>
</div>

<style>
	.segmented-hp {
		display: grid;
		grid-template-columns: auto 1fr auto;
		gap: 0.35rem 0.55rem;
		align-items: center;
		width: 100%;
		min-width: 0;
	}

	.segmented-hp--compact {
		grid-template-columns: 1fr auto;
	}

	.segmented-hp__label,
	.segmented-hp__values {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.75rem);
		line-height: 1.5;
		letter-spacing: 0.03em;
		font-variant-numeric: tabular-nums;
	}

	.segmented-hp__blocks {
		display: inline-flex;
		gap: 0.18rem;
		min-width: 0;
	}

	.segmented-hp__block {
		flex: 1 1 0;
		min-width: 0.55rem;
		height: clamp(0.55rem, 1.5vw, 0.75rem);
		border: 2px solid var(--vm-tobacco);
		background: color-mix(in srgb, var(--vm-tobacco) 30%, transparent);
		box-shadow: inset 0 1px 0 rgb(20 12 8 / 0.16);
	}

	.segmented-hp--compact .segmented-hp__block {
		min-width: 0.45rem;
		height: clamp(0.5rem, 1.35vw, 0.65rem);
	}

	.segmented-hp__block--filled.segmented-hp__block--healthy {
		background: var(--vm-status-sage);
	}

	.segmented-hp__block--filled.segmented-hp__block--caution {
		background: var(--vm-status-amber);
	}

	.segmented-hp__block--filled.segmented-hp__block--critical {
		background: var(--vm-status-brick);
	}
</style>
