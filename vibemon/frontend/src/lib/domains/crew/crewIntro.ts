/** Assembly intro choreography for the crew formation ring. */

export type IntroRitual = 'full' | 'short' | 'none';
export type IntroStage = 'pending' | 'trainer' | 'assemble' | 'spin' | 'done';

const TRAINER_BEAT_MS = 320;
const HOP_MS = 150;

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
	if (signal?.aborted) return Promise.reject(new DOMException('Aborted', 'AbortError'));
	return new Promise((resolve, reject) => {
		const timer = setTimeout(resolve, ms);
		signal?.addEventListener(
			'abort',
			() => {
				clearTimeout(timer);
				reject(new DOMException('Aborted', 'AbortError'));
			},
			{ once: true }
		);
	});
}

export async function runCrewIntro(options: {
	ritual: IntroRitual;
	filledSlots: readonly number[];
	prefersReducedMotion?: boolean;
	signal?: AbortSignal;
	onStage?: (stage: IntroStage) => void;
	onLandSlot?: (crewSlot: number) => void;
	onSpin?: (slotCount: number, durationMs: number) => Promise<void>;
}): Promise<IntroStage> {
	const {
		ritual,
		filledSlots,
		prefersReducedMotion = false,
		signal,
		onStage,
		onLandSlot,
		onSpin
	} = options;

	const setStage = (stage: IntroStage) => {
		onStage?.(stage);
	};

	if (ritual === 'none' || filledSlots.length === 0 || prefersReducedMotion) {
		setStage('done');
		return 'done';
	}

	setStage('trainer');
	await sleep(TRAINER_BEAT_MS, signal);
	setStage('assemble');

	for (const crewSlot of filledSlots) {
		onLandSlot?.(crewSlot);
		await sleep(HOP_MS, signal);
	}

	if (ritual === 'full') {
		setStage('spin');
		await onSpin?.(6, prefersReducedMotion ? 0 : 450 * 6);
	}

	setStage('done');
	return 'done';
}
