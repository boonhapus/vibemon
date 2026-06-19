import type {
	BattleCombatant,
	BattleFinish,
	BattleMove,
	BattleState,
	BattleTurn,
	HeroProgression,
	MoveLearnOffer,
	MoveLearnOption
} from './battleApi';
import {
	acceptMoveLearn,
	declineMoveLearn,
	fetchBattle,
	finishBattle,
	submitBattleRun,
	submitBattleTurn
} from './battleApi';
import { formatStatDeltaLine } from './battleStatLabels';
import { moveAnimationKind } from './MoveAnimator';

export type BattlePhase =
	| 'loading'
	| 'intro'
	| 'command'
	| 'moveSelect'
	| 'resolving'
	| 'won'
	| 'defeat'
	| 'fled';

export type MoveHighlight = {
	name: string;
	type: string;
	category: 'physical' | 'special' | 'status';
};

export type ReplayStep =
	| { kind: 'message'; text: string; moveHighlight?: MoveHighlight }
	| { kind: 'hp'; side: 'player' | 'opponent'; hp: number }
	| {
			kind: 'animation';
			profile: 'physical' | 'special' | 'status';
			actor: 'player' | 'opponent';
			moveType: string;
	  }
	| {
			kind: 'hurt';
			side: 'player' | 'opponent';
			effectiveness: number;
			crit: boolean;
			sourceType?: string;
			category?: 'physical' | 'special' | 'status';
	  }
	| { kind: 'faint'; side: 'player' | 'opponent' };

type HpTween = {
	side: 'player' | 'opponent';
	target: number;
	timer: ReturnType<typeof setInterval> | null;
	/** Actual runtime of this drain (scales with HP lost) — drives auto-advance. */
	durationMs: number;
};

type XpTween = {
	target: number;
	timer: ReturnType<typeof setInterval> | null;
	onSettled?: () => void;
};

export type WonBeat = 'idle' | 'animating' | 'xp' | 'levelUp' | 'moveLearnIntro' | 'moveLearn' | 'moveLearnReplace';

export type MoveLearnPending = {
	offer: MoveLearnOffer;
	selectedMove: MoveLearnOption | null;
};

export type BattleSessionState = {
	battleId: string;
	phase: BattlePhase;
	state: BattleState | null;
	displayHp: { player: number; opponent: number };
	displayXpRatio: number;
	dialogText: string;
	dialogMoveHighlight: MoveHighlight | null;
	dialogCursor: boolean;
	replayQueue: ReplayStep[];
	replayIndex: number;
	busy: boolean;
	error: string | null;
	finishResult: BattleFinish | null;
	hpTween: HpTween | null;
	xpTween: XpTween | null;
	wonBeat: WonBeat;
	moveOfferIndex: number;
	moveLearnPending: MoveLearnPending | null;
	faintedSides: { player: boolean; opponent: boolean };
};

export function createBattleSession(battleId: string): BattleSessionState {
	return {
		battleId,
		phase: 'loading',
		state: null,
		displayHp: { player: 0, opponent: 0 },
		displayXpRatio: 0,
		dialogText: '',
		dialogMoveHighlight: null,
		dialogCursor: false,
		replayQueue: [],
		replayIndex: 0,
		busy: false,
		error: null,
		finishResult: null,
		hpTween: null,
		xpTween: null,
		wonBeat: 'idle',
		moveOfferIndex: 0,
		moveLearnPending: null,
		faintedSides: { player: false, opponent: false }
	};
}

const HP_TWEEN_STEPS = 14;
const HP_TWEEN_STEP_MS = 45;
/** Drain cadence is fixed; the frame count scales with HP lost so a big crit
    visibly takes longer to empty than a chip hit. ponytail: linear in HP lost,
    capped at HP_TWEEN_MAX_STEPS frames (~1.35s) so huge drops still settle. */
const HP_TWEEN_MAX_STEPS = 30;

function hpTweenPlan(from: number, target: number): { stepSize: number; durationMs: number } {
	const magnitude = Math.abs(target - from);
	const stepSize = Math.max(1, Math.ceil(magnitude / HP_TWEEN_MAX_STEPS));
	const frames = Math.max(1, Math.ceil(magnitude / stepSize));
	return { stepSize, durationMs: frames * HP_TWEEN_STEP_MS };
}

/** Real drain duration for a given HP change — scales with the amount lost. */
export function hpTweenDurationMs(from: number, target: number): number {
	return from === target ? 0 : hpTweenPlan(from, target).durationMs;
}
const XP_TWEEN_STEPS = 14;
const XP_TWEEN_STEP_MS = 45;

