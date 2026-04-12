<script lang="ts">
	let { spriteUrl }: { spriteUrl: string | null } = $props();
</script>

<div class="vibemon-wrapper">
	{#if spriteUrl}
		<img src={spriteUrl} alt="" class="vibemon-sprite" />
	{:else}
		<div class="vibemon-placeholder" aria-hidden="true"></div>
	{/if}
</div>

<style>
	.vibemon-wrapper {
		display: inline-block;
		width: 100%;
		height: 100%;
	}

	.vibemon-sprite {
		width: 100%;
		height: 100%;
		object-fit: contain;
		image-rendering: pixelated;
	}

	.vibemon-placeholder {
		width: 100%;
		height: 100%;
		min-height: 120px;
		border: 1px dashed var(--vb-border);
		border-radius: var(--r-md);
		background: rgba(6, 4, 15, 0.35);
	}
</style>
