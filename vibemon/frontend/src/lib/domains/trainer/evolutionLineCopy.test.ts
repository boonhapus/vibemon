import { describe, expect, it } from 'vitest';

import { evolutionLineHint } from '$lib/domains/trainer/evolutionLineCopy';

describe('evolutionLineHint', () => {
	it('describes deep-line rarity on a stage-1 three-stage line', () => {
		const hint = evolutionLineHint(
			{ form_index: 1, form_count: 3, line_rarity: 'deep' },
			'Lunilmi',
			10
		);

		expect(hint).toBe(
			'Lunilmi is at stage 1. Two more evolutions ahead. A deep evolution line. Rarer and stronger than most three-stage paths.'
		);
		expect(hint).not.toContain('—');
		expect(hint).not.toContain('✦');
	});

	it('leaves normal three-stage lines unchanged', () => {
		const hint = evolutionLineHint(
			{ form_index: 1, form_count: 3, line_rarity: 'normal' },
			'Sproutling',
			3
		);

		expect(hint).toBe('Sproutling is at stage 1. Two more evolutions ahead.');
	});
});
