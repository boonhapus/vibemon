<script lang="ts">
	import GamePanel from '$lib/ui/GamePanel.svelte';

	import { hpPercent, type PartySlot } from './crewSlots';

	let {
		member = null
	}: {
		member?: PartySlot | null;
	} = $props();
</script>

<GamePanel tone="status" class="crew-member-panel">
	{#if member && !member.empty}
		<div class="crew-member-panel__hp">
			<span class="crew-member-panel__level">Lv{member.level}</span>
			<span class="crew-member-panel__hp-label">HP</span>
			<div class="crew-member-panel__hp-track" aria-hidden="true">
				<div class="crew-member-panel__hp-fill" style:width="{hpPercent(member)}%"></div>
			</div>
			<span class="crew-member-panel__hp-values">{member.currentHp} / {member.maxHp}</span>
		</div>
	{:else}
		<p class="crew-member-panel__empty">Open seat in the formation.</p>
	{/if}
</GamePanel>

<style>
	:global(.crew-member-panel) {
		width: 100%;
	}

	.crew-member-panel__hp {
		display: grid;
		grid-template-columns: auto auto 1fr auto;
		gap: 0.35rem 0.55rem;
		align-items: center;
		padding: clamp(0.2rem, 0.6vw, 0.35rem);
	}

	.crew-member-panel__level,
	.crew-member-panel__hp-label,
	.crew-member-panel__hp-values {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.75rem);
		line-height: 1.5;
		letter-spacing: 0.03em;
	}

	.crew-member-panel__hp-track {
		height: clamp(0.55rem, 1.5vw, 0.75rem);
		border: 2px solid var(--vm-tobacco);
		background: color-mix(in srgb, var(--vm-tobacco) 12%, var(--vm-parchment));
		padding: 1px;
	}

	.crew-member-panel__hp-fill {
		height: 100%;
		background: var(--vm-status-sage);
	}

	.crew-member-panel__empty {
		margin: 0;
		padding: clamp(0.2rem, 0.6vw, 0.35rem);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.75rem);
		line-height: 1.5;
		letter-spacing: 0.05em;
		color: color-mix(in srgb, var(--vm-tobacco) 62%, var(--vm-brass));
	}
</style>
