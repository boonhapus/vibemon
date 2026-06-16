<script lang="ts">
	import type { EvolutionLine } from './hatchApi';

	let { line }: { line: EvolutionLine } = $props();

	let slots = $derived.by(() => {
		const count = Math.max(line.form_count, 1);
		const filled = Math.min(Math.max(line.form_index, 1), count);
		const pips: ('filled' | 'empty')[] = [];
		for (let i = 0; i < count; i++) {
			pips.push(i < filled ? 'filled' : 'empty');
		}
		return pips;
	});

	let showDeepMark = $derived(line.line_rarity === 'deep' && line.form_count >= 3);
</script>

<span class="evo-line-pips" aria-hidden="true">
	{#each slots as slot, index (index)}
		<span class="evo-line-pips__pip" class:evo-line-pips__pip--filled={slot === 'filled'}>◆</span>
	{/each}
	{#if showDeepMark}
		<span class="evo-line-pips__deep">✦</span>
	{/if}
</span>

<style>
	.evo-line-pips {
		display: inline-flex;
		align-items: center;
		gap: 0.12em;
		font-size: 0.72em;
		line-height: 1;
		letter-spacing: 0.02em;
		transform: translateY(0.04em);
	}

	.evo-line-pips__pip {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		line-height: 1;
		color: color-mix(in srgb, var(--vm-tobacco) 28%, var(--vm-panel-command-bg));
	}

	.evo-line-pips__pip--filled {
		color: color-mix(in srgb, var(--vm-status-sage) 72%, var(--vm-tobacco));
	}

	.evo-line-pips__deep {
		margin-left: 0.08em;
		color: var(--vm-mustard);
		text-shadow: 0 0 0.35em color-mix(in srgb, var(--vm-burnt-orange) 45%, transparent);
		animation: evo-line-deep-pulse 1.8s ease-in-out infinite;
	}

	@keyframes evo-line-deep-pulse {
		0%,
		100% {
			opacity: 1;
			transform: scale(1);
			text-shadow: 0 0 0.35em color-mix(in srgb, var(--vm-burnt-orange) 45%, transparent);
		}

		50% {
			opacity: 0.82;
			transform: scale(1.14);
			text-shadow: 0 0 0.6em color-mix(in srgb, var(--vm-burnt-orange) 72%, transparent);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.evo-line-pips__deep {
			animation: none;
		}
	}
</style>
