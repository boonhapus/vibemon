<script lang="ts">
	import type { Snippet } from 'svelte';
	import { fade } from 'svelte/transition';

	import SettingsNavButton from '$lib/domains/trainer/SettingsNavButton.svelte';
	import { settingsStore } from '$lib/domains/trainer/settingsStore.svelte';
	import BandedBackground from './BandedBackground.svelte';
	import FilmGrain from './FilmGrain.svelte';

	let {
		backgroundSrc,
		backgroundAlt = '',
		backgroundFadeMs = 0,
		bandedTop,
		bandedBase,
		bandedShadow,
		class: className = '',
		showSettingsKnob = true,
		children
	}: {
		backgroundSrc?: string;
		backgroundAlt?: string;
		/** When > 0, crossfade between backgrounds on src change instead of hard-swapping. */
		backgroundFadeMs?: number;
		bandedTop?: string;
		bandedBase?: string;
		bandedShadow?: string;
		class?: string;
		/** Cabinet settings knob in the bottom-right bezel corner. */
		showSettingsKnob?: boolean;
		children?: Snippet;
	} = $props();

	let frameClass = $derived(['scene-frame', className].filter(Boolean).join(' '));
</script>

<div class={frameClass}>
	{#key backgroundSrc}
		<div class="scene-frame__background-layer" transition:fade={{ duration: backgroundFadeMs }}>
			{#if backgroundSrc}
				<img
					class="scene-frame__background scene-frame__background--image"
					src={backgroundSrc}
					alt={backgroundAlt}
					decoding="async"
				/>
			{:else}
				<BandedBackground
					class="scene-frame__background"
					top={bandedTop}
					base={bandedBase}
					shadow={bandedShadow}
				/>
			{/if}
		</div>
	{/key}
	<div class="scene-frame__overlay">
		{#if children}
			{@render children()}
		{/if}
	</div>
	<div class="scene-frame__bezel" aria-hidden="true"></div>
	<div class="scene-frame__bezel-lip" aria-hidden="true"></div>
	{#if showSettingsKnob}
		<div class="scene-frame__corner-plate">
			<span class="scene-frame__corner-screw" aria-hidden="true"></span>
			<div class="scene-frame__corner-mount">
				<SettingsNavButton bind:open={settingsStore.open} />
			</div>
		</div>
	{/if}
	<FilmGrain />
</div>

<style>
	.scene-frame {
		position: relative;
		width: 100%;
		min-height: 100dvh;
		overflow: hidden;
		background: var(--vm-tobacco-black);
		/* Bezel width lives in tokens.css (--vm-bezel-w) so chrome rendered
		   outside the frame (e.g. toasts) can respect it too. */
	}

	/* Wooden TV-cabinet frame: tobacco wood with faint horizontal grain,
	   painted only on the border ring via mask-composite. */
	.scene-frame__bezel {
		position: absolute;
		inset: 0;
		z-index: 2;
		pointer-events: none;
		box-sizing: border-box;
		padding: var(--vm-bezel-w);
		background: var(--vm-cabinet-wood-grain);
		-webkit-mask:
			linear-gradient(#fff 0 0) content-box,
			linear-gradient(#fff 0 0);
		-webkit-mask-composite: xor;
		mask:
			linear-gradient(#fff 0 0) content-box,
			linear-gradient(#fff 0 0);
		mask-composite: exclude;
	}

	/* Inner lip — the shadowed seam where the screen meets the cabinet. */
	.scene-frame__bezel-lip {
		position: absolute;
		inset: var(--vm-bezel-w);
		z-index: 2;
		pointer-events: none;
		box-shadow:
			inset 0 0 0 2px rgb(42 30 22 / 0.55),
			inset 0 2px 10px rgb(42 30 22 / 0.3);
	}

	/* Quarter-round corner plate — cabinet hardware mount (ui-cohesion-plan §4). */
	.scene-frame__corner-plate {
		position: absolute;
		right: calc(var(--vm-bezel-w) * 0.3);
		bottom: calc(var(--vm-bezel-w) * 0.3);
		z-index: 3;
		width: var(--vm-settings-corner-size);
		height: var(--vm-settings-corner-size);
		border-top-left-radius: 100%;
		pointer-events: auto;
		background: var(--vm-cabinet-wood-grain-corner);
		box-shadow:
			inset 0 1px 0 rgb(240 231 206 / 0.13),
			inset -2px -2px 7px rgb(20 12 8 / 0.36),
			0 3px 0 rgb(42 30 22 / 0.44),
			0 5px 11px rgb(20 12 8 / 0.3);
	}

	.scene-frame__corner-screw {
		position: absolute;
		top: 0.55rem;
		left: 0.55rem;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: radial-gradient(circle at 35% 30%, #c9a23f, var(--vm-brass) 55%, #6b4423);
		box-shadow:
			inset 0 -1px 1px rgb(20 12 8 / 0.45),
			0 0 0 1px rgb(42 30 22 / 0.35);
	}

	.scene-frame__corner-mount {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0.35rem 0.2rem 0.2rem 0.35rem;
	}

	.scene-frame__corner-mount :global(.settings-nav) {
		width: clamp(2.85rem, 6.4vh, 3.6rem);
		height: clamp(2.85rem, 6.4vh, 3.6rem);
	}

	/* Each background generation gets its own layer so two can overlap mid-crossfade. */
	.scene-frame__background-layer {
		position: absolute;
		inset: 0;
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
