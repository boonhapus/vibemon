/** Ring placement and depth math for the crew clock formation. */

import { mod, PARTY_SIZE, type PartySlot, type SwapAnimPair } from './crewSlots';

export const ROTATE_DURATION_MS = 450;
export const STEPS_PER_ADVANCE = 8;
export const SLOT_ANGLE_DEG = 360 / PARTY_SIZE;
export const LEAD_ANGLE_DEG = 60;

// Front/spotlight slot renders at the mon's normal trainer-relative height (max 1.0);
// slots scale down toward the min as they rotate out of view.
const DEPTH_SCALE_MIN = 0.62;
const DEPTH_SCALE_MAX = 1.0;

export function quantizeRotation(rotation: number): number {
	return Math.round(rotation * STEPS_PER_ADVANCE) / STEPS_PER_ADVANCE;
}

export function rotationDeltaToFront(currentRotation: number, targetSlot: number): number {
	let delta = mod(targetSlot - currentRotation, PARTY_SIZE);
	if (delta > PARTY_SIZE / 2) delta -= PARTY_SIZE;
	return delta;
}

export function spotlightFactor(ringOffset: number): number {
	return Math.cos(ringOffset * SLOT_ANGLE_DEG * (Math.PI / 180));
}

export function depthScale(ringOffset: number): number {
	const spotlight = spotlightFactor(ringOffset);
	const t = (spotlight + 1) / 2;
	const curved = t * t * t;
	return DEPTH_SCALE_MIN + curved * (DEPTH_SCALE_MAX - DEPTH_SCALE_MIN);
}

export function depthCool(ringOffset: number): number {
	const spotlight = spotlightFactor(ringOffset);
	const t = (spotlight + 1) / 2;
	return (1 - t * t) * 18;
}

export function isSpotlight(ringOffset: number): boolean {
	return spotlightFactor(ringOffset) > 0.92;
}

export function mirrorForPosition(slot: PartySlot, x: number): boolean {
	if (slot.empty) return false;
	// Reference sprites are canonicalized to face screen-LEFT in postprocessing
	// (orient_reference_left), so facing is purely positional — never trust the stale
	// per-mon reference_detected_facing here. A left-facing sprite already looks inward
	// when right of center; mirror it to face RIGHT only when it's left of center.
	// Single threshold at x=0 → exactly one flip per crossing; resting slots never sit
	// at x≈0 (cos values are ±0.5/±1), so the sign is stable at rest.
	return x < 0;
}

export function effectiveCrewSlot(
	slot: PartySlot,
	swapAnimation: { pairs: SwapAnimPair[]; progress: number } | null
): number {
	if (!swapAnimation) return slot.crewSlot;
	const pair = swapAnimation.pairs.find((entry) => entry.memberId === slot.id);
	if (!pair || swapAnimation.progress <= 0) return slot.crewSlot;
	let delta = mod(pair.toSlot - pair.fromSlot, PARTY_SIZE);
	if (delta > PARTY_SIZE / 2) delta -= PARTY_SIZE;
	return pair.fromSlot + delta * swapAnimation.progress;
}

export function ringPosition(crewSlot: number, displayRotation: number) {
	const ringOffset = crewSlot - displayRotation;
	const angle = ((LEAD_ANGLE_DEG - ringOffset * SLOT_ANGLE_DEG) * Math.PI) / 180;
	return {
		ringOffset,
		x: Math.cos(angle),
		y: Math.sin(angle),
		cos: Math.cos(angle),
		sin: Math.sin(angle)
	};
}

export function spotlightSlot(slots: PartySlot[], rotation: number): PartySlot | undefined {
	return slots.find((slot) => !slot.empty && mod(slot.crewSlot - rotation, PARTY_SIZE) === 0);
}

export function seatTickPositions() {
	return Array.from({ length: PARTY_SIZE }, (_, index) => {
		const angle = ((LEAD_ANGLE_DEG - index * SLOT_ANGLE_DEG) * Math.PI) / 180;
		return { x: Math.cos(angle), y: Math.sin(angle) };
	});
}

export function buildSwapPairs(
	activeId: string,
	from: number,
	target: number,
	members: ReadonlyArray<{ id: string; crew_slot: number }>
): SwapAnimPair[] {
	const occupant = members.find((member) => member.crew_slot === target);
	const pairs: SwapAnimPair[] = [{ memberId: activeId, fromSlot: from, toSlot: target }];
	if (occupant && occupant.id !== activeId) {
		pairs.push({ memberId: occupant.id, fromSlot: target, toSlot: from });
	}
	return pairs;
}
