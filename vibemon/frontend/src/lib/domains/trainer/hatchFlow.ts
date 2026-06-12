/** Hatch review flow state, guards, and orchestration actions. */

import type { CandidateAction, HatchCandidate } from './hatchApi';
import {
	adoptCandidate,
	generateCandidate,
	rejectCandidate,
	refreshCandidate
} from './hatchApi';
import {
	HATCH_BEAT_CRACK_MS,
	HATCH_BEAT_STIR_MS,
	HATCH_REFRESH_LINE,
	preloadImage,
	runHatchSuspense
} from './hatchSuspense';
import type { ProviderSelectionState } from './providerSelection';

export const HATCH_FLOW_KEY = 'trainer-hatch-flow';
export const HATCH_REVEAL_MS = 720;

export type HatchPhase = 'idle' | 'generating' | 'revealing' | 'reviewing' | 'busy';

export type HatchActionHint = 'refresh' | 'adopt' | 'release';

export type HatchFlowState = {
	candidate: HatchCandidate | null;
	crewCount: number;
	spriteVisible: boolean;
	generating: boolean;
	generatingLine: string;
	beat: 0 | 1 | 2 | 3;
	revealing: boolean;
	busy: boolean;
	actionHint: HatchActionHint | null;
	candidateHint: string | null;
	adoptModalOpen: boolean;
};

export type HatchFlowBlockers = {
	settingsOpen: boolean;
	providerModalOpen: boolean;
};

export type HatchFlowDeps = {
	providers: ProviderSelectionState;
	bypassCredits: () => boolean;
	showToast: (message: string, tone: 'amber' | 'brick' | 'sage') => void;
	onPersist: () => void;
	onClearScene: () => void;
	goto: (path: string) => void | Promise<void>;
	prefersReducedMotion: () => boolean;
};

export function createHatchFlowState(initial?: Partial<HatchFlowState>): HatchFlowState {
	return {
		candidate: initial?.candidate ?? null,
		crewCount: initial?.crewCount ?? 0,
		spriteVisible: initial?.spriteVisible ?? false,
		generating: initial?.generating ?? false,
		generatingLine: initial?.generatingLine ?? '',
		beat: initial?.beat ?? 0,
		revealing: initial?.revealing ?? false,
		busy: initial?.busy ?? false,
		actionHint: initial?.actionHint ?? null,
		candidateHint: initial?.candidateHint ?? null,
		adoptModalOpen: initial?.adoptModalOpen ?? false
	};
}

export function hatchPhase(state: HatchFlowState): HatchPhase {
	if (state.generating) return 'generating';
	if (state.revealing) return 'revealing';
	if (state.busy) return 'busy';
	if (state.candidate) return 'reviewing';
	return 'idle';
}

export function hatchControlsBlocked(state: HatchFlowState, blockers: HatchFlowBlockers): boolean {
	return (
		blockers.settingsOpen ||
		blockers.providerModalOpen ||
		state.adoptModalOpen ||
		state.generating ||
		state.busy
	);
}

export function releaseDisabled(state: HatchFlowState): boolean {
	return state.crewCount === 0;
}

export function canGenerate(
	state: HatchFlowState,
	blockers: HatchFlowBlockers,
	selectedProviderCount: number
): boolean {
	return (
		!hatchControlsBlocked(state, blockers) &&
		!state.candidate &&
		selectedProviderCount > 0
	);
}

export function canReject(state: HatchFlowState, blockers: HatchFlowBlockers): boolean {
	return Boolean(state.candidate) && !releaseDisabled(state) && !hatchControlsBlocked(state, blockers);
}

export function canRefresh(state: HatchFlowState, blockers: HatchFlowBlockers): boolean {
	return Boolean(state.candidate) && !hatchControlsBlocked(state, blockers);
}

export function canAdopt(state: HatchFlowState, blockers: HatchFlowBlockers): boolean {
	return Boolean(state.candidate) && !hatchControlsBlocked(state, blockers);
}

export function applyCandidateAction(state: HatchFlowState, action: CandidateAction | null): void {
	if (!action) {
		state.candidate = null;
		return;
	}
	state.candidate = action.candidate;
	state.crewCount = action.crew_count;
}

export function clearHatchCandidate(state: HatchFlowState): void {
	state.candidate = null;
	state.spriteVisible = false;
	state.actionHint = null;
	state.candidateHint = null;
}

