<script lang="ts">
	import type { Snippet } from 'svelte';
	import { onMount } from 'svelte';
	import { fade } from 'svelte/transition';

	import { cabinetMetaStore } from '$lib/domains/game/cabinetMetaStore.svelte';
	import GuideNavButton from '$lib/domains/trainer/GuideNavButton.svelte';
	import SettingsNavButton from '$lib/domains/trainer/SettingsNavButton.svelte';
	import { settingsStore } from '$lib/domains/trainer/settingsStore.svelte';
	import BandedBackground from './BandedBackground.svelte';
	import CabinetGuidePanel from './CabinetGuidePanel.svelte';
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
		showGuideKnob = true,
		meta,
		children
	}: {
		backgroundSrc?: string;
		backgroundAlt?: string;
		backgroundFadeMs?: number;
		bandedTop?: string;
		bandedBase?: string;
		bandedShadow?: string;
		class?: string;
		showSettingsKnob?: boolean;
		showGuideKnob?: boolean;
		meta?: Snippet;
		children?: Snippet;
	} = $props();

	let frameClass = $derived(
		[
			'scene-frame',
			cabinetMetaStore.expanded && 'scene-frame--guide-expanded',
			className
		]
			.filter(Boolean)
			.join(' ')
	);

	/** Crossfade only after first paint — pageload shows the backdrop instantly. */
	let backgroundCrossfadeReady = $state(false);

	onMount(() => {
		const id = requestAnimationFrame(() => {
			backgroundCrossfadeReady = true;
		});
		return () => cancelAnimationFrame(id);
	});
</script>

{#snippet backgroundLayer()}
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
{/snippet}

<div class={frameClass}>
	{#key backgroundSrc}
		{#if backgroundCrossfadeReady}
			<div class="scene-frame__background-layer" transition:fade={{ duration: backgroundFadeMs }}>
				{@render backgroundLayer()}
			</div>
		{:else}
			<div class="scene-frame__background-layer">
				{@render backgroundLayer()}
			</div>
		{/if}
	{/key}
	<div class="scene-frame__overlay">
		{#if children}
			{@render children()}
		{/if}
	</div>
	<div class="scene-frame__bezel" aria-hidden="true"></div>
	<div class="scene-frame__bezel-lip" aria-hidden="true"></div>
	{#if showGuideKnob}
		<CabinetGuidePanel {meta} />
		<div class="scene-frame__guide-plate">
			<span class="scene-frame__guide-screw" aria-hidden="true"></span>
			<div class="scene-frame__guide-mount">
				<GuideNavButton />
			</div>
		</div>
	{/if}
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
		--vm-bezel-top-current: var(--vm-bezel-w);
	}

	.scene-frame--guide-expanded {
		--vm-bezel-top-current: var(--vm-bezel-guide-h);
	}

	.scene-frame__bezel {
		position: absolute;
		inset: 0;
		z-index: 2;
		pointer-events: none;
		box-sizing: border-box;
		padding: var(--vm-bezel-top-current) var(--vm-bezel-w) var(--vm-bezel-w) var(--vm-bezel-w);
		background: var(--vm-cabinet-wood-grain);
		background-attachment: var(--vm-cabinet-wood-grain-fixed);
		transition:
			padding-top var(--vm-guide-reveal-duration) steps(var(--anim-ui-reveal-steps), jump-none)
			var(--vm-guide-bezel-delay, var(--vm-guide-stagger));
		-webkit-mask:
			linear-gradient(#fff 0 0) content-box,
			linear-gradient(#fff 0 0);
		-webkit-mask-composite: xor;
		mask:
			linear-gradient(#fff 0 0) content-box,
			linear-gradient(#fff 0 0);
		mask-composite: exclude;
	}

	.scene-frame--guide-expanded .scene-frame__bezel,
	.scene-frame--guide-expanded .scene-frame__bezel-lip {
		--vm-guide-bezel-delay: 0ms;
	}

	.scene-frame__bezel-lip {
		position: absolute;
		inset: var(--vm-bezel-top-current) var(--vm-bezel-w) var(--vm-bezel-w) var(--vm-bezel-w);
		z-index: 2;
		pointer-events: none;
		transition:
			inset var(--vm-guide-reveal-duration) steps(var(--anim-ui-reveal-steps), jump-none)
			var(--vm-guide-bezel-delay, var(--vm-guide-stagger));
		box-shadow:
			inset 0 0 0 2px rgb(42 30 22 / 0.55),
			inset 0 2px 10px rgb(42 30 22 / 0.3);
	}

	@media (prefers-reduced-motion: reduce) {
		.scene-frame__bezel,
		.scene-frame__bezel-lip,
		:global(.cabinet-guide-panel) {
			transition: none;
		}
	}

	.scene-frame__guide-plate {
		position: absolute;
		left: calc(var(--vm-bezel-w) * 0.3);
		bottom: calc(var(--vm-bezel-w) * 0.3);
		z-index: 3;
		width: var(--vm-guide-corner-size);
		height: var(--vm-guide-corner-size);
		border-top-right-radius: 100%;
		pointer-events: auto;
		background: transparent;
	}

	/* Fixed grain underlay — knob face is transparent; wood tiles with the bezel rail. */
	.scene-frame__guide-plate::before,
	.scene-frame__corner-plate::before {
		content: '';
		position: absolute;
		inset: 0;
		z-index: -1;
		background: var(--vm-cabinet-wood-grain);
		background-attachment: var(--vm-cabinet-wood-grain-fixed);
		pointer-events: none;
	}

	.scene-frame__guide-plate::before {
		border-top-right-radius: 100%;
	}

	.scene-frame__guide-screw {
		position: absolute;
		top: 0.55rem;
		right: 0.55rem;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: radial-gradient(circle at 35% 30%, #c9a23f, var(--vm-brass) 55%, #6b4423);
		box-shadow:
			inset 0 -1px 1px rgb(20 12 8 / 0.45),
			0 0 0 1px rgb(42 30 22 / 0.35);
	}

	.scene-frame__guide-mount {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: flex-end;
		justify-content: center;
		padding: 0.2rem 0.35rem 0.15rem 0.15rem;
	}

	.scene-frame__guide-mount :global(.guide-nav) {
		width: auto;
		height: auto;
	}

	.scene-frame__corner-plate {
		position: absolute;
		right: calc(var(--vm-bezel-w) * 0.3);
		bottom: calc(var(--vm-bezel-w) * 0.3);
		z-index: 3;
		width: var(--vm-settings-corner-size);
		height: var(--vm-settings-corner-size);
		border-top-left-radius: 100%;
		pointer-events: auto;
		background: transparent;
	}

	.scene-frame__corner-plate::before {
		border-top-left-radius: 100%;
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
		align-items: flex-end;
		justify-content: center;
		padding: 0.2rem 0.15rem 0.15rem 0.35rem;
	}

	.scene-frame__corner-mount :global(.settings-nav) {
		width: auto;
		height: auto;
	}

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
