import { describe, expect, it } from 'vitest';

import {
	assessAdoptEligibility,
	MAX_CREW_SIZE,
	type CandidateAction,
	type HatchCandidate
} from './hatchApi';

function candidateAction(overrides: Partial<HatchCandidate> = {}, crewCount = 0): CandidateAction {
	return {
		crew_count: crewCount,
		candidate: {
			id: 'candidate-1',
			name: 'Testling',
			nickname: null,
			elements: ['climate'],
			base_stats: {
				hp: 50,
				attack: 50,
				defense: 50,
				sp_attack: 50,
				sp_defense: 50,
				speed: 50,
				total: 300
			},
			bst: 300,
			power_pips: 3,
			is_radiant: false,
			evo_seed: 1,
			evolution_line: { form_index: 1, form_count: 1, line_rarity: 'normal' },
			moves: [],
			display: { anchor_x: null, baseline_y: null, size_factor: 0.7 },
			lifecycle: 'christened',
			reference_url: null,
			reference_facing: 'left',
			providers: ['climate'],
			candidate_review: {
				id: 'review-1',
				trainer_id: 'trainer-1',
				status: 'pending',
				shown_at: '2026-06-16T12:00:00.000Z',
				timeout_at: '2099-06-16T13:00:00.000Z',
				resolved_at: null,
				resolution: null,
				status_label: 'Pending',
				resolved_label: null
			},
			...overrides
		}
	};
}

describe('assessAdoptEligibility', () => {
	it('allows adoption for a pending review with crew room', () => {
		const current = candidateAction({}, 2);
		expect(assessAdoptEligibility(current, 'candidate-1')).toEqual({
			eligible: true,
			current,
			needs_swap: false
		});
	});

	it('requires a swap when the crew is full', () => {
		const current = candidateAction({}, MAX_CREW_SIZE);
		const result = assessAdoptEligibility(current, 'candidate-1');
		expect(result).toEqual({
			eligible: true,
			current,
			needs_swap: true
		});
	});

	it('blocks adoption when the review has timed out', () => {
		const current = candidateAction({
			candidate_review: {
				id: 'review-1',
				trainer_id: 'trainer-1',
				status: 'pending',
				shown_at: '2026-06-16T10:00:00.000Z',
				timeout_at: '2026-06-16T10:01:00.000Z',
				resolved_at: null,
				resolution: null,
				status_label: 'Pending',
				resolved_label: null
			}
		});
		const result = assessAdoptEligibility(current, 'candidate-1');
		expect(result.eligible).toBe(false);
		if (!result.eligible) {
			expect(result.message).toMatch(/timed out/i);
		}
	});

	it('blocks adoption when there is no pending candidate', () => {
		const result = assessAdoptEligibility(null, 'candidate-1');
		expect(result.eligible).toBe(false);
		if (!result.eligible) {
			expect(result.current).toBeNull();
		}
	});
});
