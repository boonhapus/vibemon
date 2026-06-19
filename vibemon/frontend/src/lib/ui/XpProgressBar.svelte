<script lang="ts">
	let {
		ratio,
		label = 'XP',
		value
	}: {
		ratio: number;
		label?: string;
		/** Optional trailing readout (e.g. "42%") shown right of the track. */
		value?: string;
	} = $props();

	let fillRatio = $derived(Math.max(0, Math.min(1, ratio)));
</script>

<div class="xp-progress" aria-label="{label} progress">
	<span class="xp-progress__label">{label}</span>
	<span class="xp-progress__track" aria-hidden="true">
		<span class="xp-progress__fill" style:width="max(2px, {fillRatio * 100}%)"></span>
	</span>
	{#if value}<span class="xp-progress__value">{value}</span>{/if}
</div>

<style>
	.xp-progress {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.35rem 0.45rem;
		align-items: center;
		width: 100%;
		min-width: 0;
	}

	.xp-progress__label {
		font-family: var(--vm-font-ui);
		font-size: var(--vm-crew-readout-subtitle);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.05em;
		text-transform: uppercase;
		color: var(--vm-crew-readout-subtitle-color);
	}

	.xp-progress__track {
		display: block;
		height: clamp(0.45rem, 1vw, 0.6rem);
		border: 1px solid var(--vm-tobacco);
		background: color-mix(in srgb, var(--vm-tobacco) 18%, transparent);
		overflow: hidden;
	}

	.xp-progress__fill {
		display: block;
		height: 100%;
		background: var(--vm-plum);
	}
</style>
