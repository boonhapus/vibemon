import { describe, expect, it } from 'vitest';

import type { HatchCandidate } from '$lib/domains/trainer/hatchApi';
import { computeHatchDisplaySizeFactor } from '$lib/domains/trainer/hatchDisplaySize';

function candidate(overrides: Partial<HatchCandidate> = {}): HatchCandidate {
	return {
		id: '0192e2f4-7b2a-7000-8000-000000000001',
		name: 'Sproutling',
		nickname: null,
		elements: ['grass'],
		base_stats: {
			hp: 45,
			attack: 49,
			defense: 49,
			sp_attack: 65,
			sp_defense: 65,
			speed: 45,
			total: 318
		},
		bst: 318,
		power_pips: 2,
		is_radiant: false,
		evo_seed: 1,
		evolution_line: { form_index: 1, form_count: 1, line_rarity: 'normal' },
		moves: [],
		display: { anchor_x: null, baseline_y: null, size_factor: 0.7 },
		lifecycle: 'christened',
		reference_url: null,
		reference_facing: 'left',
		providers: [],
		...overrides
	};
}

describe('computeHatchDisplaySizeFactor', () => {
	it('rewards single-stage high BST mons over runty three-stage hatchlings', () => {
		const beefy = candidate({
			bst: 483,
			power_pips: 2,
			evolution_line: { form_index: 1, form_count: 1, line_rarity: 'normal' }
		});
		const runty = candidate({
			bst: 245,
			power_pips: 1,
			evolution_line: { form_index: 1, form_count: 3, line_rarity: 'normal' }
		});

		expect(computeHatchDisplaySizeFactor(beefy)).toBeGreaterThan(
			computeHatchDisplaySizeFactor(runty)
		);
	});

	it('grows mons as they advance through their evolution line', () => {
		const baseForm = candidate({
			evolution_line: { form_index: 1, form_count: 3, line_rarity: 'normal' }
		});
		const finalForm = candidate({
			evolution_line: { form_index: 3, form_count: 3, line_rarity: 'normal' }
		});

		expect(computeHatchDisplaySizeFactor(finalForm)).toBeGreaterThan(
			computeHatchDisplaySizeFactor(baseForm)
		);
	});
});
