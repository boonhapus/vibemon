import { type SolarPhase } from './solarPhase';

export type SceneBackgroundId = 'title' | 'register' | 'hatch' | 'crew-showcase' | 'battle';

/** Canonical phase each scene was authored for — used as legacy single-file fallback. */
export const SCENE_CANONICAL_PHASE: Record<SceneBackgroundId, SolarPhase> = {
	title: 'day',
	register: 'dawn',
	hatch: 'dawn',
	'crew-showcase': 'day',
	battle: 'day'
};

export function sceneBackgroundAsset(scene: SceneBackgroundId, phase: SolarPhase): string {
	return `game/backgrounds/${scene}--${phase}.png`;
}

/** Public URL for a scene backdrop at the given solar phase. */
export function sceneBackgroundSrc(scene: SceneBackgroundId, phase: SolarPhase): string {
	if (phase === SCENE_CANONICAL_PHASE[scene]) {
		return `/game/backgrounds/${scene}.png`;
	}
	return `/game/backgrounds/${scene}--${phase}.png`;
}
