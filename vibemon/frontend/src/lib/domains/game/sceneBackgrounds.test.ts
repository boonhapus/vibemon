import { describe, expect, it } from 'vitest';

import { sceneBackgroundAsset, sceneBackgroundSrc } from './sceneBackgrounds';

describe('sceneBackgroundSrc', () => {
	it('uses legacy filenames for canonical phases', () => {
		expect(sceneBackgroundSrc('title', 'day')).toBe('/game/backgrounds/title.png');
		expect(sceneBackgroundSrc('hatch', 'dawn')).toBe('/game/backgrounds/hatch.png');
		expect(sceneBackgroundSrc('register', 'dawn')).toBe('/game/backgrounds/register.png');
		expect(sceneBackgroundSrc('crew-showcase', 'day')).toBe('/game/backgrounds/crew-showcase.png');
		expect(sceneBackgroundSrc('battle', 'day')).toBe('/game/backgrounds/battle.png');
	});

	it('uses phase suffixes for non-canonical variants', () => {
		expect(sceneBackgroundSrc('title', 'dawn')).toBe('/game/backgrounds/title--dawn.png');
		expect(sceneBackgroundSrc('title', 'night')).toBe('/game/backgrounds/title--night.png');
		expect(sceneBackgroundSrc('hatch', 'night')).toBe('/game/backgrounds/hatch--night.png');
		expect(sceneBackgroundSrc('crew-showcase', 'dusk')).toBe(
			'/game/backgrounds/crew-showcase--dusk.png'
		);
		expect(sceneBackgroundSrc('battle', 'dawn')).toBe('/game/backgrounds/battle--dawn.png');
		expect(sceneBackgroundSrc('battle', 'dusk')).toBe('/game/backgrounds/battle--dusk.png');
		expect(sceneBackgroundSrc('battle', 'night')).toBe('/game/backgrounds/battle--night.png');
	});
});

describe('sceneBackgroundAsset', () => {
	it('always uses phase suffix for asset pipeline paths', () => {
		expect(sceneBackgroundAsset('register', 'dawn')).toBe('game/backgrounds/register--dawn.png');
	});
});
