import { browser } from '$app/environment';

import type { HatchCandidate } from './hatchApi';
import { fetchCurrentCandidate } from './hatchApi';
import { applyCandidateAction, type HatchFlowState } from './hatchFlow';
import { preloadImage } from './hatchSuspense';
import { applyCandidateProviderIds, type ProviderSelectionState } from './providerSelection';
import { resolveTrainerSession } from './trainerApi';
import {
	applyTrainerReferenceUrl,
	DEFAULT_TRAINER_REFERENCE_SPRITE,
	resolveTrainerReferenceUrl,
	type TrainerOnboardingUi
} from './trainerOnboardingUi';

const STORAGE_KEY = 'vibemon.hatchScene';

type HatchSceneSnapshot = {
	referenceSpriteSrc: string;
	hatchCandidate: HatchCandidate | null;
	hatchSpriteVisible: boolean;
	selectedProviderIds: string[];
};

function readSnapshot(): HatchSceneSnapshot | null {
	if (!browser) return null;
	const raw = sessionStorage.getItem(STORAGE_KEY);
	if (!raw) return null;
	try {
		return JSON.parse(raw) as HatchSceneSnapshot;
	} catch {
		return null;
	}
}

/** Read a persisted trainer reference URL from sessionStorage (client only). */
export function readRestoredReferenceSpriteSrc(): string | null {
	return readSnapshot()?.referenceSpriteSrc ?? null;
}

/** Restore the last hatch scene snapshot on the client before hatch bootstrap runs. */
export function restoreHatchSceneState(
	ui: TrainerOnboardingUi,
	hatch: HatchFlowState,
	providers: ProviderSelectionState
): void {
	const snapshot = readSnapshot();
	if (!snapshot) return;
	ui.referenceSpriteSrc = snapshot.referenceSpriteSrc;
	hatch.candidate = snapshot.hatchCandidate;
	hatch.spriteVisible = snapshot.hatchSpriteVisible;
	providers.selectedIds = [...snapshot.selectedProviderIds];
}

export function persistHatchSceneState(
	ui: TrainerOnboardingUi,
	hatch: HatchFlowState,
	providers: ProviderSelectionState
): void {
	if (!browser) return;
	const snapshot: HatchSceneSnapshot = {
		referenceSpriteSrc: ui.referenceSpriteSrc,
		hatchCandidate: hatch.candidate,
		hatchSpriteVisible: hatch.spriteVisible,
		selectedProviderIds: [...providers.selectedIds]
	};
	sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
}

export function clearHatchSceneState(): void {
	if (!browser) return;
	sessionStorage.removeItem(STORAGE_KEY);
}

let hatchBootstrapKey: string | null = null;
let hatchBootstrapPromise: Promise<boolean> | null = null;

export function clearHatchBootstrapCache(): void {
	hatchBootstrapKey = null;
	hatchBootstrapPromise = null;
}

/** Deduplicate hatch bootstrap across layout effects and embedded configuration scene. */
export function bootstrapHatchSceneOnce(
	ui: TrainerOnboardingUi,
	hatch: HatchFlowState,
	providers: ProviderSelectionState,
	username: string
): Promise<boolean> {
	const key = username.trim().toLowerCase();
	if (hatchBootstrapKey === key && hatchBootstrapPromise) {
		return hatchBootstrapPromise;
	}
	hatchBootstrapKey = key;
	hatchBootstrapPromise = bootstrapHatchScene(ui, hatch, providers, username);
	return hatchBootstrapPromise;
}

async function hydrateTrainerReferenceSprite(ui: TrainerOnboardingUi, url: string): Promise<void> {
	try {
		await preloadImage(url);
	} catch {
		// Preload is best-effort — still apply so the <img> can load normally.
	}
	applyTrainerReferenceUrl(ui, url);
}

/** Establish session then hydrate trainer reference and any in-progress candidate review. */
export async function bootstrapHatchScene(
	ui: TrainerOnboardingUi,
	hatch: HatchFlowState,
	providers: ProviderSelectionState,
	username: string
): Promise<boolean> {
	try {
		const session = await resolveTrainerSession(username);
		if (!session) {
			await hydrateTrainerReferenceSprite(ui, DEFAULT_TRAINER_REFERENCE_SPRITE);
			return false;
		}

		const referenceUrl = resolveTrainerReferenceUrl(
			session,
			ui.referenceSpriteSrc,
			readRestoredReferenceSpriteSrc()
		);
		await hydrateTrainerReferenceSprite(ui, referenceUrl);
		hatch.crewCount = session.crew_count;

		try {
			const current = await fetchCurrentCandidate();
			if (current) {
				applyCandidateAction(hatch, current);
				if (current.candidate.providers?.length) {
					applyCandidateProviderIds(providers, current.candidate.providers);
				}
				hatch.spriteVisible = true;
				persistHatchSceneState(ui, hatch, providers);
			}
		} catch {
			// Best-effort restore of an in-progress review.
		}
		return true;
	} finally {
		ui.referenceSpriteReady = true;
	}
}
