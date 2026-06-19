import { describe, expect, it } from 'vitest';

import { formatStatDeltaLine } from './battleStatLabels';

describe('formatStatDeltaLine', () => {
	it('formats positive deltas with short labels', () => {
		expect(
			formatStatDeltaLine([
				{ stat: 'hp', previous: 40, new: 43, delta: 3 },
				{ stat: 'attack', previous: 12, new: 13, delta: 1 }
			])
		).toBe('HP +3  ATK +1');
	});
});
