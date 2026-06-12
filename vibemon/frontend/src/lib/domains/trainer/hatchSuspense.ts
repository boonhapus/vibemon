/** Timed copy and helpers for the hatch generation suspense beat. */

export const HATCH_SUSPENSE_LINES = [
	'The glow pulses, just once...',
	'Your vibes are finding their shape...',
	'Something cozy begins to stir...',
	'Patterns are starting to land...',
	'A soft heartbeat flickers...',
	'The glow gets a touch warmer...',
	'Can you feel that?',
	'Static whispers, then stills...',
	'Almost there, Trainer...'
] as const;

export const HATCH_REFRESH_LINE = 'Redrawing from your vibes...';

export const HATCH_MIN_GENERATION_MS = 7000;
export const HATCH_LINE_BASE_MS = 6000;
export const HATCH_LINE_JITTER_MS = 1000;

/* Motion beats escalate alongside the copy: settle → stir → crack build. */
export const HATCH_BEAT_STIR_MS = 2500;
export const HATCH_BEAT_CRACK_MS = 5500;

export function randomHatchLineDelayMs(): number {
	const jitter = Math.floor(Math.random() * (HATCH_LINE_JITTER_MS * 2 + 1)) - HATCH_LINE_JITTER_MS;
	return HATCH_LINE_BASE_MS + jitter;
}

export function startHatchLineCycle(
	onLine: (line: string) => void,
	lines?: readonly string[]
): () => void {
	// Ordered, not shuffled: the copy escalates calm → urgent with the motion beats.
	const queue = [...(lines ?? HATCH_SUSPENSE_LINES)];
	let index = 0;
	let cancelled = false;
	let timer: ReturnType<typeof setTimeout> | number | undefined;

	const scheduleNext = () => {
		if (cancelled) return;
		timer = window.setTimeout(() => {
			if (cancelled) return;
			index += 1;
			onLine(queue[index % queue.length] ?? HATCH_SUSPENSE_LINES[0]);
			scheduleNext();
		}, randomHatchLineDelayMs());
	};

	onLine(queue[0] ?? HATCH_SUSPENSE_LINES[0]);
	scheduleNext();

	return () => {
		cancelled = true;
		if (timer !== undefined) window.clearTimeout(timer);
	};
}

export async function waitForHatchMinimum(startedAt: number): Promise<void> {
	const remaining = HATCH_MIN_GENERATION_MS - (Date.now() - startedAt);
	if (remaining <= 0) return;
	await new Promise<void>((resolve) => window.setTimeout(resolve, remaining));
}

/** Run an API task while cycling suspense lines for at least the minimum hatch duration. */
export async function runHatchSuspense<T>(
	runTask: () => Promise<T>,
	onLine: (line: string) => void,
	lines?: readonly string[]
): Promise<T> {
	const startedAt = Date.now();
	const stopLines = startHatchLineCycle(onLine, lines);
	try {
		const [result] = await Promise.all([runTask(), waitForHatchMinimum(startedAt)]);
		return result;
	} finally {
		stopLines();
	}
}

export function preloadImage(url: string): Promise<void> {
	return new Promise((resolve, reject) => {
		const image = new Image();
		image.onload = () => resolve();
		image.onerror = () => reject(new Error('Could not load Vibemon sprite.'));
		image.src = url;
	});
}
