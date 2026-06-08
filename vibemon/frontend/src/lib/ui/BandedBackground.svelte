<script lang="ts">
	let {
		top = '#c4a882',
		base = '#6b7a2a',
		shadow = 'var(--vm-tobacco)',
		warm = '#b8956a',
		deep = '#4a3428',
		class: className = ''
	}: {
		top?: string;
		base?: string;
		shadow?: string;
		warm?: string;
		deep?: string;
		class?: string;
	} = $props();

	let rootClass = $derived(['banded-bg', className].filter(Boolean).join(' '));
</script>

<div
	class={rootClass}
	style="--top: {top}; --base: {base}; --shadow: {shadow}; --warm: {warm}; --deep: {deep};"
	aria-hidden="true"
></div>

<style>
	.banded-bg {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		background-color: var(--top);
		background-image:
			linear-gradient(
				to bottom,
				color-mix(in srgb, var(--shadow) 7%, var(--top)) 0%,
				color-mix(in srgb, var(--top) 92%, var(--warm)) 2.5%,
				transparent 6%
			),
			radial-gradient(ellipse 96% 34% at 50% 0%, color-mix(in srgb, var(--warm) 28%, var(--top)) 0%, transparent 54%),
			radial-gradient(ellipse 26% 72% at -4% 30%, color-mix(in srgb, var(--warm) 18%, var(--top)) 0%, transparent 48%),
			radial-gradient(ellipse 26% 72% at 104% 30%, color-mix(in srgb, var(--warm) 18%, var(--top)) 0%, transparent 48%),
			radial-gradient(
				ellipse 118% 118% at 50% 46%,
				transparent 44%,
				color-mix(in srgb, color-mix(in srgb, var(--shadow) 68%, var(--warm)) 24%, transparent) 100%
			),
			linear-gradient(
				to bottom,
				color-mix(in srgb, var(--top) 91%, var(--warm)) 0%,
				var(--top) 30%,
				var(--top) 52.5%,

				color-mix(in srgb, var(--base) 5%, var(--top)) 58.5%,
				color-mix(in srgb, var(--base) 5%, var(--top)) 61.3%,
				color-mix(in srgb, var(--base) 12%, var(--top)) 61.3%,
				color-mix(in srgb, var(--base) 12%, var(--top)) 63.9%,
				color-mix(in srgb, var(--base) 22%, var(--top)) 63.9%,
				color-mix(in srgb, var(--base) 22%, var(--top)) 66.8%,
				color-mix(in srgb, var(--base) 34%, var(--top)) 66.8%,
				color-mix(in srgb, var(--base) 34%, var(--top)) 70.1%,
				color-mix(in srgb, var(--base) 48%, var(--top)) 70.1%,
				color-mix(in srgb, var(--base) 48%, var(--top)) 73.4%,
				color-mix(in srgb, var(--base) 64%, var(--top)) 73.4%,
				color-mix(in srgb, var(--base) 64%, var(--top)) 76.5%,
				color-mix(in srgb, var(--base) 82%, var(--top)) 76.5%,
				color-mix(in srgb, var(--base) 82%, var(--top)) 79.6%,
				var(--base) 79.6%,
				var(--base) 82%,

				var(--base) 92%,
				color-mix(in srgb, var(--base) 55%, var(--deep)) 100%
			);
		box-shadow:
			inset 0 0 0 clamp(4px, 0.7vw, 7px) color-mix(in srgb, var(--shadow) 88%, black),
			inset 0 0 clamp(14px, 3vw, 28px) color-mix(in srgb, var(--shadow) 28%, transparent);
		user-select: none;
		pointer-events: none;
	}

	/* Fine, even paper fiber — uniform speckle like the mockup, not localized stains */
	.banded-bg::after {
		content: '';
		position: absolute;
		inset: 0;
		opacity: 0.32;
		background-image:
			radial-gradient(circle, rgb(61 43 31 / 0.09) 0.5px, transparent 0.5px),
			radial-gradient(circle, rgb(61 43 31 / 0.06) 0.5px, transparent 0.5px),
			radial-gradient(circle, rgb(196 168 130 / 0.07) 0.5px, transparent 0.5px);
		background-size:
			3px 3px,
			5px 5px,
			4px 4px;
		background-position:
			0 0,
			1px 2px,
			2px 1px;
		pointer-events: none;
	}
</style>
