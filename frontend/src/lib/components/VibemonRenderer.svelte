<script lang="ts">
	import type { VisualDNA } from '$lib/types';
	import {
		generateHullPoints,
		smoothClosedPath,
		generateLimbs,
		generateEyes,
		eyeToSvg,
		pupilToSvg,
		generateMouth,
		generateTexturePattern,
		hsl
	} from '$lib/utils/blobRenderer';

	let { dna, seed, uid, flipped = false }: {
		dna: VisualDNA;
		seed: number;
		uid: string;
		flipped?: boolean;
	} = $props();

	let hullPoints = $derived(generateHullPoints(dna, seed));
	let bodyPath = $derived(smoothClosedPath(hullPoints));
	let limbs = $derived(generateLimbs(hullPoints, dna, seed));
	let eyes = $derived(generateEyes(hullPoints, dna, seed));
	let mouth = $derived(generateMouth(hullPoints, dna));
	let texturePattern = $derived(generateTexturePattern(dna, uid));

	let cpStr = $derived(hsl(dna.color_primary));
	let csStr = $derived(hsl(dna.color_secondary));
	let caStr = $derived(hsl(dna.color_accent));
	let ceStr = $derived(hsl(dna.color_eye));

	let floatDuration = $derived(`${dna.animation_speed.toFixed(2)}s`);
	let glowDuration = $derived(`${(dna.animation_speed * 1.5).toFixed(2)}s`);
	let glowBlur = $derived(dna.glow_intensity * 6);
</script>

<div
	class="vibemon-wrapper"
	style="
		--float-duration: {floatDuration};
		--glow-duration: {glowDuration};
	"
>
	<svg
		viewBox="0 0 200 220"
		xmlns="http://www.w3.org/2000/svg"
		class="vibemon-svg"
		style="
			--cp: {cpStr};
			--cs: {csStr};
			--ca: {caStr};
			--ce: {ceStr};
			--ow: {dna.outline_weight}px;
			transform: scaleX({flipped ? -1 : 1}) scale({dna.size_scale});
		"
	>
		<defs>
			<filter id="glow-{uid}">
				<feGaussianBlur stdDeviation="{glowBlur}" result="blur" />
				<feMerge>
					<feMergeNode in="blur" />
					<feMergeNode in="SourceGraphic" />
				</feMerge>
			</filter>
			{#if texturePattern}
				{@html texturePattern}
			{/if}
		</defs>

		<!-- Limbs (behind body) -->
		{#each limbs as limb}
			<path
				d={limb.path}
				fill={limb.fill}
				opacity={limb.opacity}
				stroke="var(--cs)"
				stroke-width="1"
			/>
		{/each}

		<!-- Body -->
		<path
			d={bodyPath}
			fill="var(--cp)"
			stroke="var(--cs)"
			stroke-width="var(--ow)"
			filter="url(#glow-{uid})"
		/>

		<!-- Texture overlay -->
		{#if texturePattern}
			<path
				d={bodyPath}
				fill="url(#texture-{uid})"
				stroke="none"
			/>
		{/if}

		<!-- Eyes -->
		{#each eyes as eye, i}
			{@html eyeToSvg(eye, uid, i)}
			{@html pupilToSvg(eye, uid, i)}
		{/each}

		<!-- Mouth -->
		{#if mouth}
			{@html mouth}
		{/if}
	</svg>
</div>

<style>
	.vibemon-wrapper {
		display: inline-block;
		animation: float var(--float-duration, 1.5s) ease-in-out infinite alternate;
	}

	.vibemon-svg {
		width: 100%;
		height: 100%;
		overflow: visible;
	}

	@keyframes float {
		0% {
			transform: translateY(0);
		}
		100% {
			transform: translateY(-6px);
		}
	}
</style>
