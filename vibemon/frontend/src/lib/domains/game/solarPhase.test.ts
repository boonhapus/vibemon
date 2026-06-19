import SunCalc from 'suncalc';
import { describe, expect, it } from 'vitest';

import { parseSolarPhase, resolveSolarPhase } from './solarPhase';

const EQUATOR = { latitude: 0, longitude: 0 };

/** Midpoint instant strictly between two boundary times. */
function midpoint(a: Date, b: Date): Date {
	return new Date((a.getTime() + b.getTime()) / 2);
}

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

	it('widens dawn through the morning golden hour', () => {
		const times = SunCalc.getTimes(new Date('2026-06-21T12:00:00.000Z'), EQUATOR.latitude, EQUATOR.longitude);
		const at = midpoint(times.sunrise, times.goldenHourEnd);
		expect(resolveSolarPhase(EQUATOR, at)).toBe('dawn');
	});

	it('widens dusk to begin at the evening golden hour', () => {
		const times = SunCalc.getTimes(new Date('2026-06-21T12:00:00.000Z'), EQUATOR.latitude, EQUATOR.longitude);
		const at = midpoint(times.goldenHour, times.sunset);
		expect(resolveSolarPhase(EQUATOR, at)).toBe('dusk');
	});

	it('keeps deep night night', () => {
		const at = new Date('2026-06-21T00:00:00.000Z');
		expect(resolveSolarPhase(EQUATOR, at)).toBe('night');
	});
});