function startHatchBeats(state: HatchFlowState): () => void {
	state.beat = 1;
	const stirTimer = window.setTimeout(() => {
		state.beat = 2;
	}, HATCH_BEAT_STIR_MS);
	const crackTimer = window.setTimeout(() => {
		state.beat = 3;
	}, HATCH_BEAT_CRACK_MS);
	return () => {
		window.clearTimeout(stirTimer);
		window.clearTimeout(crackTimer);
		state.beat = 0;
	};
}

function triggerHatchReveal(state: HatchFlowState, deps: HatchFlowDeps): void {
	state.spriteVisible = true;
	deps.onPersist();
	state.revealing = true;
	const duration = deps.prefersReducedMotion() ? 0 : HATCH_REVEAL_MS;
	window.setTimeout(() => {
		state.revealing = false;
	}, duration);
}

async function finalizeCandidateResult(
	state: HatchFlowState,
	deps: HatchFlowDeps,
	result: CandidateAction
): Promise<void> {
	if (result.candidate.reference_url) {
		await preloadImage(result.candidate.reference_url);
	}
	applyCandidateAction(state, result);
	triggerHatchReveal(state, deps);
}

export function createHatchFlowActions(state: HatchFlowState, deps: HatchFlowDeps) {
	return {
		async generate(blockers: HatchFlowBlockers): Promise<void> {
			if (!canGenerate(state, blockers, deps.providers.selectedIds.length)) {
				if (deps.providers.selectedIds.length === 0) {
					deps.showToast('Connect at least one vibe source before you hatch.', 'amber');
				}
				return;
			}

			state.generating = true;
			state.actionHint = null;
			state.candidateHint = null;
			const stopBeats = startHatchBeats(state);
			try {
				const result = await runHatchSuspense(
					() =>
						generateCandidate({
							providers: deps.providers.selectedIds,
							latitude: deps.providers.coordinates?.latitude,
							longitude: deps.providers.coordinates?.longitude,
							bypassCredits: deps.bypassCredits()
						}),
					(line) => {
						state.generatingLine = line;
					}
				);
				await finalizeCandidateResult(state, deps, result);
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Could not hatch a Vibemon.';
				deps.showToast(message, 'brick');
			} finally {
				stopBeats();
				state.generating = false;
				state.generatingLine = '';
			}
		},

		async reject(blockers: HatchFlowBlockers): Promise<void> {
			const candidate = state.candidate;
			if (!candidate || !canReject(state, blockers)) return;
			state.busy = true;
			state.candidateHint = null;
			try {
				await rejectCandidate(candidate.id);
				clearHatchCandidate(state);
				deps.onClearScene();
				deps.showToast('Released to the Wild.', 'amber');
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Could not release this Vibemon.';
				deps.showToast(message, 'brick');
			} finally {
				state.busy = false;
			}
		},

		async refresh(blockers: HatchFlowBlockers): Promise<void> {
			const candidate = state.candidate;
			if (!candidate || !canRefresh(state, blockers)) return;
			state.busy = true;
			state.generatingLine = '';
			state.actionHint = null;
			state.candidateHint = null;
			state.spriteVisible = false;
			const stopBeats = startHatchBeats(state);
			try {
				const result = await runHatchSuspense(
					() => refreshCandidate(candidate.id),
					(line) => {
						state.generatingLine = line;
					},
					[HATCH_REFRESH_LINE]
				);
				await finalizeCandidateResult(state, deps, result);
			} catch (error) {
				state.spriteVisible = true;
				const message = error instanceof Error ? error.message : 'Could not refresh this Vibemon.';
				deps.showToast(message, 'brick');
			} finally {
				stopBeats();
				state.busy = false;
				state.generatingLine = '';
			}
		},

		openAdoptModal(blockers: HatchFlowBlockers): void {
			if (!canAdopt(state, blockers)) return;
			state.adoptModalOpen = true;
		},

		async confirmAdopt(nickname: string | null): Promise<void> {
			const candidate = state.candidate;
			if (!candidate) {
				state.adoptModalOpen = false;
				return;
			}
			state.busy = true;
			state.candidateHint = null;
			try {
				const result = await adoptCandidate(candidate.id, nickname);
				state.crewCount = result.crew_count;
				clearHatchCandidate(state);
				deps.onClearScene();
				state.adoptModalOpen = false;
				deps.showToast('Welcome to the crew — good vibes.', 'sage');
				await deps.goto('/deck/crew');
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Could not adopt this Vibemon.';
				deps.showToast(message, 'brick');
			} finally {
				state.busy = false;
			}
		}
	};
}

export type HatchFlowActions = ReturnType<typeof createHatchFlowActions>;
