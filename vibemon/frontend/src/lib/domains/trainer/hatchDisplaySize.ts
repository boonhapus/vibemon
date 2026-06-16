/** Trainer-relative sprite height for hatch and crew scenes. */

import type { HatchCandidate } from './hatchApi';

export const EMPTY_SLOT_HEIGHT_FACTOR = 0.5;

const SIZE_FACTOR_BASE = 0.36;
const SIZE_FACTOR_EVO_SPAN = 0.34;
const SIZE_FACTOR_BST_FLOOR = 260;
const SIZE_FACTOR_BST_CEILING = 620;
const SIZE_FACTOR_BST_SPAN = 0.3;
const SIZE_FACTOR_STR_SPAN = 0.14;
const SIZE_FACTOR_MIN = 0.36;
const SIZE_FACTOR_MAX = 1.32;

/** Mirror backend hatch_display_size_factor for stale payloads and tests. */
export function computeHatchDisplaySizeFactor(candidate: HatchCandidate): number {
	const line = candidate.evolution_line;
	const count = Math.max(line?.form_count ?? 1, 1);
	const index = Math.min(Math.max(line?.form_index ?? 1, 1), count);
	const evoProgress = index / count;

	const bstSpan = SIZE_FACTOR_BST_CEILING - SIZE_FACTOR_BST_FLOOR;
	const bstNorm =
		bstSpan > 0
			? Math.min(Math.max((candidate.bst - SIZE_FACTOR_BST_FLOOR) / bstSpan, 0), 1)
			: 0;

	const pips = Math.min(Math.max(candidate.power_pips ?? 2, 1), 3);
	const strProgress = (pips - 1) / 2;

	const factor =
		SIZE_FACTOR_BASE +
		evoProgress * SIZE_FACTOR_EVO_SPAN +
		bstNorm * SIZE_FACTOR_BST_SPAN +
		strProgress * SIZE_FACTOR_STR_SPAN;

	return Math.min(Math.max(factor, SIZE_FACTOR_MIN), SIZE_FACTOR_MAX);
}

export function trainerRelativeHeight(candidate: HatchCandidate | null): number {
	if (!candidate) return EMPTY_SLOT_HEIGHT_FACTOR;
	const factor = candidate.display?.size_factor;
	if (typeof factor === 'number' && factor > 0) return factor;
	return computeHatchDisplaySizeFactor(candidate);
}
