<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { generation } from '$lib/stores/generation.svelte';
	import VibemonRenderer from '$lib/components/VibemonRenderer.svelte';

	let ready = $state(false);

	onMount(() => {
		if (!generation.payload) {
			void goto('/');
			return;
		}
		ready = true;
	});

	let player = $derived(generation.payload?.player);
	let enemy = $derived(generation.payload?.enemy);

	function seedFromUid(uid: string): number {
		let hash = 0;
		for (let i = 0; i < uid.length; i++) {
			hash = (Math.imul(31, hash) + uid.charCodeAt(i)) | 0;
		}
		return hash >>> 0;
	}
</script>

{#if ready && player && enemy}
	<div class="battle-scene">
		<div class="battle-field">
			<!-- Enemy (top-right) -->
			<div class="mon-slot enemy-slot">
				<div class="mon-info">
					<span class="mon-name">{enemy.name}</span>
					<span class="mon-element">{enemy.stats.element}{enemy.stats.element_secondary ? ` · ${enemy.stats.element_secondary}` : ''}</span>
				</div>
				<div class="mon-render">
					<VibemonRenderer
						dna={enemy.visual_dna}
						seed={seedFromUid(enemy.uid)}
						uid={enemy.uid}
						flipped={true}
					/>
				</div>
			</div>

			<!-- Player (bottom-left) -->
			<div class="mon-slot player-slot">
				<div class="mon-render">
					<VibemonRenderer
						dna={player.visual_dna}
						seed={seedFromUid(player.uid)}
						uid={player.uid}
					/>
				</div>
				<div class="mon-info">
					<span class="mon-name">{player.name}</span>
					<span class="mon-element">{player.stats.element}{player.stats.element_secondary ? ` · ${player.stats.element_secondary}` : ''}</span>
				</div>
			</div>
		</div>

		<div class="stat-bar-section">
			<div class="stat-row">
				<span class="stat-label">{player.name}</span>
				<span class="stat-hp">HP {player.stats.hp}</span>
			</div>
			<div class="stat-row">
				<span class="stat-label">{enemy.name}</span>
				<span class="stat-hp">HP {enemy.stats.hp}</span>
			</div>
		</div>

		<div class="moves-grid">
			{#each player.moves as move}
				<button class="move-btn" type="button" disabled>
					<span class="move-name">{move.is_signature ? '★ ' : ''}{move.name}</span>
					<span class="move-meta">
						{move.category}{move.power > 0 ? ` · ${move.power}` : ''}
					</span>
				</button>
			{/each}
		</div>

		<div class="battle-footer">
			<p class="muted">{player.flavour_text}</p>
			<p><a href="/">← Back</a></p>
		</div>
	</div>
{:else}
	<div class="layout">
		<p class="muted">Redirecting…</p>
	</div>
{/if}

<style>
	.battle-scene {
		max-width: 600px;
		margin: 0 auto;
		padding: 1rem 1rem 2rem;
	}

	.battle-field {
		position: relative;
		min-height: 380px;
		margin-bottom: 1rem;
	}

	.mon-slot {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
	}

	.enemy-slot {
		position: absolute;
		top: 0;
		right: 0;
		width: 45%;
	}

	.player-slot {
		position: absolute;
		bottom: 0;
		left: 0;
		width: 50%;
	}

	.mon-render {
		width: 160px;
		height: 180px;
	}

	.mon-info {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.15rem;
	}

	.mon-name {
		font-weight: 700;
		font-size: 1.05rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.mon-element {
		font-size: 0.8rem;
		color: #9aa3b2;
	}

	.stat-bar-section {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		margin-bottom: 1.25rem;
		padding: 0.75rem 1rem;
		border: 1px solid #222836;
		border-radius: 10px;
		background: #13161d;
	}

	.stat-row {
		display: flex;
		justify-content: space-between;
		font-size: 0.9rem;
	}

	.stat-label {
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.stat-hp {
		color: #6ddf8b;
		font-variant-numeric: tabular-nums;
	}

	.moves-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.5rem;
		margin-bottom: 1.25rem;
	}

	.move-btn {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.15rem;
		padding: 0.65rem 0.5rem;
		text-align: center;
	}

	.move-name {
		font-weight: 600;
		font-size: 0.9rem;
	}

	.move-meta {
		font-size: 0.75rem;
		color: #6b7385;
		text-transform: capitalize;
	}

	.battle-footer {
		text-align: center;
	}
</style>
