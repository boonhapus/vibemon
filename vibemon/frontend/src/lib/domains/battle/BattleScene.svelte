<script lang="ts">
	import { goto } from '$app/navigation';
	import { untrack } from 'svelte';

	import { sceneBackgroundSrc } from '$lib/domains/game/sceneBackgrounds';
	import { sceneSolarPhase } from '$lib/domains/game/gameSolarContext.svelte';
	import DialogBox from '$lib/ui/DialogBox.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import { playGameAudio } from '$lib/ui/gameAudioStore.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';
	import { elementTypeColor } from '$lib/ui/elementTypes';

	import BattleHudPlate from './BattleHudPlate.svelte';
	import BattleStage from './BattleStage.svelte';
	import { impactStrength } from './battleImpact';
	import CommandMenu from './CommandMenu.svelte';
	import {
		CREW_COMING_SOON_TOAST,
		DECK_COMING_SOON_TOAST,
		type CommandId
	} from './commandMenu';
	import { navigateBattleGrid } from './battleGridMenu';
	import MoveMenu from './MoveMenu.svelte';
	import MoveLearnMenu from './MoveLearnMenu.svelte';
	import { moveCategoryTextColor } from './moveCategoryStyles';
	import {
		advanceIntro,
		advanceReplay,
		advanceWonBeat,
		ATTACK_VISUAL_MS,
		bootstrapBattleSession,
		chooseMove,
		chooseRun,
		closeMoveSelect,
		confirmMoveLearnReplacement,
		createBattleSession,
		currentMoveLearnOffer,
		currentReplayStep,
		declineCurrentMoveOffer,
		moveLearnPickerMoves,
		openMoveSelect,
		selectMoveLearnOption
	} from './battleSession.svelte';
	import { moveReadHint } from './moveReadHint';
	import { emoteHappyFromBattleSprite } from './battleSpriteUrls';

	let { battleId }: { battleId: string } = $props();

	let session = $state(createBattleSession(''));
	let contextHeld = $state(false);
	let commandIndex = $state(0);
	let moveIndex = $state(0);
	let moveLearnIndex = $state(0);
	let moveLearnHoverIndex = $state<number | null>(null);
	let lastShownError = $state<string | null>(null);
	let dialogBox = $state<{ skipTyping: () => boolean } | undefined>();
	/** Holds the lunge active for its full visual duration even after the replay
	    advances to the hit, so the dash and the contact feedback overlap. */
	let lungingActor = $state<'player' | 'opponent' | null>(null);
	let lungeTimer: ReturnType<typeof setTimeout> | null = null;

	let backgroundSrc = $derived(sceneBackgroundSrc('battle', sceneSolarPhase()));
	let battleState = $derived(session.state);
	let defeatSceneClass = $derived(session.phase === 'defeat' ? 'scene-frame--battle-defeat' : '');
	let replayStep = $derived(currentReplayStep(session));
	let playerAttacking = $derived(lungingActor === 'player');
	let opponentAttacking = $derived(lungingActor === 'opponent');

	$effect(() => {
		const step = replayStep;
		if (step?.kind !== 'animation' || step.profile !== 'physical') return;
		const actor = step.actor;
		untrack(() => {
			lungingActor = actor;
			if (lungeTimer) clearTimeout(lungeTimer);
			lungeTimer = setTimeout(() => {
				lungingActor = null;
				lungeTimer = null;
			}, ATTACK_VISUAL_MS);
		});
	});
	let playerStatusGlow = $derived(
		replayStep?.kind === 'animation' &&
			replayStep.profile === 'status' &&
			replayStep.actor === 'player'
	);
	let opponentStatusGlow = $derived(
		replayStep?.kind === 'animation' &&
			replayStep.profile === 'status' &&
			replayStep.actor === 'opponent'
	);
	let playerHurt = $derived(replayStep?.kind === 'hurt' && replayStep.side === 'player');
	let opponentHurt = $derived(replayStep?.kind === 'hurt' && replayStep.side === 'opponent');
	let playerFainting = $derived(replayStep?.kind === 'faint' && replayStep.side === 'player');
	let opponentFainting = $derived(replayStep?.kind === 'faint' && replayStep.side === 'opponent');
	let playerFainted = $derived(session.faintedSides.player);
	let opponentFainted = $derived(session.faintedSides.opponent);
	let projectileVisible = $derived(
		replayStep?.kind === 'animation' && replayStep.profile === 'special'
	);
	let projectileActor = $derived<'player' | 'opponent'>(
		replayStep?.kind === 'animation' && replayStep.profile === 'special'
			? replayStep.actor
			: 'player'
	);
	let projectileTint = $derived(
		replayStep?.kind === 'animation'
			? elementTypeColor(replayStep.moveType)
			: 'var(--vm-burnt-orange)'
	);
	let hurtStep = $derived(replayStep && replayStep.kind === 'hurt' ? replayStep : null);
	let impactStrengthValue = $derived(
		hurtStep ? impactStrength(hurtStep.effectiveness, hurtStep.crit) : 0.7
	);
	let impactCrit = $derived(hurtStep?.crit ?? false);
	let impactPhysical = $derived(hurtStep?.category === 'physical');
	let impactTint = $derived(
		hurtStep?.sourceType ? elementTypeColor(hurtStep.sourceType) : 'var(--vm-status-amber)'
	);
	let statusAuraColor = $derived(
		replayStep?.kind === 'animation' && replayStep.profile === 'status'
			? elementTypeColor(replayStep.moveType)
			: 'var(--vm-mustard)'
	);
	let dialogEmphasis = $derived.by(() => {
		const highlight = session.dialogMoveHighlight;
		if (!highlight) return undefined;
		return {
			text: highlight.name,
			color: moveCategoryTextColor(highlight.category),
			typeBadge: highlight.type
		};
	});
	let moveLearnActive = $derived(
		session.wonBeat === 'moveLearn' || session.wonBeat === 'moveLearnReplace'
	);
	let moveLearnMode = $derived<'pick' | 'replace'>(
		session.wonBeat === 'moveLearnReplace' ? 'replace' : 'pick'
	);
	let moveLearnMoves = $derived(moveLearnPickerMoves(session));
	let moveLearnOffer = $derived(currentMoveLearnOffer(session));
	let moveLearnLevelReqs = $derived(
		moveLearnOffer?.moves.map((entry) => entry.level_requirement) ?? []
	);
	let moveLearnDialogHint = $derived.by(() => {
		if (!moveLearnActive || !battleState) return null;
		const moves = moveLearnMode === 'replace' ? battleState.player.moves : moveLearnMoves;
		const index =
			contextHeld || moveLearnHoverIndex !== null
				? (moveLearnHoverIndex ?? moveLearnIndex)
				: null;
		if (index === null) return null;
		const move = moves[index];
		if (!move) return null;
		return moveReadHint(move);
	});
	let moveLearnShowHint = $derived(moveLearnDialogHint !== null);
	let moveLearnEmoteSrc = $derived(
		battleState ? emoteHappyFromBattleSprite(battleState.player.sprite_url) : null
	);
	let moveLearnCombatant = $derived(
		battleState && moveLearnOffer?.vibemon_id === battleState.player.vibemon_id
			? battleState.player
			: battleState?.player ?? null
	);

	$effect(() => {
		const id = battleId;
		session = createBattleSession(id);
		lastShownError = null;
		untrack(() => {
			if (lungeTimer) clearTimeout(lungeTimer);
			lungeTimer = null;
			lungingActor = null;
			void bootstrapBattleSession(session);
		});
	});

	function handleCommandDown() {
		commandIndex = (commandIndex + 2) % 4;
		playGameAudio('menu-nav');
	}

	function handleDialogContinue() {
		if (session.phase === 'intro') {
			advanceIntro(session);
			return;
		}
		if (session.phase === 'command' && session.dialogCursor) {
			session.dialogText = 'What will you do?';
			session.dialogMoveHighlight = null;
			session.dialogCursor = false;
			return;
		}
		if (session.phase === 'resolving') {
			advanceReplay(session);
			return;
		}
		if (session.phase === 'won' || session.phase === 'defeat' || session.phase === 'fled') {
			if (session.phase === 'won' && !advanceWonBeat(session)) {
				return;
			}
			void goto('/deck/crew');
		}
	}

	function handleCommand(command: CommandId) {
		playGameAudio('confirm');
		if (command === 'moves') {
			openMoveSelect(session);
			return;
		}
		if (command === 'run') {
			void chooseRun(session);
		}
	}

	function handleMove(move: { name: string }) {
		playGameAudio('confirm');
		void chooseMove(session, move.name);
	}

	function handleMoveLearnConfirm(move: { id: string; name: string }) {
		playGameAudio('confirm');
		if (session.wonBeat === 'moveLearnReplace') {
			const activeMove = battleState?.player.moves[moveLearnIndex];
			if (activeMove) {
				void confirmMoveLearnReplacement(session, activeMove);
			}
			return;
		}
		const option = moveLearnOffer?.moves.find((entry) => entry.id === move.id);
		if (option) {
			void selectMoveLearnOption(session, option);
		}
	}

	function handleWindowKeydown(event: KeyboardEvent) {
		if (event.key === 'c' || event.key === 'C') {
			if (!event.repeat) contextHeld = true;
			return;
		}

		if (session.busy) return;

		if (session.phase === 'command') {
			if (session.dialogCursor && (event.key === 'Enter' || event.key === ' ')) {
				event.preventDefault();
				handleDialogContinue();
				return;
			}

			switch (event.key) {
				case 'ArrowUp':
				case 'ArrowDown':
				case 'ArrowLeft':
				case 'ArrowRight':
					event.preventDefault();
					commandIndex = navigateBattleGrid(commandIndex, event.key);
					playGameAudio('menu-nav');
					break;
				case 'Enter':
				case ' ':
					event.preventDefault();
					if (commandIndex === 0) handleCommand('moves');
					else if (commandIndex === 1) showGameToast(DECK_COMING_SOON_TOAST, 'amber');
					else if (commandIndex === 2) showGameToast(CREW_COMING_SOON_TOAST, 'amber');
					else if (commandIndex === 3) handleCommand('run');
					break;
			}
			return;
		}

		if (session.phase === 'moveSelect' && battleState) {
			const moveCount = battleState.player.moves.length;
			switch (event.key) {
				case 'ArrowUp':
				case 'ArrowDown':
				case 'ArrowLeft':
				case 'ArrowRight':
					event.preventDefault();
					moveIndex = navigateBattleGrid(moveIndex, event.key, moveCount);
					playGameAudio('menu-nav');
					break;
				case 'Enter':
				case ' ':
					event.preventDefault();
					{
						const move = battleState.player.moves[moveIndex];
						if (move) handleMove(move);
					}
					break;
				case 'Escape':
				case 'Backspace':
					event.preventDefault();
					closeMoveSelect(session);
					break;
			}
			return;
		}

		if (moveLearnActive && battleState) {
			const moveCount =
				moveLearnMode === 'replace' ? battleState.player.moves.length : moveLearnMoves.length;
			switch (event.key) {
				case 'ArrowUp':
				case 'ArrowDown':
				case 'ArrowLeft':
				case 'ArrowRight':
					event.preventDefault();
					moveLearnIndex = navigateBattleGrid(moveLearnIndex, event.key, moveCount);
					moveLearnHoverIndex = null;
					playGameAudio('menu-nav');
					break;
				case 'Enter':
				case ' ':
					event.preventDefault();
					if (moveLearnMode === 'replace') {
						const move = battleState.player.moves[moveLearnIndex];
						if (move) handleMoveLearnConfirm(move);
					} else {
						const move = moveLearnMoves[moveLearnIndex];
						if (move) handleMoveLearnConfirm(move);
					}
					break;
				case 'Escape':
				case 'Backspace':
					if (moveLearnMode === 'replace') {
						event.preventDefault();
						session.wonBeat = 'moveLearn';
						session.dialogText = 'Choose a move to learn.';
						session.dialogCursor = false;
					}
					break;
			}
			return;
		}

		if (
			(session.phase === 'resolving' ||
				session.dialogCursor ||
				session.phase === 'won') &&
			(event.key === 'Enter' || event.key === ' ')
		) {
			event.preventDefault();
			if (session.phase === 'resolving' && dialogBox?.skipTyping()) {
				return;
			}
			handleDialogContinue();
		}
	}

	function handleWindowKeyup(event: KeyboardEvent) {
		if (event.key === 'c' || event.key === 'C') {
			contextHeld = false;
		}
	}

	$effect(() => {
		const error = session.error;
		if (error && error !== lastShownError) {
			showGameToast(error, 'brick');
			lastShownError = error;
		}
	});
