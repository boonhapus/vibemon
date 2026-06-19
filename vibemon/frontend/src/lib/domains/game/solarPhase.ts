/**
 * Live, UI-only solar phase for scene-background ambiance — computed from the player's
 * current time and coordinates. Dawn/dusk are intentionally widened to the golden hours so
 * crepuscular backgrounds appear earlier; this is distinct from the backend birth-instant
 * phase used for mon generation and is not meant to mirror it.
 */

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

/**
 * Resolve the display solar phase at `at` for `coords`. Dawn spans civil dawn through the
 * morning golden hour, dusk spans the evening golden hour through civil dusk — so twilight
 * backgrounds show earlier than the bare sunrise/sunset boundaries.
 */
export function resolveSolarPhase(
	coords: GeoCoordinates | null | undefined,
	at: Date = new Date()
): SolarPhase {
	if (!coords) return DEFAULT_SOLAR_PHASE;

	const times = SunCalc.getTimes(at, coords.latitude, coords.longitude);
	if (
		!isValidTime(times.dawn) ||
		!isValidTime(times.goldenHourEnd) ||
		!isValidTime(times.goldenHour) ||
		!isValidTime(times.dusk)
	) {
		return polarFallback(coords.latitude);
	}

	const instant = at.getTime();
	if (instant < times.dawn.getTime()) return 'night';
	if (instant < times.goldenHourEnd.getTime()) return 'dawn';
	if (instant < times.goldenHour.getTime()) return 'day';
	if (instant < times.dusk.getTime()) return 'dusk';
	return 'night';
}
