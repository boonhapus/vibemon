/** Gear sprite pose paths under `/game/sprites/`. */
export type GearSpriteKey = 'camera' | 'vibe-deck' | 'vibe-cart';
export type GearSpriteFacing = 'left' | 'right';

export function gearSpritePath(key: GearSpriteKey, facing: GearSpriteFacing): string {
	return `/game/sprites/${key}-${facing}.png`;
}
