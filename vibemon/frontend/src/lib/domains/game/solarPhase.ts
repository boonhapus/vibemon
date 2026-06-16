/** Local solar phase from coordinates — mirrors backend BirthSeed.solar_phase (UTC timezone). */

import SunCalc from 'suncalc';

export type SolarPhase = 'night' | 'dawn' | 'day' | 'dusk';

export const SOLAR_PHASES: readonly SolarPhase[] = ['night', 'dawn', 'day', 'dusk'];

export type GeoCoordinates = {
	latitude: number;
	longitude: number;
};

/** Background fallback when coordinates are unknown (register before geolocation). */
export const DEFAULT_SOLAR_PHASE: SolarPhase = 'dawn';

const SOLAR_PHASE_SET = new Set<string>(SOLAR_PHASES);

export function parseSolarPhase(value: string | null | undefined): SolarPhase | null {
	if (!value) return null;
	const normalized = value.trim().toLowerCase();
	return SOLAR_PHASE_SET.has(normalized) ? (normalized as SolarPhase) : null;
}

function polarFallback(latitude: number): SolarPhase {
	return Math.abs(latitude) > 66 ? 'night' : 'day';
}

function isValidTime(value: Date): boolean {
	return Number.isFinite(value.getTime());
}

/** Resolve solar phase at `at` for `coords`. Uses UTC bands to match backend BirthSeed defaults. */
export function resolveSolarPhase(
	coords: GeoCoordinates | null | undefined,
	at: Date = new Date()
): SolarPhase {
	if (!coords) return DEFAULT_SOLAR_PHASE;

	const times = SunCalc.getTimes(at, coords.latitude, coords.longitude);
	if (!isValidTime(times.dawn) || !isValidTime(times.sunrise) || !isValidTime(times.sunset) || !isValidTime(times.dusk)) {
		return polarFallback(coords.latitude);
	}

	const instant = at.getTime();
	if (instant < times.dawn.getTime()) return 'night';
	if (instant < times.sunrise.getTime()) return 'dawn';
	if (instant < times.sunset.getTime()) return 'day';
	if (instant < times.dusk.getTime()) return 'dusk';
	return 'night';
}
