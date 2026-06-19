<script lang="ts">
	import type { BattleCombatant } from './battleApi';

	import ElementBadge from '$lib/ui/ElementBadge.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';

	const HP_SEGMENTS = 15;

	const STAGE_ORDER = [
		'attack',
		'defense',
		'sp_attack',
		'sp_defense',
		'speed',
		'accuracy',
		'evasion'
	] as const;

	const STAT_SHORT: Record<string, string> = {
		attack: 'ATK',
		defense: 'DEF',
		sp_attack: 'SPA',
		sp_defense: 'SPD',
		speed: 'SPE',
		accuracy: 'ACC',
		evasion: 'EVA'
	};

	let {
		combatant,
		currentHp,
		side,
		contextHeld = false,
		xpFillRatio,
		xpAnimating = false
	}: {
		combatant: BattleCombatant;
		currentHp: number;
		side: 'player' | 'opponent';
		contextHeld?: boolean;
		xpFillRatio?: number;
		xpAnimating?: boolean;
	} = $props();

	let ratio = $derived(
		combatant.max_hp > 0 ? Math.max(0, Math.min(1, currentHp / combatant.max_hp)) : 0
	);
	let filledSegments = $derived(Math.round(ratio * HP_SEGMENTS));
	let tone = $derived(ratio <= 0.2 ? 'critical' : ratio <= 0.5 ? 'caution' : 'healthy');
	let xpRatio = $derived(
		side === 'player' ? Math.max(0, Math.min(1, xpFillRatio ?? combatant.xp_bar_ratio)) : 0
	);

	function formatStageValue(stat: (typeof STAGE_ORDER)[number]): string {
		const value = combatant.stat_stages[stat] ?? 0;
		if (value === 0) return '—';
		return value > 0 ? `+${value}` : `${value}`;
	}
</script>

<GamePanel
	tone="status"
	class={['battle-hud', `battle-hud--${side}`, contextHeld && 'battle-hud--deck-read']
		.filter(Boolean)
		.join(' ')}
