import { describe, expect, it } from 'vitest';

import { parseSolarPhase, resolveSolarPhase } from './solarPhase';

describe('parseSolarPhase', () => {
	it('accepts known phases case-insensitively', () => {
		expect(parseSolarPhase('NIGHT')).toBe('night');
		expect(parseSolarPhase(' Dawn ')).toBe('dawn');
	});

	it('rejects unknown values', () => {
		expect(parseSolarPhase('noon')).toBeNull();
		expect(parseSolarPhase('')).toBeNull();
	});
});

describe('resolveSolarPhase', () => {
	it('defaults to dawn without coordinates', () => {
		expect(resolveSolarPhase(null)).toBe('dawn');
	});

	it('returns day at equatorial noon UTC', () => {
		const at = new Date('2026-06-21T12:00:00.000Z');
		expect(resolveSolarPhase({ latitude: 0, longitude: 0 }, at)).toBe('day');
	});

	it('returns night at high-latitude winter midnight UTC', () => {
		const at = new Date('2026-12-21T00:00:00.000Z');
		expect(resolveSolarPhase({ latitude: 72, longitude: 0 }, at)).toBe('night');
	});
});
