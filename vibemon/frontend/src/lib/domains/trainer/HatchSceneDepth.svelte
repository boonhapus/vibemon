<script lang="ts">
	/** Static parallax depth for the hatch field — tree line + grass tufts (DESIGN.md §4). */
</script>

<div class="hatch-scene-depth" aria-hidden="true">
	<div class="hatch-scene-depth__trees"></div>
	<div class="hatch-scene-depth__grass"></div>
</div>

<style>
	.hatch-scene-depth {
		position: absolute;
		inset: 0;
		z-index: 0;
		pointer-events: none;
		overflow: hidden;
	}

	/* Sage Olive tree line — stacked flat pixel silhouettes, no smooth bands alone. */
	.hatch-scene-depth__trees {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 38%;
		height: clamp(4.5rem, 14vh, 8rem);
		background:
			linear-gradient(to top, transparent 0 18%, rgb(110 117 64 / 0.92) 18% 22%, transparent 22% 34%),
			linear-gradient(to top, transparent 0 8%, rgb(110 117 64 / 0.78) 8% 14%, transparent 14% 28%),
			linear-gradient(to top, transparent 0 0%, rgb(107 122 42 / 0.55) 0% 10%, transparent 10% 100%);
		background-size:
			28% 100%,
			22% 100%,
			100% 100%;
		background-position:
			8% 100%,
			72% 100%,
			0 100%;
		background-repeat: no-repeat;
		image-rendering: pixelated;
		opacity: 0.88;
	}

	.hatch-scene-depth__trees::before,
	.hatch-scene-depth__trees::after {
		content: '';
		position: absolute;
		bottom: 0;
		width: 18%;
		height: 72%;
		background: rgb(110 117 64 / 0.85);
		clip-path: polygon(50% 0%, 0% 100%, 100% 100%);
		image-rendering: pixelated;
	}

	.hatch-scene-depth__trees::before {
		left: 22%;
		transform: scale(1.15, 1);
	}

	.hatch-scene-depth__trees::after {
		right: 16%;
		width: 14%;
		height: 58%;
		opacity: 0.82;
	}

	/* Foreground grass tufts along the field floor. */
	.hatch-scene-depth__grass {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: clamp(2.5rem, 8vh, 4.5rem);
		background:
			repeating-linear-gradient(
				90deg,
				transparent 0 14px,
				rgb(107 122 42 / 0.35) 14px 16px,
				transparent 16px 28px,
				rgb(110 117 64 / 0.42) 28px 30px,
				transparent 30px 44px
			),
			linear-gradient(to top, rgb(107 122 42 / 0.28) 0%, transparent 72%);
		background-size:
			120px 100%,
			100% 100%;
		background-position:
			0 100%,
			0 100%;
		image-rendering: pixelated;
	}
</style>
