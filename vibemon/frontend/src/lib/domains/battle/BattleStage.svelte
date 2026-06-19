<script lang="ts">
	import type { BattleCombatant } from './battleApi';
	import BattleMon from './BattleMon.svelte';

	let {
		player,
		opponent,
		playerHp,
		opponentHp,
		entering = false,
		playerAttacking = false,
		opponentAttacking = false,
		playerHurt = false,
		opponentHurt = false,
		playerStatusGlow = false,
		opponentStatusGlow = false,
		playerFainting = false,
		opponentFainting = false,
		playerFainted = false,
		opponentFainted = false,
		projectileTint = 'var(--vm-burnt-orange)',
		projectileVisible = false,
		projectileActor = 'player',
		impactStrength = 0.7,
		impactCrit = false,
		impactPhysical = false,
		impactTint = 'var(--vm-mustard)',
		statusAuraColor = 'var(--vm-mustard)'
	}: {
		player: BattleCombatant;
		opponent: BattleCombatant;
		playerHp: number;
		opponentHp: number;
		entering?: boolean;
		playerAttacking?: boolean;
		opponentAttacking?: boolean;
		playerHurt?: boolean;
		opponentHurt?: boolean;
		playerStatusGlow?: boolean;
		opponentStatusGlow?: boolean;
		playerFainting?: boolean;
		opponentFainting?: boolean;
		playerFainted?: boolean;
		opponentFainted?: boolean;
		projectileTint?: string;
		projectileVisible?: boolean;
		projectileActor?: 'player' | 'opponent';
		impactStrength?: number;
		impactCrit?: boolean;
		impactPhysical?: boolean;
		impactTint?: string;
		statusAuraColor?: string;
	} = $props();

	let burstSide = $derived<'player' | 'opponent' | null>(
		playerHurt ? 'player' : opponentHurt ? 'opponent' : null
	);
	let shaking = $derived((playerHurt || opponentHurt) && impactStrength > 0);
	/** Debris shards thrown outward on contact hits — eight-way scatter. */
	const BURST_SHARDS = [0, 1, 2, 3, 4, 5, 6, 7];
</script>

