<script lang="ts">
	import type { BattleMove } from './battleApi';
	import { effectivenessPhrase } from './effectivenessCopy';
	import { BATTLE_GRID_SLOTS } from './battleGridMenu';
	import { MOVE_CATEGORY_STYLES } from './moveCategoryStyles';
	import { moveReadHint } from './moveReadHint';
	import ElementBadge from '$lib/ui/ElementBadge.svelte';
	import GameButton from '$lib/ui/GameButton.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';

	let {
		moves,
		selected = 0,
		contextHeld = false,
		variant = 'default',
		levelRequirements = [],
		class: className = '',
		onSelect,
		onConfirm,
		onHover,
		onDecline
	}: {
		moves: BattleMove[];
		selected?: number;
		contextHeld?: boolean;
		variant?: 'default' | 'learn' | 'replace';
		levelRequirements?: number[];
		class?: string;
		onSelect?: (index: number) => void;
		onConfirm?: (move: BattleMove) => void;
		onHover?: (index: number | null) => void;
		onDecline?: () => void;
	} = $props();

	let highlighted = $derived(moves[selected] ?? moves[0] ?? null);
	let highlightedLevel = $derived(
		variant === 'learn' ? (levelRequirements[selected] ?? levelRequirements[0]) : undefined
	);
	let statsOnly = $derived(variant === 'learn' || variant === 'replace');
	let readLine = $derived(highlighted && contextHeld ? moveReadHint(highlighted) : null);
	let effectivenessLine = $derived(
		highlighted && contextHeld && highlighted.category !== 'status'
			? effectivenessPhrase(highlighted.effectiveness)
			: null
	);

	let categoryStyle = $derived(
		highlighted ? MOVE_CATEGORY_STYLES[highlighted.category] : MOVE_CATEGORY_STYLES.physical
	);

	function formatAccuracy(accuracy: number | null): string {
		if (accuracy == null) return '—';
		return `${Math.round(accuracy * 100)}%`;
	}

	function activate(index: number) {
		const move = moves[index];
		if (!move) return;
		onSelect?.(index);
		onConfirm?.(move);
	}
</script>