/** Match `tokens.css` battle animation durations. */
/** Full contact-lunge runtime (must match `--anim-attack-duration`). */
export const ATTACK_VISUAL_MS = 600;
/**
 * The replay advances to the hit (hurt flash + burst + shake) at the lunge's
 * contact peak rather than after the attacker has fully recovered, so melee
 * impact lands in sync with the dash. The lunge keeps playing for
 * `ATTACK_VISUAL_MS` via a separate visual flag in `BattleScene`.
 */
export const REPLAY_ATTACK_MS = 220;
export const REPLAY_PROJECTILE_MS = 620;
export const REPLAY_HURT_MS = 1050;
/** Baseline drain runtime / fallback when no tween is active; live drains use
    `hpTweenDurationMs`, which scales the wait with the HP actually lost. */
export const REPLAY_HP_TWEEN_MS = HP_TWEEN_STEPS * HP_TWEEN_STEP_MS;
export const REPLAY_FAINT_MS = 720;
export const REPLAY_XP_TWEEN_MS = XP_TWEEN_STEPS * XP_TWEEN_STEP_MS;

let replayAutoAdvanceTimer: ReturnType<typeof setTimeout> | null = null;

function setDialogMessage(
	session: BattleSessionState,
	text: string,
	moveHighlight: MoveHighlight | null = null
): void {
	session.dialogText = text;
	session.dialogMoveHighlight = moveHighlight;
}

function clearReplayAutoAdvance(): void {
	if (replayAutoAdvanceTimer !== null) {
		clearTimeout(replayAutoAdvanceTimer);
		replayAutoAdvanceTimer = null;
	}
}

export function replayStepDelayMs(step: ReplayStep): number | null {
	switch (step.kind) {
		case 'message':
			return null;
		case 'animation':
			return step.profile === 'special' ? REPLAY_PROJECTILE_MS : REPLAY_ATTACK_MS;
		case 'hurt':
			return REPLAY_HURT_MS;
		case 'hp':
			return REPLAY_HP_TWEEN_MS;
		case 'faint':
			return REPLAY_FAINT_MS;
	}
}

function clearHpTween(session: BattleSessionState): void {
	if (session.hpTween?.timer) clearInterval(session.hpTween.timer);
	session.hpTween = null;
}

function clearXpTween(session: BattleSessionState): void {
	if (session.xpTween?.timer) clearInterval(session.xpTween.timer);
	session.xpTween = null;
}

function settleXpTween(session: BattleSessionState): void {
	const tween = session.xpTween;
	if (!tween) return;
	session.displayXpRatio = tween.target;
	const onSettled = tween.onSettled;
	clearXpTween(session);
	onSettled?.();
}

function settleHpTween(session: BattleSessionState): void {
	const tween = session.hpTween;
	if (!tween) return;
	session.displayHp[tween.side] = tween.target;
	clearHpTween(session);
}

function startHpTween(
	session: BattleSessionState,
	side: 'player' | 'opponent',
	target: number
): void {
	settleHpTween(session);
	const from = session.displayHp[side];
	if (from === target) return;
	const direction = target > from ? 1 : -1;
	const { stepSize, durationMs } = hpTweenPlan(from, target);
	const timer = setInterval(() => {
		const next = session.displayHp[side] + direction * stepSize;
		if ((direction > 0 && next >= target) || (direction < 0 && next <= target)) {
			settleHpTween(session);
		} else {
			session.displayHp[side] = next;
		}
	}, HP_TWEEN_STEP_MS);
	session.hpTween = { side, target, timer, durationMs };
}

function syncFaintedVisibility(session: BattleSessionState): void {
	if (!session.state) return;
	session.faintedSides = {
		player: session.state.player.is_fainted,
		opponent: session.state.opponent.is_fainted
	};
}

export async function bootstrapBattleSession(session: BattleSessionState): Promise<void> {
	session.busy = true;
	session.error = null;
	try {
		const state = await fetchBattle(session.battleId);
		session.state = state;
		session.displayHp = { player: state.player.current_hp, opponent: state.opponent.current_hp };
		session.displayXpRatio = state.player.xp_bar_ratio;
		if (state.concluded) {
			session.phase = resolveEndPhase(state);
			setDialogMessage(session, endDialogForPhase(session.phase, state));
			session.dialogCursor = true;
			syncFaintedVisibility(session);
			return;
		}
		session.faintedSides = { player: false, opponent: false };
		session.phase = 'intro';
		setDialogMessage(session, `A wild ${state.opponent.name} steps out.`);
		session.dialogCursor = true;
	} catch (error) {
		session.error = error instanceof Error ? error.message : 'Could not load battle.';
	} finally {
		session.busy = false;
	}
}

