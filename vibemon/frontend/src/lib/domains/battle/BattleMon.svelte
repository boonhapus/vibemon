<script lang="ts">
	let {
		spriteSrc,
		facing = 'left',
		attacking = false,
		hurt = false,
		statusGlow = false,
		scale,
		impactStrength = 0.7,
		recoilX = 0,
		recoilY = 0,
		lungeX = 1,
		lungeY = 0,
		auraColor = 'var(--vm-mustard)',
		class: className = ''
	}: {
		spriteSrc: string | null;
		facing?: 'left' | 'right';
		attacking?: boolean;
		hurt?: boolean;
		statusGlow?: boolean;
		scale?: number;
		/** 0 (immune) .. 1.3 (crit super-effective); scales flash + knockback. */
		impactStrength?: number;
		/** Recoil direction signs for the knockback (away from the hit). */
		recoilX?: number;
		recoilY?: number;
		/** Lunge direction signs (toward the defender). */
		lungeX?: number;
		lungeY?: number;
		auraColor?: string;
		class?: string;
	} = $props();

	const PLACEHOLDER = '/game/sprites/hatchling-silhouette@128.png';
	let src = $derived(spriteSrc ?? PLACEHOLDER);
	let modelClass = $derived(
		[
			'battle-mon__model',
			attacking && 'is-attacking',
			hurt && 'is-hurt',
			statusGlow && 'is-status',
			className
		]
			.filter(Boolean)
			.join(' ')
	);
</script>

<div
	class="battle-mon"
	class:battle-mon--flip={facing === 'left'}
	class:battle-mon--status={statusGlow}
	style:--battle-mon-scale={scale}
	style:--impact-strength={impactStrength}
	style:--recoil-x={recoilX}
	style:--recoil-y={recoilY}
	style:--lunge-x={lungeX}
	style:--lunge-y={lungeY}
	style:--status-aura-color={auraColor}
