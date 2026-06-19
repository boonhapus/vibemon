import { describe, expect, it } from 'vitest';

import { emoteHappyFromBattleSprite } from './battleSpriteUrls';

describe('emoteHappyFromBattleSprite', () => {
	it('swaps battle pose path for emote-happy', () => {
		expect(
			emoteHappyFromBattleSprite(
				'/api/assets/mons/019edc9f-c97f-7036-8999-87aba37f927a/v1/r1/pose/battle-back.png'
			)
		).toBe(
			'/api/assets/mons/019edc9f-c97f-7036-8999-87aba37f927a/v1/r1/pose/emote-happy.png'
		);
	});

	it('returns null when no pose segment exists', () => {
		expect(emoteHappyFromBattleSprite('/api/assets/mons/x/v1/r1/sprite/reference.png')).toBeNull();
	});
});
