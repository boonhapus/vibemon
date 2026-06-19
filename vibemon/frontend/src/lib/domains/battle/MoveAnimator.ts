import type { BattleMove } from './battleApi';
import { animationProfileForMove } from './moveAnimations';

export type MoveAnimationKind = 'physical' | 'special' | 'status';

export function moveAnimationKind(move: BattleMove): MoveAnimationKind {
	return animationProfileForMove(move);
}

export function moveAnimationDurationMs(kind: MoveAnimationKind): number {
	switch (kind) {
		case 'physical':
			return 600;
		case 'special':
			return 500;
		case 'status':
			return 450;
	}
}