export function advanceIntro(session: BattleSessionState): void {
	if (session.phase !== 'intro' || !session.state) return;
	session.phase = 'command';
	setDialogMessage(session, 'What will you do?');
	session.dialogCursor = false;
}

export function openMoveSelect(session: BattleSessionState): void {
	if (session.phase !== 'command' || session.busy) return;
	session.phase = 'moveSelect';
	setDialogMessage(session, 'Choose a move.');
	session.dialogCursor = false;
}

export function closeMoveSelect(session: BattleSessionState): void {
	if (session.phase !== 'moveSelect') return;
	session.phase = 'command';
	setDialogMessage(session, 'What will you do?');
	session.dialogCursor = false;
}

export async function chooseRun(session: BattleSessionState): Promise<void> {
	if (session.phase !== 'command' || session.busy || !session.state) return;
	await resolveTurn(session, () => submitBattleRun(session.battleId));
}

export async function chooseMove(session: BattleSessionState, moveName: string): Promise<void> {
	if (session.phase !== 'moveSelect' || session.busy) return;
	await resolveTurn(session, () => submitBattleTurn(session.battleId, moveName));
}

async function resolveTurn(
	session: BattleSessionState,
	request: () => Promise<BattleTurn>
): Promise<void> {
	session.busy = true;
	session.error = null;
	try {
		const turn = await request();
		clearReplayAutoAdvance();
		clearHpTween(session);
		session.state = turn.state;
		session.faintedSides = { player: false, opponent: false };
		if (!session.xpTween) {
			session.displayXpRatio = turn.state.player.xp_bar_ratio;
		}
		session.replayQueue = buildReplayQueue(turn);
		session.replayIndex = 0;
		session.phase = 'resolving';
		applyReplayStep(session);
	} catch (error) {
		session.error = error instanceof Error ? error.message : 'Turn failed.';
		session.phase = session.state?.concluded ? resolveEndPhase(session.state) : 'command';
	} finally {
		session.busy = false;
	}
}

export function advanceReplay(session: BattleSessionState): void {
	if (session.phase !== 'resolving') return;
	clearReplayAutoAdvance();
	// Snap any in-progress HP drain to its target before moving on.
	settleHpTween(session);
	const current = session.replayQueue[session.replayIndex];
	if (current?.kind === 'faint') {
		session.faintedSides[current.side] = true;
	}
	const nextIndex = session.replayIndex + 1;
	if (nextIndex >= session.replayQueue.length) {
		void concludeReplay(session);
		return;
	}
	session.replayIndex = nextIndex;
	applyReplayStep(session);
}

function scheduleReplayAutoAdvance(session: BattleSessionState, step: ReplayStep): void {
	clearReplayAutoAdvance();
	let delayMs = replayStepDelayMs(step);
	if (delayMs === null) return;
	if (step.kind === 'hp') {
		// Match the wait to this drain's real (HP-scaled) runtime, not the baseline.
		delayMs = session.hpTween ? session.hpTween.durationMs : 0;
	}
	replayAutoAdvanceTimer = setTimeout(() => {
		replayAutoAdvanceTimer = null;
		if (session.phase === 'resolving') {
			advanceReplay(session);
		}
	}, delayMs);
}

function applyReplayStep(session: BattleSessionState): void {
	const step = session.replayQueue[session.replayIndex];
	if (!step) return;
	switch (step.kind) {
		case 'message':
			setDialogMessage(session, step.text, step.moveHighlight ?? null);
			session.dialogCursor = true;
			break;
		case 'hp':
			session.dialogCursor = false;
			startHpTween(session, step.side, step.hp);
			break;
		case 'animation':
		case 'hurt':
		case 'faint':
			session.dialogCursor = false;
			break;
	}
	scheduleReplayAutoAdvance(session, step);
}

