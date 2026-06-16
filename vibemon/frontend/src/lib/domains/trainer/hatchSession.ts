/** Deep Hatch session: Candidate Review state, provider opt-in, persistence, and bootstrap. */

import type { CandidateAction, CrewMember, HatchCandidate } from './hatchApi';
import {
	adoptCandidate,
	fetchAdoptEligibility,
	fetchCrew,
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
import {
	applyCandidateProviderIds,
	createProviderSelectionState,
	type ProviderSelectionState
} from './providerSelection';
import { resolveTrainerSession } from './trainerApi';
import {
	DEFAULT_TRAINER_REFERENCE_SPRITE,
	resolveTrainerReferenceUrl
} from './trainerOnboardingUi';

export const HATCH_SESSION_KEY = 'trainer-hatch-session';
export const HATCH_REVEAL_MS = 720;

const STORAGE_KEY = 'vibemon.hatchSession';

export type HatchPhase = 'idle' | 'generating' | 'revealing' | 'reviewing' | 'busy';
export type HatchActionHint = 'refresh' | 'adopt' | 'release';

export type HatchSessionState = {
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
	adoptSwapMembers: CrewMember[] | null;
	adoptReleaseTargetId: string | null;
	providers: ProviderSelectionState;
	referenceSpriteSrc: string;
	referenceSpriteReady: boolean;
};

export type HatchSessionBlockers = {
	settingsOpen: boolean;
	providerModalOpen: boolean;
};

export type HatchSessionDeps = {
	bypassCredits: () => boolean;
	showToast: (message: string, tone: 'amber' | 'brick' | 'sage') => void;
	goto: (path: string) => void | Promise<void>;
	prefersReducedMotion: () => boolean;
};

type HatchSessionSnapshot = {
	referenceSpriteSrc: string;
	hatchCandidate: HatchCandidate | null;
	hatchSpriteVisible: boolean;
	selectedProviderIds: string[];
};

export function createHatchSession(initial?: Partial<HatchSessionState>): HatchSessionState {
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
		adoptModalOpen: initial?.adoptModalOpen ?? false,
		adoptSwapMembers: initial?.adoptSwapMembers ?? null,
		adoptReleaseTargetId: initial?.adoptReleaseTargetId ?? null,
		providers: createProviderSelectionState(initial?.providers),
		referenceSpriteSrc: initial?.referenceSpriteSrc ?? DEFAULT_TRAINER_REFERENCE_SPRITE,
		referenceSpriteReady: initial?.referenceSpriteReady ?? false
	};
}

export function hatchPhase(state: HatchSessionState): HatchPhase {
	if (state.generating) return 'generating';
	if (state.revealing) return 'revealing';
	if (state.busy) return 'busy';
	if (state.candidate) return 'reviewing';
	return 'idle';
}

export function hatchControlsBlocked(state: HatchSessionState, blockers: HatchSessionBlockers): boolean {
	return (
		blockers.settingsOpen ||
		blockers.providerModalOpen ||
		state.adoptModalOpen ||
		state.generating ||
		state.busy
	);
}

export function releaseDisabled(state: HatchSessionState): boolean {
	return state.crewCount === 0;
}

export function canGenerate(
	state: HatchSessionState,
	blockers: HatchSessionBlockers
): boolean {
	return (
		!hatchControlsBlocked(state, blockers) &&
		!state.candidate &&
		state.providers.selectedIds.length > 0
	);
}

export function canReject(state: HatchSessionState, blockers: HatchSessionBlockers): boolean {
	return Boolean(state.candidate) && !releaseDisabled(state) && !hatchControlsBlocked(state, blockers);
}

export function canRefresh(state: HatchSessionState, blockers: HatchSessionBlockers): boolean {
	return Boolean(state.candidate) && !hatchControlsBlocked(state, blockers);
}

export function canAdopt(state: HatchSessionState, blockers: HatchSessionBlockers): boolean {
	return Boolean(state.candidate) && !hatchControlsBlocked(state, blockers);
}

export function clearAdoptModalState(state: HatchSessionState): void {
	state.adoptModalOpen = false;
	state.adoptSwapMembers = null;
	state.adoptReleaseTargetId = null;
}

