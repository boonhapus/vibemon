import { describe, expect, it } from 'vitest';

import {
	canAdopt,
	canGenerate,
	canReject,
	createHatchSession,
	hatchControlsBlocked,
	hatchPhase,
	releaseDisabled,
	type HatchSessionBlockers
} from './hatchSession';
import { createProviderSelectionState } from './providerSelection';

const blockers: HatchSessionBlockers = { settingsOpen: false, providerModalOpen: false };

describe('hatchSession guards', () => {
	it('blocks generate while a candidate is on screen', () => {
		const state = createHatchSession({
			candidate: { id: '1' } as never,
			providers: createProviderSelectionState({ selectedIds: ['music'] })
		});
		expect(canGenerate(state, blockers)).toBe(false);
	});

	it('blocks generate without connected providers', () => {
		const state = createHatchSession();
		expect(canGenerate(state, blockers)).toBe(false);
	});

	it('blocks reject for the first crew slot policy', () => {
		const state = createHatchSession({
			candidate: { id: '1' } as never,
			crewCount: 0
		});
		expect(releaseDisabled(state)).toBe(true);
		expect(canReject(state, blockers)).toBe(false);
	});

	it('blocks adopt while generating', () => {
		const state = createHatchSession({
			candidate: { id: '1' } as never,
			generating: true
		});
		expect(canAdopt(state, blockers)).toBe(false);
		expect(hatchPhase(state)).toBe('generating');
	});

	it('treats modal chrome as a control blocker', () => {
		const state = createHatchSession({ adoptModalOpen: true });
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
