import { describe, expect, it } from 'vitest';

import { impactStrength, impactTier } from './battleImpact';

describe('impactTier', () => {
	it('classifies effectiveness into visual tiers', () => {
		expect(impactTier(0)).toBe('immune');
		expect(impactTier(0.5)).toBe('resisted');
		expect(impactTier(1)).toBe('neutral');
		expect(impactTier(2)).toBe('super');
		expect(impactTier(4)).toBe('super');
	});
});

describe('impactStrength', () => {
	it('grows with effectiveness', () => {
		expect(impactStrength(0)).toBe(0);
		expect(impactStrength(0.5)).toBeLessThan(impactStrength(1));
		expect(impactStrength(1)).toBeLessThan(impactStrength(2));
	});

	it('lifts non-immune hits on a crit but stays bounded', () => {
		expect(impactStrength(1, true)).toBeGreaterThan(impactStrength(1, false));
		expect(impactStrength(2, true)).toBeLessThanOrEqual(1.3);
		// Immune hits never shake, even on a (theoretical) crit.
		expect(impactStrength(0, true)).toBe(0);
	});
});
