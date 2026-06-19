<script lang="ts">
	import { prefersReducedMotion } from 'svelte/motion';

	import type { BattleMove, BattleCombatant } from './battleApi';
	import MoveMenu from './MoveMenu.svelte';
	import ElementBadge from '$lib/ui/ElementBadge.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';

	let {
		moves,
		activeMoves = [],
		emoteSrc = null,
		combatant = null,
		mode = 'pick',
		selected = 0,
		contextHeld = false,
		levelRequirements = [],
		onSelect,
		onConfirm,
		onHover,
		onDecline
	}: {
		moves: BattleMove[];
		activeMoves?: BattleMove[];
		/** Happy emote pose shown above the move picker. */
		emoteSrc?: string | null;
		combatant?: BattleCombatant | null;
		mode?: 'pick' | 'replace';
		selected?: number;
		contextHeld?: boolean;
		levelRequirements?: number[];
		onSelect?: (index: number) => void;
		onConfirm?: (move: BattleMove) => void;
		onHover?: (index: number | null) => void;
		onDecline?: () => void;
	} = $props();

	let displayMoves = $derived(mode === 'replace' ? activeMoves : moves);
	let menuVariant = $derived<'learn' | 'replace'>(mode === 'pick' ? 'learn' : 'replace');
</script>

<div class="move-learn-modal" role="presentation">
	<div class="move-learn-modal__scrim" aria-hidden="true"></div>
	<div class="move-learn-modal__positioner">
		<div
			class="move-learn-modal__card"
			class:move-learn-modal__card--instant={prefersReducedMotion.current}
			role="dialog"
			aria-modal="true"
			aria-label={mode === 'replace' ? 'Replace a move' : 'Learn a move'}
		>
			<div class="move-learn-modal__body">
				<div class="move-learn-modal__identity-row">
					{#if combatant}
						<GamePanel tone="status" class="move-learn-modal__badge">
							<div class="move-learn-modal__badge-body">
								<div class="move-learn-modal__identity">
									<span class="move-learn-modal__name">{combatant.name}</span>
									<span class="move-learn-modal__level">Lv {combatant.level}</span>
								</div>
								<div class="move-learn-modal__types">
									{#each combatant.types as type (type)}
										<ElementBadge {type} />
									{/each}
								</div>
							</div>
						</GamePanel>
					{/if}
					{#if emoteSrc}
						<div class="move-learn-modal__emote-slot">
							<img class="move-learn-modal__emote" src={emoteSrc} alt="" decoding="async" />
						</div>
					{/if}
				</div>

				<div class="move-learn-modal__picker">
					<MoveMenu
						moves={displayMoves}
						{selected}
						{contextHeld}
						variant={menuVariant}
						{levelRequirements}
						class="move-learn-modal__move-menu"
						onDecline={mode === 'pick' ? onDecline : undefined}
						{onSelect}
						{onConfirm}
						{onHover}
					/>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.move-learn-modal {
		position: fixed;
		inset: 0;
		z-index: 998;
		isolation: isolate;
		pointer-events: none;
	}

	.move-learn-modal__scrim {
		position: absolute;
		inset: 0;
		background: rgb(42 30 22 / 0.42);
		backdrop-filter: grayscale(1);
		-webkit-backdrop-filter: grayscale(1);
		pointer-events: auto;
	}

	.move-learn-modal__positioner {
		position: relative;
		z-index: 1;
		display: flex;
		align-items: flex-end;
		justify-content: center;
		width: 100%;
		height: 100%;
		padding: var(--vm-hud-bottom-inset);
		padding-bottom: calc(
			var(--vm-hud-dialog-slot-height) + var(--vm-hud-bottom-inset) + var(--vm-space-sm)
		);
		box-sizing: border-box;
		pointer-events: none;
	}

	.move-learn-modal__card {
		position: relative;
		display: flex;
		flex-direction: column;
		width: 50%;
		min-width: min(100%, 18rem);
		max-width: 100%;
		pointer-events: auto;
		transform-origin: center bottom;
		animation: move-learn-pop var(--anim-attack-duration, 0.6s)
			steps(var(--anim-ui-reveal-steps, 8));
	}

	.move-learn-modal__card--instant {
		animation: none;
	}

	.move-learn-modal__body {
		display: grid;
		grid-template-columns: minmax(0, 1fr) var(--vm-battle-hud-column-width, 30%);
		row-gap: var(--vm-space-md);
		column-gap: 0;
		flex: 0 0 auto;
		width: 100%;
		min-width: 0;
	}

	.move-learn-modal__identity-row {
		grid-column: 1;
		display: flex;
		align-items: flex-end;
		justify-content: flex-start;
		gap: var(--vm-space-sm);
		flex: 0 0 auto;
		width: 100%;
		min-width: 0;
	}

	:global(.move-learn-modal__badge.game-panel) {
		flex: 0 0 auto;
		align-self: flex-end;
		min-width: 0;
		max-width: min(42%, 14rem);
	}

	:global(.move-learn-modal__badge .game-panel__content) {
		padding: clamp(0.55rem, 1.4vw, 0.9rem);
	}

	.move-learn-modal__badge-body {
		display: flex;
		flex-direction: column;
		gap: clamp(0.35rem, 1vw, 0.55rem);
		min-width: 0;
	}

	.move-learn-modal__identity {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.15rem 0.75rem;
		min-width: 0;
	}

	.move-learn-modal__name {
		font-family: var(--vm-font-ui);
		font-size: var(--vm-text-heading);
		font-weight: 700;
		line-height: 1;
		letter-spacing: 0.04em;
		color: var(--vm-tobacco-black);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 100%;
	}

	.move-learn-modal__level {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.55vw, 0.6875rem);
		font-weight: 400;
		line-height: 1;
		letter-spacing: 0.05em;
		color: color-mix(in srgb, var(--vm-tobacco) 68%, transparent);
		flex-shrink: 0;
	}

	.move-learn-modal__types {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}

	.move-learn-modal__emote-slot {
		flex: 1 1 0;
		min-width: 0;
		height: clamp(20rem, 76vh, 28rem);
		display: flex;
		align-items: flex-end;
		justify-content: center;
	}

	.move-learn-modal__emote {
		display: block;
		width: 100%;
		height: 100%;
		object-fit: contain;
		object-position: bottom center;
		image-rendering: pixelated;
	}

	@keyframes move-learn-pop {
		0% {
			opacity: 0;
			transform: translateY(8px) scale(0.97);
		}
		100% {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.move-learn-modal__picker {
		grid-column: 1 / -1;
		flex: 0 0 auto;
		height: clamp(10rem, 36vh, 14.5rem);
		min-height: 0;
	}

	.move-learn-modal__picker :global(.move-learn-modal__move-menu.move-menu) {
		height: 100%;
		min-height: 0;
	}

	@media (max-width: 480px) {
		.move-learn-modal__body {
			grid-template-columns: minmax(0, 1fr) var(--vm-battle-hud-column-width, 34%);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.move-learn-modal__card {
			animation: none;
		}
	}
</style>
