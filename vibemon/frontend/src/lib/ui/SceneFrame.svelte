<script lang="ts">
	import type { Snippet } from 'svelte';

	import BandedBackground from './BandedBackground.svelte';

	let {
		backgroundSrc,
		backgroundAlt = '',
		bandedTop,
		bandedBase,
		bandedShadow,
		class: className = '',
		children
	}: {
		backgroundSrc?: string;
		backgroundAlt?: string;
		bandedTop?: string;
		bandedBase?: string;
		bandedShadow?: string;
		class?: string;
		children?: Snippet;
	} = $props();

	let frameClass = $derived(['scene-frame', className].filter(Boolean).join(' '));
</script>

<div class={frameClass}>
	{#if backgroundSrc}
		<img
			class="scene-frame__background scene-frame__background--image"
			src={backgroundSrc}
			alt={backgroundAlt}
			decoding="async"
		/>
	{:else}
		<BandedBackground class="scene-frame__background" top={bandedTop} base={bandedBase} shadow={bandedShadow} />
	{/if}
	<div class="scene-frame__overlay">
		{#if children}
			{@render children()}
		{/if}
	</div>
</div>

<style>
	.scene-frame {
		position: relative;
		width: 100%;
		min-height: 100dvh;
		overflow: hidden;
		background: var(--vm-tobacco-black);
	}

	.scene-frame__background {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
	}

	.scene-frame__background--image {
		object-fit: cover;
		object-position: center;
		image-rendering: pixelated;
		user-select: none;
		pointer-events: none;
	}

	.scene-frame__overlay {
		position: relative;
		z-index: 1;
		min-height: 100dvh;
	}
</style>
