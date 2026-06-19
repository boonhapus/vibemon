/** Shared solar phase for scene backgrounds — driven by stored trainer coordinates. */

import { browser } from '$app/environment';

import {
	readStoredTrainerCoordinates,
	type TrainerCoordinates
} from '$lib/domains/trainer/trainerGeolocation';

import {
	DEFAULT_SOLAR_PHASE,
	parseSolarPhase,
	resolveSolarPhase,
	type SolarPhase
} from './solarPhase';

const PHASE_REFRESH_MS = 60_000;

export const gameSolarContext = $state({
	coordinates: null as TrainerCoordinates | null,
	override: null as SolarPhase | null,
	phase: DEFAULT_SOLAR_PHASE as SolarPhase
});

/** False until mount — keeps SSR and hydration on DEFAULT_SOLAR_PHASE, then crossfades to live phase. */
let scenePhaseReady = $state(false);

/** Phase for scene backdrops — stable across SSR/hydration, then live after mount. */
export function sceneSolarPhase(): SolarPhase {
	if (!scenePhaseReady) return DEFAULT_SOLAR_PHASE;
	return gameSolarContext.phase;
}

export function syncGameSolarCoordinates(coords: TrainerCoordinates | null = readStoredTrainerCoordinates()) {
	gameSolarContext.coordinates = coords;
}

export function setGameSolarOverride(phase: SolarPhase | null) {
	gameSolarContext.override = phase;
}

export function refreshGameSolarPhase(at: Date = new Date()) {
	gameSolarContext.phase =
		gameSolarContext.override ??
		resolveSolarPhase(gameSolarContext.coordinates, at);
}

export function applyGameSolarDevOverride(searchParams: URLSearchParams) {
	setGameSolarOverride(parseSolarPhase(searchParams.get('solar-phase')));
	refreshGameSolarPhase();
}

let refreshTimer: ReturnType<typeof setInterval> | undefined;

export function startGameSolarClock() {
	if (!browser) return;
	if (!refreshTimer) {
		syncGameSolarCoordinates();
		refreshGameSolarPhase();
		refreshTimer = setInterval(() => refreshGameSolarPhase(), PHASE_REFRESH_MS);
	}
	scenePhaseReady = true;
}

export function stopGameSolarClock() {
	if (!refreshTimer) return;
	clearInterval(refreshTimer);
	refreshTimer = undefined;
	scenePhaseReady = false;
}
