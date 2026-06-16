import { describe, expect, it } from 'vitest';

import { buildCrewStoryEntries } from './crewTimeline';

describe('buildCrewStoryEntries', () => {
	it('lists birth providers without invented dates', () => {
		const entries = buildCrewStoryEntries({
			id: '0192e2f4-7b2a-7000-8000-000000000001',
			name: 'Fesali',
			nickname: null,
			elements: ['fire'],
			base_stats: {
				hp: 1,
				attack: 1,
				defense: 1,
				sp_attack: 1,
				sp_defense: 1,
				speed: 1,
				total: 6
			},
			bst: 6,
			power_pips: 2,
			is_radiant: false,
			evo_seed: 1,
			evolution_line: { form_index: 1, form_count: 2, line_rarity: 'normal' },
			moves: [],
			display: { anchor_x: null, baseline_y: null, size_factor: 0.7 },
			lifecycle: 'owned',
			reference_url: null,
			reference_facing: 'left',
			providers: ['music', 'climate']
		});

		expect(entries).toHaveLength(2);
		expect(entries[0]).toMatchObject({
			id: 'birth',
			title: 'Hatched',
			body: 'Shaped by MUSIC and SKY.'
		});
		expect(entries[1]).toMatchObject({
			id: 'adoption',
			title: 'Joined your crew'
		});
		expect(entries.every((entry) => !('when' in entry))).toBe(true);
	});
});
