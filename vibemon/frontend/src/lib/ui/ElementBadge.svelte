<script lang="ts">
	import { elementBadgeTextColor, elementTypeColor, elementTypeLabel } from './elementTypes';

	let { type, class: className = '' }: { type: string; class?: string } = $props();

	let badgeClass = $derived(['element-badge', className].filter(Boolean).join(' '));
	let label = $derived(elementTypeLabel(type));
	let background = $derived(elementTypeColor(type));
	let foreground = $derived(elementBadgeTextColor(type));
</script>

<span class={badgeClass} style:--badge-bg={background} style:--badge-fg={foreground}>{label}</span>

<style>
	.element-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.2rem 0.45rem;
		border: 2px solid color-mix(in srgb, var(--badge-fg) 28%, var(--vm-tobacco));
		border-radius: var(--vm-radius-sm);
		background-color: var(--badge-bg);
		background-image:
			radial-gradient(circle at 22% 28%, rgb(61 43 31 / 0.1) 1px, transparent 1px),
			radial-gradient(circle at 72% 68%, rgb(61 43 31 / 0.08) 1px, transparent 1px);
		background-size:
			5px 5px,
			7px 7px;
		color: var(--badge-fg);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1.35;
		letter-spacing: 0.06em;
		white-space: nowrap;
	}
</style>