export function applyCandidateAction(state: HatchSessionState, action: CandidateAction | null): void {
	if (!action) {
		state.candidate = null;
		return;
	}
	state.candidate = action.candidate;
	state.crewCount = action.crew_count;
}

export function clearHatchCandidate(state: HatchSessionState): void {
	state.candidate = null;
	state.spriteVisible = false;
	state.actionHint = null;
	state.candidateHint = null;
}

function isBrowser(): boolean {
	return typeof window !== 'undefined';
}

function readSnapshot(): HatchSessionSnapshot | null {
	if (!isBrowser()) return null;
	const raw = sessionStorage.getItem(STORAGE_KEY);
	if (!raw) return null;
	try {
		return JSON.parse(raw) as HatchSessionSnapshot;
	} catch {
		return null;
	}
}

function readRestoredReferenceSpriteSrc(): string | null {
	return readSnapshot()?.referenceSpriteSrc ?? null;
}

export function restoreHatchSession(state: HatchSessionState): void {
	const snapshot = readSnapshot();
	if (!snapshot) return;
	state.referenceSpriteSrc = snapshot.referenceSpriteSrc;
	state.candidate = snapshot.hatchCandidate;
	state.spriteVisible = snapshot.hatchSpriteVisible;
	state.providers.selectedIds = [...snapshot.selectedProviderIds];
}

export function persistHatchSession(state: HatchSessionState): void {
	if (!isBrowser()) return;
	const snapshot: HatchSessionSnapshot = {
		referenceSpriteSrc: state.referenceSpriteSrc,
		hatchCandidate: state.candidate,
		hatchSpriteVisible: state.spriteVisible,
		selectedProviderIds: [...state.providers.selectedIds]
	};
	sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
}

export function clearHatchSessionState(): void {
	if (!isBrowser()) return;
	sessionStorage.removeItem(STORAGE_KEY);
}

let hatchBootstrapKey: string | null = null;
let hatchBootstrapPromise: Promise<boolean> | null = null;
let hatchBootstrapState: HatchSessionState | null = null;

export function clearHatchBootstrapCache(): void {
	hatchBootstrapKey = null;
	hatchBootstrapPromise = null;
	hatchBootstrapState = null;
}

export function bootstrapHatchSessionOnce(state: HatchSessionState, username: string): Promise<boolean> {
	const key = username.trim().toLowerCase();
	// Reuse only when the same live session object is bootstrapping. After hatch → deck/crew
	// the onboarding layout remounts with a fresh session; a username-only cache would return
	// an already-settled promise and leave referenceSpriteReady false on the new session.
	if (hatchBootstrapKey === key && hatchBootstrapPromise && hatchBootstrapState === state) {
		return hatchBootstrapPromise;
	}
	hatchBootstrapKey = key;
	hatchBootstrapState = state;
	hatchBootstrapPromise = bootstrapHatchSession(state, username);
	return hatchBootstrapPromise;
}

async function hydrateTrainerReferenceSprite(state: HatchSessionState, url: string): Promise<void> {
	try {
		await preloadImage(url);
	} catch {
		// Preload is best-effort — still apply so the <img> can load normally.
	}
	state.referenceSpriteSrc = url;
}

export async function bootstrapHatchSession(
	state: HatchSessionState,
	username: string
): Promise<boolean> {
	try {
		const session = await resolveTrainerSession(username);
		if (!session) {
			await hydrateTrainerReferenceSprite(state, DEFAULT_TRAINER_REFERENCE_SPRITE);
			return false;
		}

		const referenceUrl = resolveTrainerReferenceUrl(
			session,
			state.referenceSpriteSrc,
			readRestoredReferenceSpriteSrc()
		);
		await hydrateTrainerReferenceSprite(state, referenceUrl);
		state.crewCount = session.crew_count;

		try {
			const current = await fetchCurrentCandidate();
			if (current) {
				applyCandidateAction(state, current);
				if (current.candidate.providers?.length) {
					applyCandidateProviderIds(state.providers, current.candidate.providers);
				}
				state.spriteVisible = true;
				persistHatchSession(state);
			}
		} catch {
			// Best-effort restore of an in-progress review.
		}
		return true;
	} finally {
		state.referenceSpriteReady = true;
	}
}

