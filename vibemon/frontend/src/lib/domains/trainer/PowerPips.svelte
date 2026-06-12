<script lang="ts">
	let {
		pips,
		label = 'Strength',
		compact = false
	}: {
		pips: 1 | 2 | 3;
		label?: string;
		/** Pips only — label lives in hover hint. */
		compact?: boolean;
	} = $props();

	let filled = $derived(Math.min(Math.max(pips, 1), 3));
</script>

<div class="power-pips" class:power-pips--compact={compact} role="img" aria-label="{label}: {filled} of 3">
	{#if !compact}
		<span class="power-pips__label">{label}</span>
	{/if}
	<span class="power-pips__blocks" aria-hidden="true">
		{#each [1, 2, 3] as block (block)}
			<span class="power-pips__block" class:power-pips__block--filled={block <= filled}></span>
		{/each}
	</span>
</div>

<style>
	.power-pips {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
	}

	.power-pips__label {
		font-size: var(--vm-text-caption);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.05em;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-brass));
	}

	.power-pips__blocks {
		display: inline-flex;
		gap: var(--hatch-pip-gap, 0.28rem);
	}

	.power-pips__block {
		width: var(--hatch-pip-block-w, 0.72rem);
		height: var(--hatch-pip-block-h, 0.55rem);
		border-radius: 1px;
		background: color-mix(in srgb, var(--vm-tobacco) 30%, var(--vm-panel-command-bg));
		box-shadow: inset 0 1px 0 rgb(20 12 8 / 0.18);
	}

	.power-pips__block--filled {
		background: var(--vm-status-sage);
		box-shadow:
			inset 0 -1px 0 rgb(20 12 8 / 0.22),
			0 0 0 1px color-mix(in srgb, var(--vm-tobacco) 35%, transparent);
	}
</style>
