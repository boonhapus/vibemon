export function applyTrainerReferenceUrl(ui: TrainerOnboardingUi, referenceUrl: string) {
	clearPendingReferencePreview(ui);
	ui.referenceSpriteSrc = referenceUrl;
}

export function isTrainerReferenceAssetUrl(url: string): boolean {
	return url.startsWith('/api/assets/trainers/');
}

export function isUsableRestoredReferenceSrc(url: string): boolean {
	return isTrainerReferenceAssetUrl(url) && !url.startsWith('blob:');
}

export function resolveTrainerReferenceUrl(
	session: { reference_url: string | null } | null,
	currentSrc: string,
	restoredSrc?: string | null
): string {
	if (session?.reference_url) return session.reference_url;
	const candidates = [restoredSrc, currentSrc];
	for (const candidate of candidates) {
		if (candidate && isUsableRestoredReferenceSrc(candidate)) return candidate;
	}
	return DEFAULT_TRAINER_REFERENCE_SPRITE;
}

/** View-only onboarding chrome; hatch orchestration lives in hatchSession.ts. */
export type TrainerOnboardingUi = {
	referenceHintVisible: boolean;
	referenceSpriteSrc: string;
	/** False until the trainer reference is resolved and preloaded (hatch scene). */
	referenceSpriteReady: boolean;
	registrationUsername: string;
	pendingReferenceFile: File | null;
	referencePreviewUrl: string | null;
	referenceGenerating: boolean;
	setupInProgress: boolean;
};

export function createTrainerOnboardingUi(): TrainerOnboardingUi {
	return {
		referenceHintVisible: false,
		referenceSpriteSrc: DEFAULT_TRAINER_REFERENCE_SPRITE,
		referenceSpriteReady: false,
		registrationUsername: '',
		pendingReferenceFile: null,
		referencePreviewUrl: null,
		referenceGenerating: false,
		setupInProgress: false
	};
}

export function setPendingReferencePreview(ui: TrainerOnboardingUi, file: File, previewUrl?: string) {
	if (ui.referencePreviewUrl?.startsWith('blob:')) {
		URL.revokeObjectURL(ui.referencePreviewUrl);
	}
	ui.pendingReferenceFile = file;
	ui.referencePreviewUrl = previewUrl ?? URL.createObjectURL(file);
	ui.referenceSpriteSrc = ui.referencePreviewUrl;
}

export function clearPendingReferencePreview(ui: TrainerOnboardingUi) {
	if (ui.referencePreviewUrl?.startsWith('blob:')) {
		URL.revokeObjectURL(ui.referencePreviewUrl);
	}
	ui.pendingReferenceFile = null;
	ui.referencePreviewUrl = null;
}

export const DEFAULT_TRAINER_REFERENCE_SPRITE = '/game/sprites/trainer@128.png';
