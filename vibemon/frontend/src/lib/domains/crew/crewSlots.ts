/** Shared crew slot mapping for the roster and clock-formation views. */

import type { CrewMember, HatchCandidate, SpriteFacing } from '$lib/domains/trainer/hatchApi';
import {
	EMPTY_SLOT_HEIGHT_FACTOR,
	trainerRelativeHeight
} from '$lib/domains/trainer/hatchDisplaySize';

export const PLACEHOLDER_SPRITE = '/game/sprites/hatchling-silhouette@128.png';
export const PARTY_SIZE = 6;

export { EMPTY_SLOT_HEIGHT_FACTOR, trainerRelativeHeight };

export type PartySlot = {
	id: string;
	name: string;
	level: number;
	currentHp: number;
	maxHp: number;
	xp: number;
	xpToNext: number;
	xpBarRatio: number;
	spriteSrc: string;
	facing: SpriteFacing | null;
	crewSlot: number;
	empty: boolean;
	detail: HatchCandidate | null;
	/** Sprite height as a fraction of the trainer's height. */
	heightFactor: number;
};

/** Map API members onto a fixed array of PARTY_SIZE slots indexed by crew_slot. */
export function buildParty(members: CrewMember[], partySize: number = PARTY_SIZE): PartySlot[] {
	const slots: PartySlot[] = Array.from({ length: partySize }, (_, crewSlot) => ({
		id: `empty-${crewSlot}`,
		name: '',
		level: 0,
		currentHp: 0,
		maxHp: 0,
		xp: 0,
		xpToNext: 0,
		xpBarRatio: 0,
		spriteSrc: '',
		facing: null,
		crewSlot,
		empty: true,
		detail: null,
		heightFactor: EMPTY_SLOT_HEIGHT_FACTOR
	}));

	for (const member of members) {
		const slot = member.crew_slot;
		if (slot < 0 || slot >= partySize) continue;
		slots[slot] = {
			id: member.id,
			name: (member.nickname?.trim() || member.name).toUpperCase(),
			level: member.level,
			currentHp: member.current_hp,
			maxHp: member.max_hp,
			xp: member.xp,
			xpToNext: member.xp_to_next,
			xpBarRatio: member.xp_bar_ratio,
			spriteSrc: member.sprite_url ?? PLACEHOLDER_SPRITE,
			facing: member.reference_detected_facing,
			crewSlot: slot,
			empty: false,
			detail: member.detail,
			heightFactor: trainerRelativeHeight(member.detail)
		};
	}

	return slots;
}

export function hpPercent(slot: PartySlot): number {
	if (slot.empty || slot.maxHp <= 0) return 0;
	return Math.max(0, Math.min(100, (slot.currentHp / slot.maxHp) * 100));
}

/** Positive modulo. */
export function mod(value: number, base: number): number {
	return ((value % base) + base) % base;
}

export type SwapAnimPair = {
	memberId: string;
	fromSlot: number;
	toSlot: number;
};

export type SwapAnimation = {
	pairs: SwapAnimPair[];
	progress: number;
};