>
	<img class={modelClass} {src} alt="" decoding="async" />

	{#if statusGlow}
		<span class="battle-mon__aura" aria-hidden="true"></span>
		<span class="battle-mon__motes" aria-hidden="true">
			{#each [0, 1, 2, 3, 4] as mote (mote)}
				<span class="battle-mon__mote" style:--mote={mote}></span>
			{/each}
		</span>
	{/if}
</div>

<style>
	.battle-mon {
		position: relative;
		display: flex;
		align-items: flex-end;
		justify-content: center;
		width: 100%;
		height: 100%;
		transform-origin: bottom center;
	}

	.battle-mon--flip {
		transform: scaleX(-1);
	}

	.battle-mon__model {
		display: block;
		width: calc(64px * var(--battle-mon-scale, 1));
		height: calc(64px * var(--battle-mon-scale, 1));
		max-width: calc(64px * var(--battle-mon-scale, 1));
		max-height: calc(64px * var(--battle-mon-scale, 1));
		object-fit: contain;
		object-position: bottom center;
		image-rendering: pixelated;
		transform-origin: bottom center;
	}

	:global(.battle-mon .is-attacking) {
		animation: physical-lunge var(--anim-attack-duration) steps(var(--anim-action-steps)) forwards;
	}

	:global(.battle-mon .is-hurt) {
		animation:
			hurt-flash var(--anim-hurt-duration) steps(4) 3,
			hurt-knockback var(--anim-knockback-duration, 320ms) steps(6) 1;
	}

	:global(.battle-mon .is-status) {
		animation: status-glow var(--anim-status-aura-duration, 650ms) steps(8) 1;
	}

	/*
		Contact lunge squash/stretch (DESIGN.md §6.4). The slot handles the travel
		toward the defender (see BattleStage); here we add the coil/stretch and a
		small secondary thrust along --lunge-x/y so the sprite feels like it drives
		into the hit rather than gliding.
	*/
	@keyframes physical-lunge {
		0% {
			transform: translate(0, 0) rotate(0deg) scale(1, 1);
		}
		14% {
			/* Anticipation: coil back (opposite the dash) and compress. */
			transform: translate(calc(var(--lunge-x, 1) * -10px), calc(var(--lunge-y, 0) * -7px))
				rotate(calc(var(--lunge-x, 1) * -4deg)) scale(0.84, 1.08);
		}
		32% {
			/* Action: thrust into the hit, stretched along travel. */
			transform: translate(calc(var(--lunge-x, 1) * 26px), calc(var(--lunge-y, 0) * 17px))
				rotate(calc(var(--lunge-x, 1) * 4deg)) scale(1.24, 0.9);
		}
		46% {
			/* Impact hold: brief rebound just short of the thrust peak. */
			transform: translate(calc(var(--lunge-x, 1) * 18px), calc(var(--lunge-y, 0) * 12px))
				rotate(calc(var(--lunge-x, 1) * 2deg)) scale(1.08, 0.96);
		}
		100% {
			transform: translate(0, 0) rotate(0deg) scale(1, 1);
		}
	}

	/* Warm analog snap (DESIGN.md §6.5) — brightness lift scales with the hit. */
	@keyframes hurt-flash {
		0%,
		100% {
			opacity: 1;
			filter: brightness(1);
		}
		50% {
			opacity: calc(0.55 - 0.2 * var(--impact-strength, 0.7));
			filter: brightness(calc(1 + 0.55 * var(--impact-strength, 0.7))) sepia(0.15);
		}
	}

	/* Stepped recoil away from the hit; distance scales with impact strength. */
	@keyframes hurt-knockback {
		0% {
			translate: 0 0;
		}
		25% {
			translate: calc(var(--recoil-x, 0) * 7px * var(--impact-strength, 0.7))
				calc(var(--recoil-y, 0) * 5px * var(--impact-strength, 0.7));
		}
		60% {
			translate: calc(var(--recoil-x, 0) * 2px * var(--impact-strength, 0.7))
				calc(var(--recoil-y, 0) * 1px * var(--impact-strength, 0.7));
		}
		100% {
			translate: 0 0;
		}
	}

	@keyframes status-glow {
		0%,
		100% {
			filter: brightness(1);
		}
		50% {
			filter: brightness(1.3) drop-shadow(0 0 5px var(--status-aura-color, var(--vm-mustard)));
		}
	}

	/* Attacker aura ring (DESIGN.md §9.3 status profile) — stepped expand + fade. */
	.battle-mon__aura {
		position: absolute;
		left: 50%;
		bottom: 6%;
		width: calc(34px * var(--battle-mon-scale, 1));
		height: calc(34px * var(--battle-mon-scale, 1));
		translate: -50% 0;
		border-radius: 50%;
		border: 2px solid var(--status-aura-color, var(--vm-mustard));
		opacity: 0;
		pointer-events: none;
		image-rendering: pixelated;
		animation: status-aura var(--anim-status-aura-duration, 650ms) steps(8) 1;
	}

	@keyframes status-aura {
		0% {
			opacity: 0;
			transform: scale(0.4);
		}
		30% {
			opacity: 0.9;
			transform: scale(0.85);
		}
		100% {
			opacity: 0;
			transform: scale(1.35);
		}
	}

	.battle-mon__motes {
		position: absolute;
		inset: 0;
		pointer-events: none;
	}

	.battle-mon__mote {
		position: absolute;
		left: calc(50% + (var(--mote) - 2) * 14%);
		bottom: 12%;
		width: 4px;
		height: 4px;
		background: var(--status-aura-color, var(--vm-mustard));
		image-rendering: pixelated;
		opacity: 0;
		animation: status-mote var(--anim-status-aura-duration, 650ms) steps(6) 1;
		animation-delay: calc(var(--mote) * 70ms);
	}

	@keyframes status-mote {
		0% {
			opacity: 0;
			transform: translateY(0) scale(1);
		}
		40% {
			opacity: 1;
		}
		100% {
			opacity: 0;
			transform: translateY(-26px) scale(0.6);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		:global(.battle-mon .is-hurt) {
			animation: hurt-flash var(--anim-hurt-duration) steps(4) 2;
		}

		.battle-mon__aura,
		.battle-mon__motes {
			display: none;
		}
	}
</style>
