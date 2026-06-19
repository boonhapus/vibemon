import { describe, expect, it } from 'vitest';

import { moveReadHint } from './moveReadHint';

describe('moveReadHint', () => {
	it('joins flavor text and combat hints', () => {
		expect(
			moveReadHint({
				flavor_text: 'A leafy smack.',
				combat_hints: ['Never misses.']
			})
		).toBe('A leafy smack. Never misses.');
	});

	it('falls back when no copy is available', () => {
		expect(moveReadHint({ flavor_text: '', combat_hints: [] })).toBe(
			'No lore recorded for this move yet.'
		);
	});
});