<div class="battle-stage">
	<div class="battle-stage__field" class:battle-stage__field--shaking={shaking}>
		{#if !opponentFainted}
			<div
				class={[
					'battle-stage__opponent',
					entering && 'battle-stage__slot--entering',
					opponentAttacking && 'battle-stage__slot--lunging',
					opponentFainting && 'battle-stage__slot--fainting'
				]
					.filter(Boolean)
					.join(' ')}
			>
				<BattleMon
					spriteSrc={opponent.sprite_url}
					facing="right"
					attacking={opponentAttacking}
					hurt={opponentHurt}
					statusGlow={opponentStatusGlow}
					{impactStrength}
					recoilX={1}
					recoilY={-1}
					lungeX={-1}
					lungeY={1}
					auraColor={statusAuraColor}
				/>
			</div>
		{/if}

		{#if !playerFainted}
			<div
				class={[
					'battle-stage__player',
					entering && 'battle-stage__slot--entering',
					playerAttacking && 'battle-stage__slot--lunging',
					playerFainting && 'battle-stage__slot--fainting'
				]
					.filter(Boolean)
					.join(' ')}
			>
				<BattleMon
					spriteSrc={player.sprite_url}
					facing="right"
					attacking={playerAttacking}
					hurt={playerHurt}
					statusGlow={playerStatusGlow}
					{impactStrength}
					recoilX={-1}
					recoilY={1}
					lungeX={1}
					lungeY={-1}
					auraColor={statusAuraColor}
				/>
			</div>
		{/if}

		{#if projectileVisible}
			<span
				class="battle-stage__projectile"
				class:battle-stage__projectile--opponent={projectileActor === 'opponent'}
				style:--proj-tint={projectileTint}
				aria-hidden="true"
			>
				<span class="battle-stage__proj-flash"></span>
				{#each [3, 2, 1] as lag (lag)}
					<span class="battle-stage__proj-mote" style:--lag={lag}></span>
				{/each}
				<span class="battle-stage__proj-mote battle-stage__proj-mote--head"></span>
			</span>
		{/if}

		{#if burstSide && impactStrength > 0}
			<span
				class="battle-stage__burst"
				class:battle-stage__burst--player={burstSide === 'player'}
				class:battle-stage__burst--opponent={burstSide === 'opponent'}
				class:battle-stage__burst--crit={impactCrit}
				class:battle-stage__burst--physical={impactPhysical}
				style:--burst-tint={impactTint}
				style:--impact-strength={impactStrength}
				aria-hidden="true"
			>
				<span class="battle-stage__burst-spikes"></span>
				{#if impactPhysical}
					<span class="battle-stage__burst-spikes battle-stage__burst-spikes--diagonal"></span>
					<span class="battle-stage__burst-debris">
						{#each BURST_SHARDS as shard (shard)}
							<span class="battle-stage__shard" style:--shard={shard}></span>
						{/each}
					</span>
				{/if}
			</span>
		{/if}
	</div>
</div>

<style>
	.battle-stage {
		position: absolute;
		inset: 0;
		z-index: 1;
		pointer-events: none;
		/*
			Ring centers on battle.png (0–1 art space) mapped through object-fit:cover
			into the stage field. Player ring measured in-browser against visible dirt oval.
			Re-measure if the backdrop asset or cover crop changes.
		*/
		--battle-ring-player-x: 28.5%;
		--battle-ring-player-y: 90.5%;
		--battle-ring-opponent-x: 80.5%;
		--battle-ring-opponent-y: 64.5%;
		--battle-mon-scale-player: 3.0375;
		--battle-mon-scale-opponent: calc(var(--battle-mon-scale-player) * 0.9);
		/*
			Body-center aim points (mid-torso), above each ring by roughly half the
			sprite's on-screen height. Projectiles fly here and contact bursts land
			here so effects hit the mon, not the dirt. Tune against the live scene.
		*/
		--battle-body-player-x: var(--battle-ring-player-x);
		--battle-body-player-y: 72%;
		--battle-body-opponent-x: var(--battle-ring-opponent-x);
		--battle-body-opponent-y: 50%;
	}

	.battle-stage__field {
		position: relative;
		width: 100%;
		height: 100%;
		pointer-events: none;
	}

	/* Camera shake on the sprite/effects layer only — chrome stays still. */
	.battle-stage__field--shaking {
		animation: field-shake var(--anim-impact-shake-duration, 260ms)
			steps(var(--anim-impact-shake-steps, 8)) 1;
	}

	@keyframes field-shake {
		0%,
		100% {
			transform: translate(0, 0);
		}
		20% {
			transform: translate(
				calc(3px * var(--impact-strength, 0.7)),
				calc(-2px * var(--impact-strength, 0.7))
			);
		}
		40% {
			transform: translate(
				calc(-3px * var(--impact-strength, 0.7)),
				calc(1px * var(--impact-strength, 0.7))
			);
		}
		60% {
			transform: translate(
				calc(2px * var(--impact-strength, 0.7)),
				calc(2px * var(--impact-strength, 0.7))
			);
		}
		80% {
			transform: translate(calc(-1px * var(--impact-strength, 0.7)), 0);
		}
	}

	.battle-stage__opponent,
	.battle-stage__player {
		position: absolute;
		display: flex;
		align-items: flex-end;
		justify-content: center;
		transform: translate(-50%, -100%);
		z-index: 2;
		pointer-events: auto;
		width: calc(64px * var(--battle-mon-scale));
		height: calc(64px * var(--battle-mon-scale));
	}

	.battle-stage__opponent {
		left: var(--battle-ring-opponent-x);
		top: var(--battle-ring-opponent-y);
		--battle-mon-scale: var(--battle-mon-scale-opponent);
		/* Lands right, so it wipes in from the opposite (left) edge. */
		--enter-from: -1;
		/* Dash 62% of the way toward the player's ring. */
		--dash-from-x: var(--battle-ring-opponent-x);
		--dash-from-y: var(--battle-ring-opponent-y);
		--dash-to-x: calc(
			var(--battle-ring-opponent-x) +
				(var(--battle-ring-player-x) - var(--battle-ring-opponent-x)) * 0.62
		);
		--dash-to-y: calc(
			var(--battle-ring-opponent-y) +
				(var(--battle-ring-player-y) - var(--battle-ring-opponent-y)) * 0.62
		);
	}

	.battle-stage__player {
		left: var(--battle-ring-player-x);
		top: var(--battle-ring-player-y);
		--battle-mon-scale: var(--battle-mon-scale-player);
		/* Lands left, so it wipes in from the opposite (right) edge. */
		--enter-from: 1;
		/* Dash 62% of the way toward the opponent's ring. */
		--dash-from-x: var(--battle-ring-player-x);
		--dash-from-y: var(--battle-ring-player-y);
		--dash-to-x: calc(
			var(--battle-ring-player-x) +
				(var(--battle-ring-opponent-x) - var(--battle-ring-player-x)) * 0.62
		);
		--dash-to-y: calc(
			var(--battle-ring-player-y) +
				(var(--battle-ring-opponent-y) - var(--battle-ring-player-y)) * 0.62
		);
	}

	/*
		Travel beat of the contact lunge — the whole slot slides along the true
		vector toward the defender (left/top so aim follows the rings exactly),
		while BattleMon adds the squash/stretch on top. Contact peak at ~32%
		matches REPLAY_ATTACK_MS so the hit feedback fires as the dash lands.
	*/
	/*
		Battle entrance (classic intro): each mon wipes in across the field from
		the horizontal edge opposite its landing ring, settling onto the dirt.
		`translate` composes with the slot's base translate(-50%,-100%); stepped
		per DESIGN.md §6 so it reads as limited animation, not a smooth glide.
	*/
	.battle-stage__slot--entering {
		animation: slot-enter var(--anim-transition-duration, 0.7s)
			steps(var(--anim-transition-steps, 16)) 1;
	}

	@keyframes slot-enter {
		0% {
			translate: calc(var(--enter-from, 1) * 90vw) 0;
		}
		100% {
			translate: 0 0;
		}
	}

	.battle-stage__slot--lunging {
		animation: slot-lunge var(--anim-attack-duration) steps(var(--anim-action-steps, 12)) 1;
	}

	@keyframes slot-lunge {
		0% {
			left: var(--dash-from-x);
			top: var(--dash-from-y);
		}
		14% {
			/* Anticipation: recoil away from the foe. */
			left: calc(var(--dash-from-x) - (var(--dash-to-x) - var(--dash-from-x)) * 0.12);
			top: calc(var(--dash-from-y) - (var(--dash-to-y) - var(--dash-from-y)) * 0.12);
		}
		32% {
			left: var(--dash-to-x);
			top: var(--dash-to-y);
		}
		46% {
			/* Impact hold: rebound just short of the contact point. */
			left: calc(var(--dash-from-x) + (var(--dash-to-x) - var(--dash-from-x)) * 0.86);
			top: calc(var(--dash-from-y) + (var(--dash-to-y) - var(--dash-from-y)) * 0.86);
		}
		100% {
			left: var(--dash-from-x);
			top: var(--dash-from-y);
		}
	}

	.battle-stage__slot--fainting {
		animation: battle-mon-faint var(--anim-faint-duration, 720ms) steps(8) forwards;
	}

	/* Downward topple + fade — base translate(-50%,-100%) is preserved in each frame. */
	@keyframes battle-mon-faint {
		0% {
			opacity: 1;
			filter: brightness(1);
			transform: translate(-50%, -100%) rotate(0deg);
		}
		35% {
			opacity: 1;
			filter: brightness(1.4);
			transform: translate(-50%, -96%) rotate(-3deg);
		}
		100% {
			opacity: 0;
			filter: brightness(0.6);
			transform: translate(-50%, -64%) rotate(10deg);
		}
	}

	/*
		Comet layer fills the field so the motes' left/top percentages resolve
		against the field — letting them fly to the defender's body-center exactly.
		Default = player firing at the opponent's body.
	*/
	.battle-stage__projectile {
		position: absolute;
		inset: 0;
		pointer-events: none;
		z-index: 3;
		--proj-from-x: var(--battle-body-player-x);
		--proj-from-y: var(--battle-body-player-y);
		--proj-to-x: var(--battle-body-opponent-x);
		--proj-to-y: var(--battle-body-opponent-y);
	}

	/* Opponent firing back at the player's body — endpoints swapped. */
	.battle-stage__projectile--opponent {
		--proj-from-x: var(--battle-body-opponent-x);
		--proj-from-y: var(--battle-body-opponent-y);
		--proj-to-x: var(--battle-body-player-x);
		--proj-to-y: var(--battle-body-player-y);
	}

	/* Muzzle flash at launch so the eye catches where the shot comes from. */
	.battle-stage__proj-flash {
		position: absolute;
		left: var(--proj-from-x);
		top: var(--proj-from-y);
		width: clamp(2.25rem, 6vw, 4rem);
		aspect-ratio: 1;
		transform: translate(-50%, -50%);
		border-radius: 50%;
		background: radial-gradient(
			circle,
			var(--vm-parchment) 0%,
			var(--proj-tint, var(--vm-burnt-orange)) 38%,
			transparent 72%
		);
		opacity: 0;
		image-rendering: pixelated;
		animation: projectile-flash 200ms steps(4) 1;
	}

	@keyframes projectile-flash {
		0% {
			opacity: 0;
			transform: translate(-50%, -50%) scale(0.4);
		}
		40% {
			opacity: 0.95;
			transform: translate(-50%, -50%) scale(1.1);
		}
		100% {
			opacity: 0;
			transform: translate(-50%, -50%) scale(1.4);
		}
	}

	.battle-stage__proj-mote {
		position: absolute;
		left: var(--proj-from-x);
		top: var(--proj-from-y);
		/* Trail motes shrink with lag so the head reads as the comet's tip. */
		width: calc(clamp(1rem, 2.6vw, 1.65rem) * (1 - var(--lag, 0) * 0.22));
		aspect-ratio: 1;
		border-radius: 50%;
		/* Hot parchment core melting into the move's type tint, then a soft halo. */
		background: radial-gradient(
			circle,
			var(--vm-parchment) 0%,
			var(--proj-tint, var(--vm-burnt-orange)) 55%,
			transparent 80%
		);
		box-shadow:
			0 0 8px 2px var(--proj-tint, var(--vm-burnt-orange)),
			0 0 16px 4px color-mix(in srgb, var(--proj-tint, var(--vm-burnt-orange)) 55%, transparent);
		opacity: 0;
		pointer-events: none;
		image-rendering: pixelated;
		animation: projectile-travel var(--anim-projectile-duration) steps(10) forwards;
		animation-delay: calc(var(--lag, 0) * 32ms);
	}

	.battle-stage__proj-mote--head {
		width: clamp(1.5rem, 3.6vw, 2.4rem);
		box-shadow:
			0 0 12px 3px var(--proj-tint, var(--vm-burnt-orange)),
			0 0 26px 8px color-mix(in srgb, var(--proj-tint, var(--vm-burnt-orange)) 60%, transparent);
	}

	/* left/top interpolate from launch to the defender's body-center; the squash
	   stretch lives in transform so both compose cleanly. */
	@keyframes projectile-travel {
		0% {
			left: var(--proj-from-x);
			top: var(--proj-from-y);
			opacity: 0;
			transform: translate(-50%, -50%) scale(0.5);
		}
		10% {
			opacity: 1;
			transform: translate(-50%, -50%) scale(1.2, 0.8);
		}
		82% {
			opacity: 1;
			transform: translate(-50%, -50%) scale(1, 1);
		}
		100% {
			left: var(--proj-to-x);
			top: var(--proj-to-y);
			opacity: 0;
			transform: translate(-50%, -50%) scale(1.5, 0.55);
		}
	}

	/* Contact burst at the struck ring (DESIGN.md §6 limited-animation snap). */
	.battle-stage__burst {
		position: absolute;
		width: calc(16px + 14px * var(--impact-strength, 0.7));
		aspect-ratio: 1;
		transform: translate(-50%, -50%);
		pointer-events: none;
		image-rendering: pixelated;
		z-index: 3;
	}

	.battle-stage__burst--player {
		left: var(--battle-body-player-x);
		top: var(--battle-body-player-y);
	}

	.battle-stage__burst--opponent {
		left: var(--battle-body-opponent-x);
		top: var(--battle-body-opponent-y);
	}

	.battle-stage__burst::before {
		content: '';
		position: absolute;
		inset: 20%;
		background: var(--burst-tint, var(--vm-mustard));
		opacity: 0;
		animation: burst-core var(--anim-burst-duration, 360ms) steps(6) 1;
	}

	.battle-stage__burst::after {
		content: '';
		position: absolute;
		inset: 0;
		border: 2px solid var(--burst-tint, var(--vm-mustard));
		border-radius: 50%;
		opacity: 0;
		animation: burst-ring var(--anim-burst-duration, 360ms) steps(6) 1;
	}

	/* Four radial spikes (a stepped spark star) sell the moment of contact. */
	.battle-stage__burst-spikes {
		position: absolute;
		inset: 0;
	}

	.battle-stage__burst-spikes::before,
	.battle-stage__burst-spikes::after {
		content: '';
		position: absolute;
		left: 50%;
		top: 50%;
		background: var(--burst-tint, var(--vm-mustard));
		opacity: 0;
		image-rendering: pixelated;
		animation: burst-spike var(--anim-burst-duration, 360ms) steps(5) 1;
	}

	/* Vertical spike. */
	.battle-stage__burst-spikes::before {
		width: 22%;
		height: 150%;
		transform: translate(-50%, -50%) scaleY(0.2);
	}

	/* Horizontal spike. */
	.battle-stage__burst-spikes::after {
		width: 150%;
		height: 22%;
		transform: translate(-50%, -50%) scaleX(0.2);
	}

	@keyframes burst-spike {
		0% {
			opacity: 0;
		}
		25% {
			opacity: 1;
			transform: translate(-50%, -50%) scale(1.15);
		}
		100% {
			opacity: 0;
			transform: translate(-50%, -50%) scale(1.4);
		}
	}

	/* Critical hits punch a quick double pop of the core. */
	.battle-stage__burst--crit::before {
		animation-iteration-count: 2;
		animation-duration: calc(var(--anim-burst-duration, 360ms) * 0.6);
	}

	@keyframes burst-core {
		0% {
			opacity: 0;
			transform: rotate(45deg) scale(0.4);
		}
		30% {
			opacity: 1;
			transform: rotate(45deg) scale(1.1);
		}
		100% {
			opacity: 0;
			transform: rotate(45deg) scale(1.4);
		}
	}

	@keyframes burst-ring {
		0% {
			opacity: 0.9;
			transform: scale(0.5);
		}
		100% {
			opacity: 0;
			transform: scale(1.7);
		}
	}

	/*
		Physical (contact) hits land bigger than ranged/status: the whole burst
		scales up, a second spike star rotates 45° into an eight-point flash, and
		chunky debris shards scatter outward. Special/status keep the subtle pop.
	*/
	.battle-stage__burst--physical {
		width: calc(26px + 30px * var(--impact-strength, 0.7));
	}

	/* Shorter, offset second star so the eight points read 4 long + 4 short. */
	.battle-stage__burst-spikes--diagonal {
		transform: rotate(45deg) scale(0.72);
	}

	.battle-stage__burst-debris {
		position: absolute;
		inset: 0;
	}

	.battle-stage__shard {
		--shard-angle: calc(var(--shard, 0) * 45deg + 22deg);
		--shard-dist: calc(26px + 30px * var(--impact-strength, 0.7));
		position: absolute;
		left: 50%;
		top: 50%;
		width: calc(3px + 4px * var(--impact-strength, 0.7));
		height: calc(3px + 4px * var(--impact-strength, 0.7));
		background: var(--burst-tint, var(--vm-mustard));
		opacity: 0;
		image-rendering: pixelated;
		transform: translate(-50%, -50%) rotate(var(--shard-angle)) translateY(0);
		animation: burst-shard var(--anim-burst-duration, 360ms) steps(5) 1;
		animation-delay: 30ms;
	}

	/* Alternate shards travel shorter for an uneven, debris-like scatter. */
	.battle-stage__shard:nth-child(even) {
		--shard-dist: calc(16px + 18px * var(--impact-strength, 0.7));
		animation-delay: 10ms;
	}

	@keyframes burst-shard {
		0% {
			opacity: 0;
			transform: translate(-50%, -50%) rotate(var(--shard-angle)) translateY(0) scale(1.25);
		}
		25% {
			opacity: 1;
		}
		100% {
			opacity: 0;
			transform: translate(-50%, -50%) rotate(var(--shard-angle))
				translateY(calc(-1 * var(--shard-dist))) scale(0.5);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.battle-stage__slot--entering {
			animation: none;
		}

		.battle-stage__field--shaking {
			animation: none;
		}

		.battle-stage__burst::before {
			animation-iteration-count: 1;
		}

		.battle-stage__burst-debris {
			display: none;
		}
	}
</style>