async function concludeReplay(session: BattleSessionState): Promise<void> {
	if (!session.state || session.phase !== 'resolving') return;

	// Claim the phase before any await so a second advanceReplay cannot re-enter.
	const endPhase = session.state.concluded ? resolveEndPhase(session.state) : 'command';
	session.phase = endPhase;

	clearReplayAutoAdvance();
	clearHpTween(session);
	session.displayHp = {
		player: session.state.player.current_hp,
		opponent: session.state.opponent.current_hp
	};
	session.replayQueue = [];
	session.replayIndex = 0;

	if (endPhase !== 'won' && endPhase !== 'defeat' && endPhase !== 'fled') {
		setDialogMessage(session, 'What will you do?');
		session.dialogCursor = false;
		return;
	}

	setDialogMessage(session, endDialogForPhase(endPhase, session.state));
	session.dialogCursor = true;
	try {
		if (!session.finishResult) {
			session.finishResult = await finishBattle(session.battleId);
		}
		const progression = session.finishResult.progression;
		if (endPhase === 'won' && progression) {
			startXpGainAnimation(session, progression);
		}
	} catch (error) {
		session.error = error instanceof Error ? error.message : 'Could not finish battle.';
	}
	syncFaintedVisibility(session);
}

function resolveEndPhase(state: BattleState): BattlePhase {
	if (state.fled) return 'fled';
	if (state.winner_trainer_id === state.player_trainer_id) return 'won';
	return 'defeat';
}

/** Patch hero HUD fields from finish progression. */
export function patchHeroProgression(
	combatant: BattleCombatant,
	progression: HeroProgression
): void {
	combatant.xp = progression.new_xp;
	combatant.level = progression.new_level;
	combatant.xp_to_next = progression.xp_to_next;
	combatant.xp_bar_ratio = progression.xp_bar_ratio;
	const hpDelta = progression.stat_deltas?.find((entry) => entry.stat === 'hp');
	if (hpDelta) {
		combatant.max_hp = hpDelta.new;
		combatant.current_hp = Math.min(hpDelta.new, combatant.current_hp + hpDelta.delta);
	}
}

export function xpGainedDialogText(
	combatant: BattleCombatant,
	progression: HeroProgression
): string {
	const xpGained = Math.max(0, progression.new_xp - progression.previous_xp);
	return `${combatant.name} gained ${xpGained} XP!`;
}

export function levelUpDialogText(
	combatant: BattleCombatant,
	progression: HeroProgression
): string {
	if (!progression.leveled_up) return '';
	const headline = `${combatant.name} grew to Lv ${progression.new_level}!`;
	const deltas = progression.stat_deltas ?? [];
	if (deltas.length === 0) return headline;
	return `${headline}\n${formatStatDeltaLine(deltas)}`;
}

/** Patch hero HUD fields and return level-up dialog when applicable. */
export function applyHeroProgression(
	combatant: BattleCombatant,
	progression: HeroProgression
): string {
	patchHeroProgression(combatant, progression);
	return levelUpDialogText(combatant, progression);
}

function tweenXpRatio(
	session: BattleSessionState,
	target: number,
	onSettled?: () => void
): void {
	settleXpTween(session);
	const from = session.displayXpRatio;
	if (Math.abs(from - target) < 0.001) {
		session.displayXpRatio = target;
		onSettled?.();
		return;
	}
	const direction = target > from ? 1 : -1;
	const stepSize = Math.max(0.01, Math.abs(target - from) / XP_TWEEN_STEPS);
	const timer = setInterval(() => {
		const next = session.displayXpRatio + direction * stepSize;
		if ((direction > 0 && next >= target) || (direction < 0 && next <= target)) {
			session.displayXpRatio = target;
			const onSettled = session.xpTween?.onSettled;
			clearXpTween(session);
			onSettled?.();
		} else {
			session.displayXpRatio = next;
		}
	}, XP_TWEEN_STEP_MS);
	session.xpTween = { target, timer, onSettled };
}

function completeXpGainAnimation(
	session: BattleSessionState,
	progression: HeroProgression
): void {
	if (!session.state) return;
	patchHeroProgression(session.state.player, progression);
	session.displayHp.player = session.state.player.current_hp;
	session.displayXpRatio = progression.xp_bar_ratio;
	setDialogMessage(session, xpGainedDialogText(session.state.player, progression));
	session.dialogCursor = true;
	session.wonBeat = 'xp';
}

export function startXpGainAnimation(
	session: BattleSessionState,
	progression: HeroProgression
): void {
	if (!session.state) return;
	const from = session.state.player.xp_bar_ratio;
	const to = progression.xp_bar_ratio;
	session.wonBeat = 'animating';
	setDialogMessage(session, '');
	session.dialogCursor = false;
	session.displayXpRatio = from;

	if (progression.leveled_up) {
		tweenXpRatio(session, 1, () => {
			if (!session.state) return;
			session.state.player.level = progression.new_level;
			session.displayXpRatio = 0;
			tweenXpRatio(session, to, () => completeXpGainAnimation(session, progression));
		});
		return;
	}

	tweenXpRatio(session, to, () => completeXpGainAnimation(session, progression));
}