function startHatchBeats(state: HatchSessionState): () => void {
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

function triggerHatchReveal(state: HatchSessionState, deps: HatchSessionDeps): void {
	state.spriteVisible = true;
	persistHatchSession(state);
	state.revealing = true;
	const duration = deps.prefersReducedMotion() ? 0 : HATCH_REVEAL_MS;
	window.setTimeout(() => {
		state.revealing = false;
	}, duration);
}

async function finalizeCandidateResult(
	state: HatchSessionState,
	deps: HatchSessionDeps,
	result: CandidateAction
): Promise<void> {
	if (result.candidate.reference_url) {
		await preloadImage(result.candidate.reference_url);
	}
	applyCandidateAction(state, result);
	triggerHatchReveal(state, deps);
}

export function createHatchSessionActions(state: HatchSessionState, deps: HatchSessionDeps) {
	return {
		async generate(blockers: HatchSessionBlockers): Promise<void> {
			if (!canGenerate(state, blockers)) {
				if (state.providers.selectedIds.length === 0) {
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
							providers: state.providers.selectedIds,
							latitude: state.providers.coordinates?.latitude,
							longitude: state.providers.coordinates?.longitude,
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

		async reject(blockers: HatchSessionBlockers): Promise<void> {
			const candidate = state.candidate;
			if (!candidate || !canReject(state, blockers)) return;
			state.busy = true;
			state.candidateHint = null;
			try {
				await rejectCandidate(candidate.id);
				clearHatchCandidate(state);
				clearHatchSessionState();
				deps.showToast('Released to the Wild.', 'amber');
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Could not release this Vibemon.';
				deps.showToast(message, 'brick');
			} finally {
				state.busy = false;
			}
		},

		async refresh(blockers: HatchSessionBlockers): Promise<void> {
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

		async openAdoptModal(blockers: HatchSessionBlockers): Promise<void> {
			const candidate = state.candidate;
			if (!candidate || !canAdopt(state, blockers)) return;

			state.busy = true;
			state.candidateHint = null;
			try {
				const eligibility = await fetchAdoptEligibility(candidate.id);
				if (!eligibility.eligible) {
					if (eligibility.current) {
						applyCandidateAction(state, eligibility.current);
						persistHatchSession(state);
					} else {
						clearHatchCandidate(state);
						clearHatchSessionState();
					}
					deps.showToast(eligibility.message, 'brick');
					return;
				}
				if (eligibility.needs_swap) {
					const crew = await fetchCrew();
					state.adoptSwapMembers = crew.members;
					state.adoptReleaseTargetId = null;
				} else {
					state.adoptSwapMembers = null;
					state.adoptReleaseTargetId = null;
				}
				applyCandidateAction(state, eligibility.current);
				state.adoptModalOpen = true;
			} catch (error) {
				const message =
					error instanceof Error ? error.message : 'Could not verify adoption eligibility.';
				deps.showToast(message, 'brick');
			} finally {
				state.busy = false;
			}
		},

		async confirmAdopt(nickname: string | null): Promise<void> {
			const candidate = state.candidate;
			if (!candidate) {
				clearAdoptModalState(state);
				return;
			}
			if (state.adoptSwapMembers && !state.adoptReleaseTargetId) return;
			state.busy = true;
			state.candidateHint = null;
			try {
				const result = await adoptCandidate(candidate.id, {
					nickname,
					releaseVibemonId: state.adoptReleaseTargetId
				});
				state.crewCount = result.crew_count;
				clearHatchCandidate(state);
				clearHatchSessionState();
				clearAdoptModalState(state);
				deps.showToast('Welcome to the crew — good vibes.', 'sage');
				await deps.goto('/deck/crew');
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Could not adopt this Vibemon.';
				deps.showToast(message, 'brick');
			} finally {
				state.busy = false;
			}
		},

		async applyReferenceUrl(url: string): Promise<void> {
			await hydrateTrainerReferenceSprite(state, url);
			persistHatchSession(state);
		}
	};
}

export type HatchSessionActions = ReturnType<typeof createHatchSessionActions>;
