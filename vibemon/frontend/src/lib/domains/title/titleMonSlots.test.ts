import { describe, expect, it } from 'vitest';

import {
	TITLE_GRASS_OVAL,
	TITLE_MON_SLOTS,
	TITLE_OUTER_FOOT_LIFT_PCT,
	TITLE_OUTER_INSET_PCT,
	zipTitleMonSprites
} from './titleMonSlots';

function footBottomPct(slot: (typeof TITLE_MON_SLOTS)[number]): number {
	return slot.bottomPct + (slot.footLiftPct ?? 0);
}

describe('zipTitleMonSprites', () => {
	it('maps four sprites onto the grass-ring slots', () => {
		const sprites = ['/a.png', '/b.png', '/c.png', '/d.png'];
		const zipped = zipTitleMonSprites(TITLE_MON_SLOTS, sprites);
		expect(zipped).toHaveLength(4);
		expect(zipped.map((entry) => entry.spriteSrc)).toEqual(sprites);
	});

	it('repeats available sprites when fewer than four are returned', () => {
		const zipped = zipTitleMonSprites(TITLE_MON_SLOTS, ['/solo.png']);
		expect(zipped.map((entry) => entry.spriteSrc)).toEqual([
			'/solo.png',
			'/solo.png',
			'/solo.png',
			'/solo.png'
		]);
	});
});

describe('TITLE_MON_SLOTS', () => {
	it('spreads mons across the far grass arc without reaching the ring edge', () => {
		const leftPositions = TITLE_MON_SLOTS.map((slot) => slot.leftPct).sort((a, b) => a - b);
		expect(leftPositions[0]).toBeGreaterThanOrEqual(23);
		expect(leftPositions[3]).toBeLessThanOrEqual(77);
		expect(leftPositions[3] - leftPositions[0]).toBeGreaterThan(50);
		expect(leftPositions[3] - leftPositions[0]).toBeLessThan(56);
	});

	it('insets outer mons from the ring edge by half a body', () => {
		const { cx, rx } = TITLE_GRASS_OVAL;
		const [outerLeft, , , outerRight] = TITLE_MON_SLOTS;
		expect(outerLeft.leftPct).toBe(cx - rx + TITLE_OUTER_INSET_PCT);
		expect(outerRight.leftPct).toBe(cx + rx - TITLE_OUTER_INSET_PCT);
	});

	it('aligns outer mon feet on the same ground line', () => {
		const [outerLeft, , , outerRight] = TITLE_MON_SLOTS;
		expect(footBottomPct(outerLeft)).toBe(footBottomPct(outerRight));
		expect(outerLeft.footLiftPct).toBe(TITLE_OUTER_FOOT_LIFT_PCT);
		expect(outerRight.footLiftPct).toBe(TITLE_OUTER_FOOT_LIFT_PCT);
	});

	it('seats the inner pair on the far arc above the outer pair', () => {
		const [outerLeft, innerLeft, innerRight, outerRight] = TITLE_MON_SLOTS.map(
			(slot) => slot.bottomPct
		);
		expect(innerLeft).toBeGreaterThan(outerLeft);
		expect(innerRight).toBeGreaterThan(outerRight);
	});

	it('mirrors left-side mons so all four face inward', () => {
		expect(TITLE_MON_SLOTS.map((slot) => slot.mirrored)).toEqual([true, true, false, false]);
	});

	it('spaces mons with nearly equal horizontal gaps', () => {
		const leftPositions = TITLE_MON_SLOTS.map((slot) => slot.leftPct);
		const gaps = leftPositions.slice(1).map((left, index) => left - leftPositions[index]!);
		const minGap = Math.min(...gaps);
		const maxGap = Math.max(...gaps);
		expect(maxGap - minGap).toBeLessThan(2.5);
	});

	it('keeps slot anchors inside the painted grass ring', () => {
		const ringCx = 50;
		const ringCy = 50;
		const ringRx = 50;
		const ringRy = 50;
		for (const slot of TITLE_MON_SLOTS) {
			const dx = (slot.leftPct - ringCx) / ringRx;
			const dy = (slot.bottomPct - ringCy) / ringRy;
			expect(dx * dx + dy * dy).toBeLessThan(0.95);
		}
	});
});