/** Advance the post-win dialog chain. Returns true when the player may leave the battle. */
export function advanceWonBeat(session: BattleSessionState): boolean {
	if (session.phase !== 'won') return false;

	if (session.wonBeat === 'animating') {
		clearXpTween(session);
		const progression = session.finishResult?.progression;
		if (progression) {
			completeXpGainAnimation(session, progression);
		}
		return false;
	}

	if (session.wonBeat === 'xp') {
		const progression = session.finishResult?.progression;
		if (progression?.leveled_up && session.state) {
			setDialogMessage(session, levelUpDialogText(session.state.player, progression));
			session.wonBeat = 'levelUp';
			session.dialogCursor = true;
			return false;
		}
		return beginMoveLearnBeat(session);
	}

	if (session.wonBeat === 'levelUp') {
		return beginMoveLearnBeat(session);
	}

	if (session.wonBeat === 'moveLearnIntro') {
		session.wonBeat = 'moveLearn';
		setDialogMessage(session, 'Choose a move to learn.');
		session.dialogCursor = false;
		return false;
	}

	if (session.wonBeat === 'moveLearn' || session.wonBeat === 'moveLearnReplace') {
		return false;
	}

	return true;
}

function currentMoveOffer(session: BattleSessionState): MoveLearnOffer | null {
	const offers = session.finishResult?.move_offers ?? [];
	return offers[session.moveOfferIndex] ?? null;
}

function beginMoveLearnBeat(session: BattleSessionState): boolean {
	const offer = currentMoveOffer(session);
	if (!offer) {
		session.wonBeat = 'idle';
		return true;
	}
	session.moveLearnPending = { offer, selectedMove: null };
	session.wonBeat = 'moveLearnIntro';
	setDialogMessage(session, `${offer.vibemon_name} is ready to learn a new move.`);
	session.dialogCursor = true;
	return false;
}

function moveLearnOptionToBattleMove(option: MoveLearnOption): BattleMove {
	return {
		id: option.id,
		name: option.name,
		type: option.type,
		category: option.category,
		power: option.power,
		accuracy: option.accuracy,
		pp_current: option.pp,
		pp_max: option.pp,
		effectiveness: 1,
		flavor_text: option.flavor_text,
		combat_hints: option.combat_hints ?? []
	};
}

function patchCombatantMove(
	combatant: BattleCombatant,
	move: MoveLearnOption,
	replaceContentId?: string
): void {
	const battleMove = moveLearnOptionToBattleMove(move);
	if (replaceContentId) {
		const slot = combatant.moves.findIndex((entry) => entry.id === replaceContentId);
		if (slot >= 0) {
			combatant.moves[slot] = battleMove;
		}
		return;
	}
	combatant.moves = [...combatant.moves, battleMove];
}

async function advanceMoveOfferQueue(session: BattleSessionState): Promise<void> {
	session.moveOfferIndex += 1;
	session.moveLearnPending = null;
	if (currentMoveOffer(session)) {
		beginMoveLearnBeat(session);
		return;
	}
	session.wonBeat = 'idle';
	setDialogMessage(session, '');
	session.dialogCursor = true;
}

export async function declineCurrentMoveOffer(session: BattleSessionState): Promise<void> {
	const offer = currentMoveOffer(session);
	if (!offer || session.busy) return;
	session.busy = true;
	session.error = null;
	try {
		await declineMoveLearn(session.battleId, { vibemon_id: offer.vibemon_id });
		await advanceMoveOfferQueue(session);
	} catch (error) {
		session.error = error instanceof Error ? error.message : 'Could not decline offer.';
	} finally {
		session.busy = false;
	}
}

export async function selectMoveLearnOption(
	session: BattleSessionState,
	move: MoveLearnOption
): Promise<void> {
	const offer = currentMoveOffer(session);
	if (!offer || session.busy) return;
	if (offer.requires_replace && session.wonBeat === 'moveLearn') {
		session.moveLearnPending = { offer, selectedMove: move };
		session.wonBeat = 'moveLearnReplace';
		setDialogMessage(session, `Replace a move with ${move.name}.`);
		session.dialogCursor = false;
		return;
	}
	await confirmMoveLearn(session, move);
}

