<script lang="ts">
	import type { TitleMonSlot } from './titleMonSlots';

	let {
		slot,
		spriteSrc
	}: {
		slot: TitleMonSlot;
		spriteSrc: string;
	} = $props();
	let bottomPct = $derived(slot.bottomPct + (slot.footLiftPct ?? 0));
</script>

<div
	class="title-grass-mon"
	class:title-grass-mon--mirrored={slot.mirrored}
	style:left="{slot.leftPct}%"
	style:bottom="{bottomPct}%"
	style:--mon-scale={slot.scale}
	style:--mon-delay="{slot.delayMs}ms"
	style:--mon-duration="{slot.durationMs}ms"
	style:--mask-url={`url("${spriteSrc}")`}
	aria-hidden="true"
>
	<div class="title-grass-mon__mon">
		<span class="title-grass-mon__mask"></span>
	</div>
</div>

<style>
	.title-grass-mon {
		position: absolute;
		width: clamp(4rem, 12vw, 7.5rem);
		height: clamp(3.4rem, 10vw, 6.5rem);
		transform: translateX(-50%) scale(var(--mon-scale, 1));
		transform-origin: center bottom;
		pointer-events: none;
	}

	.title-grass-mon__mon {
		position: absolute;
		inset: 0 2%;
		transform-origin: center bottom;
		animation: title-mon-rustle var(--mon-duration, 1.8s) steps(5, end) infinite;
		animation-delay: var(--mon-delay, 0ms);
	}

	.title-grass-mon__mask {
		position: absolute;
		inset: 0;
		background: var(--vm-tobacco);
		-webkit-mask-image: var(--mask-url);
		mask-image: var(--mask-url);
		-webkit-mask-repeat: no-repeat;
		mask-repeat: no-repeat;
		-webkit-mask-position: bottom center;
		mask-position: bottom center;
		-webkit-mask-size: contain;
		mask-size: contain;
	}

	.title-grass-mon--mirrored .title-grass-mon__mask {
		transform: scaleX(-1);
	}

	@keyframes title-mon-rustle {
		0%,
		16%,
		100% {
			transform: translate(0, 0) rotate(0deg) scale(1, 1);
		}
		4% {
			transform: translate(-1.5px, 0.5px) rotate(-0.5deg) scale(1.008, 0.992);
		}
		8% {
			transform: translate(1.5px, -0.5px) rotate(0.4deg) scale(0.995, 1.005);
		}
		12% {
			transform: translate(-1px, 0) rotate(-0.3deg) scale(1.003, 0.997);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.title-grass-mon__mon {
			animation: none;
		}
	}
</style>
