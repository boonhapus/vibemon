<script lang="ts">
	let {
		spriteSrc = '/game/sprites/trainer.png',
		mirrored = false,
		class: className = ''
	}: {
		spriteSrc?: string;
		mirrored?: boolean;
		class?: string;
	} = $props();

	let rootClass = $derived(
		['trainer-portrait', mirrored && 'trainer-portrait--mirrored', className].filter(Boolean).join(' ')
	);
</script>

<div class={rootClass} aria-hidden="true">
	<div class="trainer-portrait__platform">
		<div class="trainer-portrait__platform-core"></div>
	</div>
	<img class="trainer-portrait__sprite" src={spriteSrc} alt="" decoding="async" />
</div>

<style>
	.trainer-portrait {
		--sprite-h: clamp(22rem, 50vh, 36rem);
		--sprite-w: calc(var(--sprite-h) * 0.56);
		--platform-w: calc(var(--sprite-h) * 0.82);
		--platform-h: clamp(2rem, 4.5vw, 3rem);
		--scene-top: #c4a882;
		--scene-base: #6b7a2a;
		--platform-strength: 1;

		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: flex-end;
		width: max(var(--sprite-w), var(--platform-w));
		min-height: calc(var(--sprite-h) + var(--platform-h) * 0.55);
		padding-bottom: calc(var(--platform-h) * 0.32);
	}

	.trainer-portrait__platform {
		position: absolute;
		bottom: calc(var(--platform-h) * 0.32);
		left: 50%;
		width: var(--platform-w);
		height: var(--platform-h);
		transform: translateX(-50%) scale(0.94);
		transform-origin: center bottom;
		border-radius: 50%;
		overflow: visible;
		pointer-events: none;
		z-index: 0;
	}

	/* Defined oval under the feet — crisp center, soft outer dissolve */
	.trainer-portrait__platform-core {
		position: absolute;
		inset: -30% -20%;
		border-radius: 50%;
		opacity: calc(0.9 * var(--platform-strength));
		background: radial-gradient(
			ellipse 100% 100% at 50% 50%,
			color-mix(in srgb, var(--scene-top) 92%, white) 0%,
			color-mix(in srgb, var(--scene-top) 96%, var(--scene-base)) 38%,
			color-mix(in srgb, var(--scene-top) 78%, var(--scene-base)) 62%,
			color-mix(in srgb, var(--scene-base) 28%, var(--scene-top)) 100%
		);
		-webkit-mask-image: radial-gradient(
			ellipse 72% 66% at 50% 54%,
			rgb(0 0 0 / 1) 0%,
			rgb(0 0 0 / 0.96) 24%,
			rgb(0 0 0 / 0.82) 40%,
			rgb(0 0 0 / 0.52) 54%,
			rgb(0 0 0 / 0.26) 66%,
			rgb(0 0 0 / 0.1) 78%,
			rgb(0 0 0 / 0.03) 90%,
			transparent 100%
		);
		mask-image: radial-gradient(
			ellipse 72% 66% at 50% 54%,
			rgb(0 0 0 / 1) 0%,
			rgb(0 0 0 / 0.96) 24%,
			rgb(0 0 0 / 0.82) 40%,
			rgb(0 0 0 / 0.52) 54%,
			rgb(0 0 0 / 0.26) 66%,
			rgb(0 0 0 / 0.1) 78%,
			rgb(0 0 0 / 0.03) 90%,
			transparent 100%
		);
	}

	/* Outer feather — light blur only on the dissolve band */
	.trainer-portrait__platform::before {
		content: '';
		position: absolute;
		inset: -44% -28%;
		border-radius: 50%;
		opacity: calc(0.5 * var(--platform-strength));
		filter: blur(2px);
		background: radial-gradient(
			ellipse 100% 100% at 50% 54%,
			color-mix(in srgb, var(--scene-top) 78%, var(--scene-base)) 0%,
			color-mix(in srgb, var(--scene-top) 62%, var(--scene-base)) 100%
		);
		-webkit-mask-image: radial-gradient(
			ellipse 76% 68% at 50% 54%,
			transparent 0%,
			transparent 46%,
			rgb(0 0 0 / 0.18) 58%,
			rgb(0 0 0 / 0.12) 72%,
			rgb(0 0 0 / 0.04) 88%,
			transparent 100%
		);
		mask-image: radial-gradient(
			ellipse 76% 68% at 50% 54%,
			transparent 0%,
			transparent 46%,
			rgb(0 0 0 / 0.18) 58%,
			rgb(0 0 0 / 0.12) 72%,
			rgb(0 0 0 / 0.04) 88%,
			transparent 100%
		);
	}

	/* Pixel-dither on the outer edge only */
	.trainer-portrait__platform::after {
		content: '';
		position: absolute;
		inset: -38% -24%;
		border-radius: 50%;
		opacity: calc(0.2 * var(--platform-strength));
		background-image:
			radial-gradient(circle, rgb(61 43 31 / 0.07) 0.5px, transparent 0.5px),
			radial-gradient(circle, rgb(196 168 130 / 0.05) 0.5px, transparent 0.5px),
			radial-gradient(circle, rgb(107 122 42 / 0.04) 0.5px, transparent 0.5px);
		background-size:
			2px 2px,
			3px 3px,
			4px 4px;
		background-position:
			0 0,
			1px 1px,
			2px 0;
		-webkit-mask-image: radial-gradient(
			ellipse 74% 68% at 50% 54%,
			transparent 50%,
			rgb(0 0 0 / 0.2) 62%,
			rgb(0 0 0 / 0.14) 76%,
			rgb(0 0 0 / 0.04) 90%,
			transparent 100%
		);
		mask-image: radial-gradient(
			ellipse 74% 68% at 50% 54%,
			transparent 50%,
			rgb(0 0 0 / 0.2) 62%,
			rgb(0 0 0 / 0.14) 76%,
			rgb(0 0 0 / 0.04) 90%,
			transparent 100%
		);
	}

	.trainer-portrait__sprite {
		position: relative;
		z-index: 1;
		height: var(--sprite-h);
		width: auto;
		margin-bottom: calc(var(--platform-h) * -0.06);
		transform: translateY(-2%);
		image-rendering: pixelated;
		image-rendering: crisp-edges;
		user-select: none;
		pointer-events: none;
	}

	.trainer-portrait--mirrored .trainer-portrait__sprite {
		transform: translateY(-2%) scaleX(-1);
	}

	@media (max-width: 480px) {
		.trainer-portrait {
			--sprite-h: clamp(16rem, 42vh, 24rem);
			--platform-h: clamp(1.65rem, 3.8vw, 2.35rem);
		}
	}
</style>
