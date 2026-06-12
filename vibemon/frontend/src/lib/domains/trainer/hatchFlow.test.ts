import { describe, expect, it } from 'vitest';

import {
	canAdopt,
	canGenerate,
	canReject,
	createHatchFlowState,
	hatchControlsBlocked,
	hatchPhase,
	releaseDisabled
} from './hatchFlow';
import { createProviderSelectionState } from './providerSelection';

const blockers = { settingsOpen: false, providerModalOpen: false };

describe('hatchFlow guards', () => {
	it('blocks generate while a candidate is on screen', () => {
		const state = createHatchFlowState({ candidate: { id: '1' } as never });
		expect(canGenerate(state, blockers, 1)).toBe(false);
	});

	it('blocks generate without connected providers', () => {
		const state = createHatchFlowState();
		expect(canGenerate(state, blockers, 0)).toBe(false);
	});

	it('blocks reject for the first crew slot policy', () => {
		const state = createHatchFlowState({
			candidate: { id: '1' } as never,
			crewCount: 0
		});
		expect(releaseDisabled(state)).toBe(true);
		expect(canReject(state, blockers)).toBe(false);
	});

	it('blocks adopt while generating', () => {
		const state = createHatchFlowState({
			candidate: { id: '1' } as never,
			generating: true
		});
		expect(canAdopt(state, blockers)).toBe(false);
		expect(hatchPhase(state)).toBe('generating');
	});

	it('treats modal chrome as a control blocker', () => {
		const state = createHatchFlowState({ adoptModalOpen: true });
		expect(hatchControlsBlocked(state, blockers)).toBe(true);
	});
});

describe('providerSelection', () => {
	it('tracks warmed and selected providers independently', () => {
		const selection = createProviderSelectionState();
		selection.selectedIds = ['climate'];
		selection.warmedIds = ['climate'];
		expect(selection.selectedIds).toEqual(['climate']);
		expect(selection.warmedIds).toEqual(['climate']);
	});
});