<div class={['move-menu', className].filter(Boolean).join(' ')}>
	<GamePanel tone="command" class="move-menu__moves">
		<div class="move-menu__moves-body">
			<div
				class="move-menu__grid"
				role="menu"
				aria-label="Moves"
				onmouseleave={() => onHover?.(null)}
			>
				{#each Array(BATTLE_GRID_SLOTS) as _, index (index)}
					{@const move = moves[index]}
					{#if move}
						<button
							type="button"
							class={[
								'move-menu__cell',
								selected === index && 'move-menu__cell--selected',
								contextHeld && 'move-menu__cell--deck-read'
							]
								.filter(Boolean)
								.join(' ')}
							aria-current={selected === index ? 'true' : undefined}
							onmouseenter={() => onHover?.(index)}
							onclick={() => activate(index)}
						>
							<span class="move-menu__content">
								{#if selected === index}
									<span class="move-menu__cursor" aria-hidden="true">▶</span>
								{/if}
								<span class="move-menu__label">{move.name}</span>
							</span>
						</button>
					{:else}
						<div class="move-menu__cell move-menu__cell--empty" aria-hidden="true"></div>
					{/if}
				{/each}
			</div>

			{#if onDecline}
				<GameButton variant="primary" class="move-menu__decline" onclick={() => onDecline()}>
					Decline
				</GameButton>
			{/if}
		</div>
	</GamePanel>

	{#if highlighted}
		<GamePanel tone="status" class="move-menu__stats">
			<div class="move-menu__stats-body">
				<div class="move-menu__badge-row">
					<div class="move-menu__type-badge">
						<ElementBadge type={highlighted.type} class="move-menu__element-badge" />
					</div>
					<span
						class="move-menu__category-badge"
						style:--badge-bg={categoryStyle.bg}
						style:--badge-fg={categoryStyle.fg}
					>
						{categoryStyle.label}
					</span>
				</div>
				{#if statsOnly}
					<div class="move-menu__stats-quadrants move-menu__stats-quadrants--learn">
						<p class="move-menu__stat-line">PP {highlighted.pp_current}/{highlighted.pp_max}</p>
						<p class="move-menu__stat-line">PWR {highlighted.power ?? '—'}</p>
						<p class="move-menu__stat-line">ACC {formatAccuracy(highlighted.accuracy)}</p>
						{#if variant === 'learn'}
							<p class="move-menu__stat-line">
								{#if highlightedLevel != null}
									LV {highlightedLevel}
								{:else}
									—
								{/if}
							</p>
						{:else}
							<div class="move-menu__stat-line move-menu__stat-line--empty" aria-hidden="true"></div>
						{/if}
					</div>
				{:else if contextHeld}
					<div class="move-menu__read-block">
						<p class="move-menu__read">{readLine}</p>
						{#if effectivenessLine}
							<p class="move-menu__stat-line move-menu__stat-line--effect">{effectivenessLine}</p>
						{/if}
					</div>
				{:else}
					<div class="move-menu__stats-quadrants">
						<p class="move-menu__stat-line">PP {highlighted.pp_current}/{highlighted.pp_max}</p>
						<p class="move-menu__stat-line">PWR {highlighted.power ?? '—'}</p>
						<p class="move-menu__stat-line">ACC {formatAccuracy(highlighted.accuracy)}</p>
						<div class="move-menu__stat-line move-menu__stat-line--empty" aria-hidden="true"></div>
					</div>
				{/if}
			</div>
		</GamePanel>
	{/if}
</div>

<style>
	.move-menu {
		display: grid;
		grid-template-columns: minmax(0, 1fr) var(--vm-battle-hud-column-width, 30%);
		width: 100%;
		height: 100%;
		min-height: 0;
		align-items: stretch;
	}

	:global(.move-menu__stats.game-panel),
	:global(.move-menu__moves.game-panel) {
		display: flex;
		flex-direction: column;
		width: 100%;
		height: 100%;
		min-height: 0;
		min-width: 0;
		box-shadow: none;
	}

	:global(.move-menu__stats .game-panel__frame),
	:global(.move-menu__moves .game-panel__frame),
	:global(.move-menu__stats .game-panel__inset),
	:global(.move-menu__moves .game-panel__inset),
	:global(.move-menu__stats .game-panel__surface),
	:global(.move-menu__moves .game-panel__surface) {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		width: 100%;
		height: 100%;
		min-height: 0;
		min-width: 0;
		box-sizing: border-box;
	}

	:global(.move-menu__moves .game-panel__content) {
		box-sizing: border-box;
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		padding: clamp(0.35rem, 1vw, 0.55rem);
	}

	.move-menu__moves-body {
		display: flex;
		flex: 1 1 auto;
		flex-direction: column;
		gap: var(--vm-space-xs);
		min-height: 0;
		height: 100%;
	}

	:global(.move-menu__decline.game-button) {
		flex: 0 0 auto;
		width: 100%;
	}

	:global(.move-menu__decline .game-button__face) {
		width: 100%;
	}

	:global(.move-menu__stats .game-panel__content) {
		box-sizing: border-box;
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		--move-menu-stats-inset: clamp(0.35rem, 1vw, 0.55rem);
		padding: var(--move-menu-stats-inset);
	}

	.move-menu__stats-body {
		display: flex;
		flex-direction: column;
		flex: 1 1 auto;
		gap: 0.35rem;
		width: 100%;
		height: 100%;
		min-height: 0;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.625rem, 1.7vw, 0.8125rem);
		line-height: 1.4;
	}

	.move-menu__read-block {
		display: flex;
		flex: 1 1 auto;
		flex-direction: column;
		gap: 0.35rem;
		min-height: 0;
		margin-top: 0.15rem;
		padding: 0.35rem 0.3rem 0.2rem;
	}

	.move-menu__read-block .move-menu__stat-line {
		display: block;
		padding: 0;
		text-align: left;
	}

	.move-menu__read {
		flex: 1 1 auto;
		margin: 0;
		min-height: 0;
		overflow: hidden;
		font-size: clamp(0.5625rem, 1.5vw, 0.6875rem);
		line-height: 1.5;
		text-align: left;
	}

	.move-menu__stats-quadrants {
		display: grid;
		flex: 1 1 auto;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		grid-template-rows: repeat(2, minmax(0, 1fr));
		width: 100%;
		min-height: 0;
	}

	.move-menu__badge-row {
		flex: 0 0 auto;
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.35rem;
		align-items: center;
		width: 100%;
		min-width: 0;
	}

	.move-menu__type-badge {
		min-width: 0;
	}

	.move-menu__type-badge :global(.move-menu__element-badge.element-badge) {
		display: flex;
		width: 100%;
		justify-content: center;
		box-sizing: border-box;
	}

	.move-menu__category-badge {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		min-width: 0;
		box-sizing: border-box;
		padding: 0.2rem 0.25rem;
		border: 2px solid color-mix(in srgb, var(--badge-fg) 28%, var(--vm-tobacco));
		border-radius: var(--vm-radius-sm);
		background-color: var(--badge-bg);
		background-image:
			radial-gradient(circle at 22% 28%, rgb(61 43 31 / 0.1) 1px, transparent 1px),
			radial-gradient(circle at 72% 68%, rgb(61 43 31 / 0.08) 1px, transparent 1px);
		background-size:
			5px 5px,
			7px 7px;
		color: var(--badge-fg);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1.35;
		letter-spacing: 0.06em;
		text-align: center;
		white-space: nowrap;
	}

	.move-menu__stat-line {
		display: grid;
		place-items: center;
		margin: 0;
		padding: 0.15rem;
		text-align: center;
		line-height: 1.35;
	}

	.move-menu__stat-line--effect {
		color: var(--vm-burnt-orange);
		font-size: 0.9em;
	}

	.move-menu__stat-line--empty {
		pointer-events: none;
	}

	.move-menu__grid {
		display: grid;
		flex: 1 1 auto;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		grid-template-rows: repeat(2, minmax(0, 1fr));
		width: 100%;
		min-height: 0;
	}

	.move-menu__cell {
		display: grid;
		place-items: center;
		width: 100%;
		height: 100%;
		min-width: 0;
		min-height: 0;
		margin: 0;
		padding: 0;
		border: 0;
		background: transparent;
		color: var(--vm-tobacco-black);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.625rem, 1.8vw, 0.8125rem);
		line-height: 1;
		letter-spacing: 0.04em;
		cursor: pointer;
	}

	.move-menu__content {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.25rem;
		line-height: 1;
	}

	.move-menu__cell--empty {
		cursor: default;
		pointer-events: none;
	}

	.move-menu__cell:nth-child(odd) {
		border-right: 1px dotted color-mix(in srgb, var(--vm-tobacco) 45%, transparent);
	}

	.move-menu__cell:nth-child(-n + 2) {
		border-bottom: 1px dotted color-mix(in srgb, var(--vm-tobacco) 45%, transparent);
	}

	.move-menu__cell--selected {
		color: var(--vm-burnt-orange);
	}

	.move-menu__cell--deck-read {
		animation: deck-read-reveal calc(var(--anim-ui-reveal-steps) * 16ms)
			steps(var(--anim-ui-reveal-steps));
	}

	.move-menu__cursor {
		display: block;
		flex: 0 0 auto;
		color: var(--vm-mustard);
		font-size: 0.75em;
		line-height: 1;
		text-box-trim: trim-both;
		text-box-edge: cap alphabetic;
	}

	.move-menu__label {
		display: block;
		line-height: 1;
		text-align: center;
		text-box-trim: trim-both;
		text-box-edge: cap alphabetic;
	}

	.move-menu__stats-quadrants--learn {
		flex: 1 1 auto;
	}

	@keyframes deck-read-reveal {
		from {
			opacity: 0.25;
		}
		to {
			opacity: 1;
		}
	}

	@media (max-width: 480px) {
		.move-menu {
			grid-template-columns: minmax(0, 1fr) var(--vm-battle-hud-column-width, 34%);
		}
	}
</style>
