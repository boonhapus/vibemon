import { describe, expect, it } from 'vitest';

import {
	buildSwapPairs,
	mirrorForPosition,
	quantizeRotation,
	ringPosition,
	rotationDeltaToFront,
	spotlightSlot
} from './crewRingMath';
import { buildParty, mod, PARTY_SIZE } from './crewSlots';

describe('crewSlots', () => {
	it('maps members onto fixed party slots', () => {
		const party = buildParty([
			{
				id: 'a',
				name: 'Alpha',
				nickname: null,
				level: 5,
				current_hp: 20,
				max_hp: 20,
				xp: 120,
				xp_to_next: 55,
				xp_bar_ratio: 0.4,
				crew_slot: 2,
				sprite_url: '/a.png',
				reference_detected_facing: 'LEFT',
				detail: { id: 'a', name: 'Alpha' } as never
			}
		]);

		expect(party).toHaveLength(PARTY_SIZE);
		expect(party[2].name).toBe('ALPHA');
		expect(party[0].empty).toBe(true);
		expect(party[0].spriteSrc).toBe('');
	});

	it('uses positive modulo for rotation math', () => {
		expect(mod(-1, 6)).toBe(5);
		expect(mod(7, 6)).toBe(1);
	});
});

describe('crewRingMath', () => {
	it('quantizes rotation into clock steps', () => {
		expect(quantizeRotation(1.24)).toBe(1.25);
	});

	it('picks the shortest rotation to bring a seat forward', () => {
		expect(rotationDeltaToFront(0, 1)).toBe(1);
		expect(rotationDeltaToFront(0, 5)).toBe(-1);
		expect(rotationDeltaToFront(2, 2)).toBe(0);
	});

	it('builds swap pairs for occupied targets', () => {
		const pairs = buildSwapPairs('active', 0, 3, [
			{ id: 'active', crew_slot: 0 },
			{ id: 'other', crew_slot: 3 }
		]);
		expect(pairs).toEqual([
			{ memberId: 'active', fromSlot: 0, toSlot: 3 },
			{ memberId: 'other', fromSlot: 3, toSlot: 0 }
		]);
	});

	it('mirrors left-of-center seats so sprites face inward', () => {
		const slot = { empty: false } as never;
		const atRest = Array.from({ length: PARTY_SIZE }, (_, crewSlot) =>
			ringPosition(crewSlot, 0)
		);

		expect(atRest.map(({ x }) => mirrorForPosition(slot, x))).toEqual([
			false,
			false,
			false,
			true,
			true,
			true
		]);
	});

	it('finds the spotlight slot at the lead anchor', () => {
		const party = buildParty([
			{
				id: 'lead',
				name: 'Lead',
				nickname: null,
				level: 1,
				current_hp: 10,
				max_hp: 10,
				xp: 0,
				xp_to_next: 8,
				xp_bar_ratio: 0,
				crew_slot: 4,
				sprite_url: '/lead.png',
				reference_detected_facing: 'LEFT',
				detail: { id: 'lead', name: 'Lead' } as never
			}
		]);
		expect(spotlightSlot(party, 4)?.id).toBe('lead');
	});
});