</script>

<svelte:window onkeydown={handleWindowKeydown} onkeyup={handleWindowKeyup} />

<SceneFrame backgroundSrc={backgroundSrc} backgroundAlt="Battle field" class={defeatSceneClass}>
	<div
		class="battle-scene"
	>
		{#if session.phase === 'loading'}
			<p class="battle-scene__loading">Wild vibes stirring...</p>
		{:else if battleState}
			<div class="battle-scene__arena">
				<BattleStage
					player={battleState.player}
					opponent={battleState.opponent}
					playerHp={session.displayHp.player}
					opponentHp={session.displayHp.opponent}
					entering={session.phase === 'intro'}
					{playerAttacking}
					{opponentAttacking}
					{playerHurt}
					{opponentHurt}
					{playerStatusGlow}
					{opponentStatusGlow}
					{playerFainting}
					{opponentFainting}
					{playerFainted}
					{opponentFainted}
					{projectileVisible}
					{projectileTint}
					{projectileActor}
					impactStrength={impactStrengthValue}
					{impactCrit}
					{impactPhysical}
					{impactTint}
					{statusAuraColor}
				/>
			</div>

			<div class="battle-scene__hud battle-scene__hud--opponent">
				<BattleHudPlate
					combatant={battleState.opponent}
					currentHp={session.displayHp.opponent}
					side="opponent"
					{contextHeld}
				/>
			</div>

			<div class="battle-scene__hud battle-scene__hud--player">
				<BattleHudPlate
					combatant={battleState.player}
					currentHp={session.displayHp.player}
					side="player"
					xpFillRatio={session.displayXpRatio}
					xpAnimating={session.wonBeat === 'animating'}
					{contextHeld}
				/>
			</div>

			<div
				class="battle-scene__footer"
				class:battle-scene__footer--move-learn={moveLearnActive}
			>
				<div class="battle-scene__dialog-bar">
					{#if session.phase !== 'moveSelect'}
						<div class="battle-scene__dialog">
							{#if moveLearnShowHint && moveLearnDialogHint}
								<GamePanel
									tone="status"
									class="hud-dialog-slot battle-hud-dialog battle-scene__move-learn-hint-panel"
								>
									<p class="battle-scene__move-learn-hint">{moveLearnDialogHint}</p>
								</GamePanel>
							{:else}
								<DialogBox
									bind:this={dialogBox}
									class="battle-hud-dialog"
									text={session.dialogText}
									emphasis={dialogEmphasis}
									showCursor={session.dialogCursor || session.phase === 'command'}
									typewriter={session.phase === 'resolving'}
									onContinue={session.dialogCursor ? handleDialogContinue : undefined}
									onCursorDown={session.phase === 'command' && !session.dialogCursor
										? handleCommandDown
										: undefined}
								/>
							{/if}
						</div>
					{/if}

					{#if session.phase === 'command'}
						<div class="battle-scene__menu-overlay">
							<CommandMenu
								selected={commandIndex}
								onSelect={(index) => {
									commandIndex = index;
									playGameAudio('menu-nav');
								}}
								onConfirm={handleCommand}
							/>
						</div>
					{:else if session.phase === 'moveSelect'}
						<div class="battle-scene__move-overlay">
							<MoveMenu
								moves={battleState.player.moves}
								selected={moveIndex}
								{contextHeld}
								onSelect={(index) => {
									if (index >= 0) moveIndex = index;
								}}
								onConfirm={handleMove}
							/>
						</div>
					{/if}
				</div>
			</div>

			<p class="battle-scene__deck-hint" class:battle-scene__deck-hint--visible={!contextHeld}>
				Hold C — Read
			</p>

			{#if moveLearnActive}
				<MoveLearnMenu
					moves={moveLearnMoves}
					activeMoves={battleState.player.moves}
					emoteSrc={moveLearnEmoteSrc}
					combatant={moveLearnCombatant}
					mode={moveLearnMode}
					selected={moveLearnIndex}
					levelRequirements={moveLearnLevelReqs}
					{contextHeld}
					onSelect={(index) => {
						if (index >= 0) moveLearnIndex = index;
					}}
					onHover={(index) => {
						moveLearnHoverIndex = index;
					}}
					onConfirm={handleMoveLearnConfirm}
					onDecline={() => void declineCurrentMoveOffer(session)}
				/>
			{/if}
		{/if}
	</div>
</SceneFrame>

<style>
	.battle-scene {
		/* Match EncounterSeek / crew footer inset — not just the wood bezel width. */
		--vm-battle-hud-inset: var(--vm-hud-bottom-inset);
		--vm-battle-hud-side-inset: calc(var(--vm-battle-hud-inset) * 2);
		--vm-battle-hud-column-width: 30%;
		--vm-battle-hud-panel-gutter: var(--vm-space-sm);

		position: relative;
		display: flex;
		flex-direction: column;
		min-height: 100dvh;
		padding: var(--vm-battle-hud-inset);
		box-sizing: border-box;
	}

	.battle-scene__arena {
		position: relative;
		flex: 1 1 auto;
		min-height: 0;
		z-index: 1;
		isolation: isolate;
	}

	.battle-scene__hud {
		position: absolute;
		z-index: 5;
		display: flex;
		width: var(--vm-battle-hud-column-width);
		pointer-events: auto;
	}

	.battle-scene__hud--opponent {
		top: calc(var(--vm-battle-hud-inset) + var(--vm-battle-hud-panel-gutter));
		left: var(--vm-battle-hud-side-inset);
		justify-content: flex-start;
	}

	.battle-scene__hud--player {
		right: var(--vm-battle-hud-side-inset);
		bottom: calc(
			var(--vm-battle-hud-inset) + var(--vm-hud-dialog-slot-height) + var(--vm-battle-hud-panel-gutter)
		);
		justify-content: flex-end;
	}

	.battle-scene__loading {
		margin: auto;
		font-family: var(--vm-font-ui);
		font-size: var(--vm-text-caption);
		color: var(--vm-parchment);
		text-align: center;
	}

	.battle-scene__footer {
		position: relative;
		z-index: 3;
		flex: 0 0 var(--vm-hud-dialog-slot-height);
		width: 100%;
		margin-top: auto;
		overflow: hidden;
	}

	.battle-scene__footer--move-learn {
		z-index: 1001;
	}

	.battle-scene__dialog-bar {
		position: relative;
		width: 100%;
		height: 100%;
	}

	.battle-scene__dialog {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: stretch;
	}

	.battle-scene__dialog :global(.dialog-box.battle-hud-dialog) {
		display: flex;
		flex: 1 1 auto;
		flex-direction: column;
		align-self: stretch;
		width: 100%;
		height: 100%;
		min-height: 0;
		min-width: 0;
	}

	.battle-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__frame),
	.battle-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__inset),
	.battle-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__surface),
	.battle-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__content) {
		display: flex;
		flex: 1 1 auto;
		flex-direction: column;
		width: 100%;
		height: 100%;
		min-height: 0;
		min-width: 0;
		box-sizing: border-box;
	}

	.battle-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__frame) {
		box-shadow: none;
	}

	.battle-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__surface) {
		flex: 1 1 auto;
	}

	.battle-scene__dialog :global(.dialog-box.battle-hud-dialog .dialog-box__content) {
		flex: 1 1 auto;
		height: auto;
		min-height: 0;
	}

	.battle-scene__dialog :global(.battle-scene__move-learn-hint-panel.hud-dialog-slot) {
		display: flex;
		flex: 1 1 auto;
		flex-direction: column;
		align-self: stretch;
		width: 100%;
		height: 100%;
		min-height: 0;
		min-width: 0;
	}

	.battle-scene__dialog :global(.battle-scene__move-learn-hint-panel .game-panel__frame),
	.battle-scene__dialog :global(.battle-scene__move-learn-hint-panel .game-panel__inset),
	.battle-scene__dialog :global(.battle-scene__move-learn-hint-panel .game-panel__surface),
	.battle-scene__dialog :global(.battle-scene__move-learn-hint-panel .game-panel__content) {
		display: flex;
		flex: 1 1 auto;
		flex-direction: column;
		width: 100%;
		height: 100%;
		min-height: 0;
		min-width: 0;
		box-sizing: border-box;
	}

	.battle-scene__dialog :global(.battle-scene__move-learn-hint-panel .game-panel__content) {
		justify-content: center;
	}

	.battle-scene__move-learn-hint {
		margin: 0;
		flex: 1;
		min-width: 0;
		font-family: var(--vm-font-ui);
		font-weight: 400;
		font-size: var(--vm-hud-font-dialog-ui);
		line-height: calc(var(--vm-hud-dialog-content-height) / 2);
		color: inherit;
		white-space: pre-line;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		overflow: hidden;
	}

	.battle-scene__menu-overlay {
		position: absolute;
		top: 0;
		right: 0;
		bottom: 0;
		z-index: 2;
		display: flex;
		flex-direction: column;
		width: var(--vm-battle-hud-column-width);
	}

	.battle-scene__menu-overlay :global(.command-menu.game-panel) {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		width: 100%;
		height: 100%;
		min-height: 0;
		box-shadow: none;
	}

	.battle-scene__menu-overlay :global(.command-menu .game-panel__frame) {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		box-shadow: none;
	}

	.battle-scene__menu-overlay :global(.command-menu .game-panel__inset),
	.battle-scene__menu-overlay :global(.command-menu .game-panel__surface),
	.battle-scene__menu-overlay :global(.command-menu .game-panel__content) {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}

	.battle-scene__move-overlay {
		position: absolute;
		inset: 0;
		z-index: 2;
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.battle-scene__move-overlay :global(.move-menu) {
		flex: 1 1 auto;
		height: 100%;
		min-height: 0;
	}

	.battle-scene__deck-hint {
		position: absolute;
		right: var(--vm-battle-hud-side-inset);
		bottom: calc(
			var(--vm-battle-hud-inset) + var(--vm-hud-dialog-slot-height) + var(--vm-battle-hud-panel-gutter)
		);
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: 0.5625rem;
		color: color-mix(in srgb, var(--vm-parchment) 72%, transparent);
		opacity: 0;
		transition: opacity 180ms steps(4);
	}

	.battle-scene__deck-hint--visible {
		opacity: 1;
	}

	@media (max-width: 480px) {
		.battle-scene {
			--vm-battle-hud-column-width: 34%;
		}
	}

	:global(.scene-frame.scene-frame--battle-defeat) {
		animation: battle-defeat-desaturate 1.4s ease forwards;
	}

	@keyframes battle-defeat-desaturate {
		from {
			filter: grayscale(0);
		}
		to {
			filter: grayscale(1);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		:global(.scene-frame.scene-frame--battle-defeat) {
			animation: none;
			filter: grayscale(1);
		}
	}
</style>