>
	<div class="battle-hud__header">
		<div class="battle-hud__identity">
			<span class="battle-hud__name">{combatant.name}</span>
			<span class="battle-hud__level">Lv {combatant.level}</span>
		</div>
		<div class="battle-hud__types-slot">
			<div class="battle-hud__types">
				{#each combatant.types as type (type)}
					<ElementBadge {type} />
				{/each}
			</div>
		</div>
	</div>

	<div
		class={['battle-hud__hp-block', contextHeld && 'battle-hud__hp-block--stages']
			.filter(Boolean)
			.join(' ')}
	>
		{#if contextHeld}
			<div class="battle-hud__context" aria-live="polite">
				<ul class="battle-hud__stages">
					{#each STAGE_ORDER as stat (stat)}
						{@const value = combatant.stat_stages[stat] ?? 0}
						<li class="battle-hud__stage">
							<span class="battle-hud__stage-stat">{STAT_SHORT[stat] ?? stat}</span>
							<span
								class={[
									'battle-hud__stage-delta',
									value === 0 && 'battle-hud__stage-delta--neutral',
									value > 0 && 'battle-hud__stage-delta--positive',
									value < 0 && 'battle-hud__stage-delta--negative'
								]
									.filter(Boolean)
									.join(' ')}
							>
								{formatStageValue(stat)}
							</span>
						</li>
					{/each}
				</ul>
			</div>
		{:else}
			<div class="battle-hud__hp-meter">
				<div class="battle-hud__hp-row">
					<span class="battle-hud__label">HP</span>
					<span class="battle-hud__segments" aria-hidden="true">
						{#each Array.from({ length: HP_SEGMENTS }, (_, index) => index) as segment (segment)}
							<span
								class={[
									'battle-hud__segment',
									segment < filledSegments && 'battle-hud__segment--filled',
									segment < filledSegments && `battle-hud__segment--${tone}`
								]
									.filter(Boolean)
									.join(' ')}
							></span>
						{/each}
					</span>
				</div>
				<p class="battle-hud__hp-values">{currentHp}/{combatant.max_hp}</p>
			</div>
		{/if}
	</div>

	{#if side === 'player'}
		<div class="battle-hud__xp-footer">
			<span class="battle-hud__label">XP</span>
			<span class="battle-hud__xp-track" aria-hidden="true">
				<span
					class={['battle-hud__xp-fill', xpAnimating && 'battle-hud__xp-fill--animating']
						.filter(Boolean)
						.join(' ')}
					style:width="max(2px, {xpRatio * 100}%)"
				></span>
			</span>
		</div>
	{/if}
</GamePanel>

<style>
	:global(.battle-hud.game-panel) {
		--battle-hud-pip-height: clamp(0.6rem, 1.4vw, 0.85rem);
		--battle-hud-stat-up: #6e8fa8;
		--battle-hud-hp-slot-height: calc(
			var(--battle-hud-pip-height) + 0.2rem + (clamp(0.6875rem, 1.9vw, 0.875rem) * 1.35)
		);

		width: 100%;
		min-height: 100%;
	}

	:global(.battle-hud .game-panel__content) {
		display: flex;
		flex-direction: column;
		gap: clamp(0.35rem, 1vw, 0.55rem);
		padding: clamp(0.55rem, 1.4vw, 0.9rem);
		box-sizing: border-box;
		height: 100%;
	}

	.battle-hud--deck-read :global(.game-panel__content) {
		animation: deck-read-reveal calc(var(--anim-ui-reveal-steps) * 16ms) steps(var(--anim-ui-reveal-steps));
	}

	.battle-hud__header {
		display: flex;
		align-items: stretch;
		justify-content: space-between;
		gap: 0.5rem;
		min-height: clamp(1.35rem, 2.8vw, 1.85rem);
	}

	.battle-hud__identity {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		align-content: center;
		gap: 0.15rem 0.75rem;
		min-width: 0;
		flex: 1 1 0;
		min-height: 0;
	}

	.battle-hud__name {
		display: inline-flex;
		align-items: center;
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
		text-box-trim: trim-both;
		text-box-edge: cap alphabetic;
	}

	.battle-hud__level {
		display: inline-flex;
		align-items: center;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.55vw, 0.6875rem);
		font-weight: 400;
		line-height: 1;
		letter-spacing: 0.05em;
		color: color-mix(in srgb, var(--vm-tobacco) 68%, transparent);
		flex-shrink: 0;
		text-box-trim: trim-both;
		text-box-edge: cap alphabetic;
	}

	.battle-hud__types-slot {
		flex: 0 0 auto;
		display: flex;
		align-items: center;
		justify-content: flex-end;
		min-width: 0;
		max-width: 55%;
	}

	.battle-hud__types {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		align-content: center;
		justify-content: flex-end;
		height: 100%;
		gap: 0.25rem;
	}

	.battle-hud__context {
		display: flex;
		align-items: center;
		width: 100%;
	}

	.battle-hud__stages {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		row-gap: 0.25rem;
		gap: 0.2rem 0.5rem;
		margin: 0;
		padding: 0;
		list-style: none;
		width: 100%;
	}

	.battle-hud__stage {
		display: inline-flex;
		align-items: baseline;
		gap: 0.1rem;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.625rem, 1.7vw, 0.8125rem);
		line-height: 1.35;
		letter-spacing: 0.04em;
		white-space: nowrap;
	}

	.battle-hud__stage-delta--positive {
		color: var(--battle-hud-stat-up);
	}

	.battle-hud__stage-delta--negative {
		color: var(--vm-burnt-orange);
	}

	.battle-hud__stage-delta--neutral {
		color: color-mix(in srgb, var(--vm-tobacco) 68%, transparent);
	}

	.battle-hud__hp-block {
		display: flex;
		justify-content: flex-end;
		align-items: flex-end;
		width: 100%;
		box-sizing: border-box;
		padding-top: clamp(0.45rem, 1.2vw, 0.65rem);
		padding-bottom: 0;
		min-height: calc(clamp(0.45rem, 1.2vw, 0.65rem) + var(--battle-hud-hp-slot-height));
	}

	.battle-hud__hp-block--stages {
		justify-content: flex-start;
		align-items: center;
	}

	.battle-hud__hp-meter {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		width: 50%;
		min-width: 0;
		gap: 0.2rem;
	}

	.battle-hud__hp-row {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		width: 100%;
		min-height: var(--battle-hud-pip-height);
		column-gap: clamp(0.3rem, 0.8vw, 0.45rem);
	}

	.battle-hud__hp-row > .battle-hud__label {
		display: flex;
		align-items: center;
		height: var(--battle-hud-pip-height);
		line-height: 1;
		font-size: clamp(0.6875rem, 1.9vw, 0.875rem);
		color: color-mix(in srgb, var(--vm-tobacco) 68%, transparent);
	}

	.battle-hud__hp-meter > .battle-hud__hp-values {
		width: 100%;
		color: color-mix(in srgb, var(--vm-tobacco) 68%, transparent);
		text-align: right;
	}

	.battle-hud__label,
	.battle-hud__hp-values {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.75rem, 2.2vw, 1rem);
		line-height: 1.35;
		letter-spacing: 0.03em;
	}

	.battle-hud__segments {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex: 0 0 auto;
		height: var(--battle-hud-pip-height);
		min-width: 0;
	}

	.battle-hud__segment {
		flex: 0 0 auto;
		width: clamp(0.55rem, 1.15vw, 0.72rem);
		height: var(--battle-hud-pip-height);
		border: 1px solid var(--vm-tobacco);
		background: color-mix(in srgb, var(--vm-tobacco) 30%, transparent);
		box-sizing: border-box;
	}

	.battle-hud__segment--filled.battle-hud__segment--healthy {
		background: var(--vm-status-sage);
	}

	.battle-hud__segment--filled.battle-hud__segment--caution {
		background: var(--vm-status-amber);
	}

	.battle-hud__segment--filled.battle-hud__segment--critical {
		background: var(--vm-status-brick);
	}

	.battle-hud__hp-values {
		margin: 0;
		font-size: clamp(0.6875rem, 1.9vw, 0.875rem);
	}

	.battle-hud__xp-footer {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.35rem 0.45rem;
		align-items: center;
		box-sizing: border-box;
		margin-top: auto;
		border-top: 1px solid color-mix(in srgb, var(--vm-tobacco) 35%, transparent);
		background: color-mix(in srgb, var(--vm-tobacco) 8%, transparent);
		margin-inline: calc(-1 * clamp(0.55rem, 1.4vw, 0.9rem));
		margin-bottom: calc(-1 * clamp(0.55rem, 1.4vw, 0.9rem));
		padding: clamp(0.55rem, 1.4vw, 0.9rem);
	}

	.battle-hud__xp-footer > .battle-hud__label {
		color: color-mix(in srgb, var(--vm-tobacco) 68%, transparent);
	}

	.battle-hud__xp-track {
		display: block;
		height: clamp(0.45rem, 1vw, 0.6rem);
		border: 1px solid var(--vm-tobacco);
		background: color-mix(in srgb, var(--vm-tobacco) 18%, transparent);
		overflow: hidden;
	}

	.battle-hud__xp-fill {
		display: block;
		height: 100%;
		background: var(--vm-plum);
	}

	.battle-hud__xp-fill--animating {
		/* Stepped width updates from the session tween — discrete, not eased. */
		transition: none;
	}

	@keyframes deck-read-reveal {
		from {
			opacity: 0.2;
		}
		to {
			opacity: 1;
		}
	}
</style>
