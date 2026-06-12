/** Shared crew slot mapping for the roster and clock-formation views. */

import type { CrewMember, HatchCandidate, SpriteFacing } from '$lib/domains/trainer/hatchApi';

export const PLACEHOLDER_SPRITE = '/game/sprites/hatchling-silhouette@128.png';
export const PARTY_SIZE = 6;

/* Mon height relative to the trainer sprite, by size class — same bands the
   hatch scene uses, interpolated by power pips so heights agree across pages. */
const SIZE_BANDS: Record<string, [number, number]> = {
	small: [0.4, 0.55],
	mid: [0.7, 0.95],
	large: [1.1, 1.3]
};

export const EMPTY_SLOT_HEIGHT_FACTOR = 0.5;

export function trainerRelativeHeight(detail: HatchCandidate | null): number {
	if (!detail) return EMPTY_SLOT_HEIGHT_FACTOR;
	const band = SIZE_BANDS[detail.display?.size_class ?? 'mid'] ?? SIZE_BANDS.mid;
	const t = (Math.min(Math.max(detail.power_pips ?? 2, 1), 3) - 1) / 2;
	return band[0] + (band[1] - band[0]) * t;
}

export type PartySlot = {
	id: string;
	name: string;
	level: number;
	currentHp: number;
	maxHp: number;
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
		spriteSrc: PLACEHOLDER_SPRITE,
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
