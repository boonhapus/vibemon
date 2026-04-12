<script lang="ts">
	let { spriteUrl, animationSpeed = 1.5 }: {
		spriteUrl: string | null;
		animationSpeed?: number;
	} = $props();

	let floatDuration = $derived(`${animationSpeed.toFixed(2)}s`);
</script>

<div class="vibemon-wrapper" style="--float-duration: {floatDuration};">
	{#if spriteUrl}
		<img src={spriteUrl} alt="vibemon sprite" class="vibemon-sprite" />
	{/if}
</div>

<style>
	.vibemon-wrapper {
		display: inline-block;
		animation: float var(--float-duration, 1.5s) ease-in-out infinite alternate;
	}

	.vibemon-sprite {
		width: 100%;
		height: 100%;
		object-fit: contain;
		image-rendering: pixelated;
	}

	@keyframes float {
		0%   { transform: translateY(0); }
		100% { transform: translateY(-6px); }
	}
</style>
