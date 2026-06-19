<script lang="ts">
	import type { BaseStats } from './hatchApi';

	let {
		stats,
		size = 120
	}: {
		stats: BaseStats;
		size?: number;
	} = $props();

	const labels = [
		{ key: 'hp', label: 'HP' },
		{ key: 'attack', label: 'ATK' },
		{ key: 'defense', label: 'DEF' },
		{ key: 'speed', label: 'SPD' },
		{ key: 'sp_defense', label: 'SpD' },
		{ key: 'sp_attack', label: 'SpA' }
	] as const;

	let pad = $derived(size * 0.13);
	let center = $derived(size / 2);
	let radius = $derived(size * 0.4);
	let labelRadius = $derived(size * 0.53);
	let maxStat = $derived(Math.max(...labels.map(({ key }) => stats[key]), 1));

	function point(index: number, value: number) {
		const angle = vertexAngle(index);
		const distance = (value / maxStat) * radius;
		return {
			x: center + Math.cos(angle) * distance,
			y: center + Math.sin(angle) * distance
		};
	}

	function vertexAngle(index: number) {
		return (Math.PI * 2 * index) / labels.length - Math.PI / 2;
	}

	function labelPoint(index: number) {
		const angle = vertexAngle(index);
		return {
			x: center + Math.cos(angle) * labelRadius,
			y: center + Math.sin(angle) * labelRadius
		};
	}

	let polygon = $derived(
		labels
			.map(({ key }, index) => {
				const { x, y } = point(index, stats[key]);
				return `${x},${y}`;
			})
			.join(' ')
	);

	let gridLevels = [0.25, 0.5, 0.75, 1];
</script>

<svg
	class="bst-radar"
	width={size + pad * 2}
	height={size + pad * 2}
	viewBox="{-pad} {-pad} {size + pad * 2} {size + pad * 2}"
	style:--bst-radar-size="{size}px"
	role="img"
	aria-label="Base stat radar chart"
>
	{#each gridLevels as level (level)}
		<polygon
			class="bst-radar__grid"
			points={labels
				.map((_, index) => {
					const { x, y } = point(index, maxStat * level);
					return `${x},${y}`;
				})
				.join(' ')}
		/>
	{/each}

	<polygon class="bst-radar__fill" points={polygon} />

	{#each labels as label, index (label.key)}
		{@const outer = labelPoint(index)}
		<text
			class="bst-radar__label"
			x={outer.x}
			y={outer.y}
			text-anchor="middle"
			dominant-baseline="middle"
		>
			{label.label}
		</text>
	{/each}
</svg>

<style>
	.bst-radar {
		display: block;
		overflow: visible;
	}

	.bst-radar__grid {
		fill: none;
		stroke: color-mix(in srgb, var(--vm-tobacco) 32%, transparent);
		stroke-width: 1;
	}

	.bst-radar__fill {
		fill: color-mix(in srgb, var(--vm-crew-readout-fill) 42%, transparent);
		stroke: var(--vm-crew-readout-fill);
		stroke-width: 2;
	}

	.bst-radar__label {
		font-family: var(--vm-font-ui);
		font-size: var(--vm-crew-readout-subtitle);
		font-weight: 700;
		fill: color-mix(in srgb, var(--vm-tobacco) 90%, var(--vm-brass));
		letter-spacing: 0.06em;
	}
</style>
