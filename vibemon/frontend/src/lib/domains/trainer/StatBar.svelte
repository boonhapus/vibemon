<script lang="ts">
	let {
		label,
		value,
		pips
	}: {
		label: string;
		value: number;
		pips: 1 | 2 | 3;
	} = $props();

	let filled = $derived(Math.min(Math.max(pips, 1), 3));
</script>

<div class="stat-bar">
	<div class="stat-bar__readout">
		<span class="stat-bar__label">{label}</span>
		<span class="stat-bar__value">{value}</span>
	</div>
	<span class="stat-bar__blocks" aria-hidden="true">
		{#each [1, 2, 3] as block (block)}
			<span class="stat-bar__block" class:stat-bar__block--filled={block <= filled}></span>
		{/each}
	</span>
</div>

<style>
	.stat-bar {
		display: grid;
		grid-template-columns: minmax(0, 1fr) var(--hatch-pip-track-width, calc(3 * 0.72rem + 2 * 0.28rem));
		align-items: center;
		column-gap: var(--hatch-readout-pip-gap, 0.55rem);
		width: 100%;
		min-width: 0;
	}

	.stat-bar__readout {
		display: flex;
		flex-direction: row;
		justify-content: flex-end;
		align-items: baseline;
		min-width: 0;
		gap: 0.3rem;
		text-align: right;
	}

	.stat-bar__label {
		font-size: clamp(0.5rem, 1.45vw, 0.625rem);
		line-height: 1;
		letter-spacing: 0.07em;
		font-weight: 400;
		color: color-mix(in srgb, var(--vm-plum) 42%, var(--vm-brass));
		text-align: right;
		white-space: nowrap;
	}

	.stat-bar__value {
		font-size: clamp(0.625rem, 1.75vw, 0.75rem);
		line-height: 1;
		letter-spacing: 0.04em;
		font-weight: 700;
		color: var(--vm-tobacco-black);
		font-variant-numeric: tabular-nums;
		text-align: right;
		min-width: 1.75rem;
		flex-shrink: 0;
	}

	.stat-bar__blocks {
		display: inline-flex;
		justify-content: flex-end;
		gap: var(--hatch-pip-gap, 0.28rem);
		width: 100%;
	}

	.stat-bar__block {
		width: var(--hatch-pip-block-w, 0.72rem);
		height: var(--hatch-pip-block-h, 0.55rem);
		border-radius: 1px;
		background: color-mix(in srgb, var(--vm-tobacco) 30%, var(--vm-panel-command-bg));
		box-shadow: inset 0 1px 0 rgb(20 12 8 / 0.18);
	}

	.stat-bar__block--filled {
		background: var(--vm-status-sage);
		box-shadow:
			inset 0 -1px 0 rgb(20 12 8 / 0.22),
			0 0 0 1px color-mix(in srgb, var(--vm-tobacco) 35%, transparent);
	}
</style>
