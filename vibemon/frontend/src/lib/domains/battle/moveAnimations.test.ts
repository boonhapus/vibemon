import { describe, expect, it } from 'vitest';

import type { BattleMove } from './battleApi';
import { moveAnimationKind } from './MoveAnimator';
import { MOVE_ANIMATION_OVERRIDES } from './moveAnimations';

const baseMove: BattleMove = {
	id: 'climate.tap',
	name: 'Tap',
	type: 'normal',
	category: 'physical',
	power: 40,
	accuracy: 1,
	pp_current: 20,
	pp_max: 20,
	effectiveness: 1,
	flavor_text: ''
};

describe('moveAnimationKind', () => {
	it('maps move categories to default animation profiles', () => {
		expect(moveAnimationKind(baseMove)).toBe('physical');
		expect(moveAnimationKind({ ...baseMove, category: 'special' })).toBe('special');
		expect(moveAnimationKind({ ...baseMove, category: 'status' })).toBe('status');
	});

	it('uses override registry entries keyed by move id', () => {
		MOVE_ANIMATION_OVERRIDES['climate.tap'] = 'special';
		try {
			expect(moveAnimationKind(baseMove)).toBe('special');
		} finally {
			delete MOVE_ANIMATION_OVERRIDES['climate.tap'];
		}
	});
});