export async function confirmMoveLearnReplacement(
	session: BattleSessionState,
	replaceMove: BattleMove
): Promise<void> {
	const pending = session.moveLearnPending;
	if (!pending?.selectedMove || session.busy) return;
	await confirmMoveLearn(session, pending.selectedMove, replaceMove.id);
}

async function confirmMoveLearn(
	session: BattleSessionState,
	move: MoveLearnOption,
	replaceContentId?: string
): Promise<void> {
	const offer = currentMoveOffer(session);
	if (!offer) return;
	session.busy = true;
	session.error = null;
	try {
		await acceptMoveLearn(session.battleId, {
			vibemon_id: offer.vibemon_id,
			move_content_id: move.id,
			replace_content_id: replaceContentId
		});
		if (session.state && session.state.player.vibemon_id === offer.vibemon_id) {
			patchCombatantMove(session.state.player, move, replaceContentId);
		}
		await advanceMoveOfferQueue(session);
	} catch (error) {
		session.error = error instanceof Error ? error.message : 'Could not learn move.';
	} finally {
		session.busy = false;
	}
}

export function currentMoveLearnOffer(session: BattleSessionState): MoveLearnOffer | null {
	return currentMoveOffer(session);
}

export function moveLearnPickerMoves(session: BattleSessionState): BattleMove[] {
	const offer = currentMoveOffer(session);
	if (!offer) return [];
	return offer.moves.map(moveLearnOptionToBattleMove);
}

function endDialogForPhase(phase: BattlePhase, state: BattleState): string {
	switch (phase) {
		case 'won':
			return '';
		case 'defeat':
			return 'You and your crew head home to rest.';
		case 'fled':
			return 'You slip away.';
		default:
			return '';
	}
}

/**
 * Build the replay in true event order so visuals never run ahead of copy.
 * Backend emits exactly one message per event, index-aligned, so we reuse it
 * as the canonical dialog string for each event rather than front-loading them.
 */
export function buildReplayQueue(turn: BattleTurn): ReplayStep[] {
	const queue: ReplayStep[] = [];
	const playerName = turn.state.player.name;

	const sideOf = (target: unknown): 'player' | 'opponent' =>
		target === playerName ? 'player' : 'opponent';

	turn.events.forEach((event, index) => {
		const message = turn.messages[index] ?? '';
		switch (event.kind) {
			case 'move_used': {
				const actor = event.user === playerName ? 'player' : 'opponent';
				const move = (actor === 'player' ? turn.state.player : turn.state.opponent).moves.find(
					(entry) => entry.name === event.move
				);
				if (message) {
					queue.push({
						kind: 'message',
						text: message,
						moveHighlight: move
							? { name: move.name, type: move.type, category: move.category }
							: { name: event.move as string, type: 'normal', category: 'physical' }
					});
				}
				queue.push({
					kind: 'animation',
					profile: move ? moveAnimationKind(move) : 'physical',
					actor,
					moveType: move?.type ?? 'normal'
				});
				break;
			}
			case 'damage':
			case 'status_damage': {
				const side = sideOf(event.target);
				const hpAfter = event.hp_after;
				const effectiveness = typeof event.effectiveness === 'number' ? event.effectiveness : 1;
				const crit = event.is_crit === true;
				const sourceMove =
					typeof event.move === 'string'
						? (event.source === playerName ? turn.state.player : turn.state.opponent).moves.find(
								(entry) => entry.name === event.move
							)
						: undefined;
				const sourceType = sourceMove?.type;
				const category = sourceMove?.category;
				queue.push({ kind: 'hurt', side, effectiveness, crit, sourceType, category });
				if (typeof hpAfter === 'number') queue.push({ kind: 'hp', side, hp: hpAfter });
				if (message) queue.push({ kind: 'message', text: message });
				break;
			}
			case 'heal': {
				const side = sideOf(event.target);
				const hpAfter = event.hp_after;
				if (typeof hpAfter === 'number') queue.push({ kind: 'hp', side, hp: hpAfter });
				if (message) queue.push({ kind: 'message', text: message });
				break;
			}
			case 'faint': {
				const side = sideOf(event.target);
				queue.push({ kind: 'faint', side });
				if (message) queue.push({ kind: 'message', text: message });
				break;
			}
			default: {
				if (message) queue.push({ kind: 'message', text: message });
			}
		}
	});

	return queue;
}

export function currentReplayStep(session: BattleSessionState): ReplayStep | null {
	return session.replayQueue[session.replayIndex] ?? null;
}
