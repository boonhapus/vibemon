import type { BattleMove } from './battleApi';

/** Optional per-move animation overrides keyed by move content id. */
export const MOVE_ANIMATION_OVERRIDES: Record<string, 'physical' | 'special' | 'status'> = {};

export function animationProfileForMove(move: BattleMove): 'physical' | 'special' | 'status' {
	return MOVE_ANIMATION_OVERRIDES[move.id] ?? move.category;
}
