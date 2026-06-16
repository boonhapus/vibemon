/** Grass-ring slot layout for title-screen mon silhouettes. */

export type TitleMonSlot = {
	id: string;
	leftPct: number;
	bottomPct: number;
	scale: number;
	delayMs: number;
	durationMs: number;
	/** Flip canonical left-facing sprites to face inward toward ring center. */
	mirrored: boolean;
	/** Raise the anchor (+bottomPct) to visually align feet across sprites. */
	footLiftPct?: number;
};

export const TITLE_MON_SLOT_COUNT = 4;

/**
 * Ellipse inscribed in `.title-scene__grass-stage`, aligned to the tall-grass
 * oval painted in title--day.png. Keep in sync with the stage width/height CSS.
 */
export const TITLE_GRASS_OVAL = {
	cx: 50,
	/** Below geometric center — the painted oval reads lower in the stage box. */
	cy: 28,
	rx: 32,
	ry: 29
} as const;

/**
 * Half a mon body as % of the grass stage — matches TitleGrassMon width
 * (12vw) over the stage box (92vw): (12 / 2) / 92 ≈ 6.5%.
 */
export const TITLE_OUTER_INSET_PCT = 6.5;

/** Shared foot-lift for outer baseline mons so mirrored/unmirrored sprites share one ground line. */
export const TITLE_OUTER_FOOT_LIFT_PCT = TITLE_OUTER_INSET_PCT;

/** Outer mon on the shared foot baseline, inset from the ring edge by half a body. */
function grassBaselineSlot(
	id: string,
	side: 'left' | 'right',
	scale: number,
	delayMs: number,
	durationMs: number
): TitleMonSlot {
	const { cx, cy, rx } = TITLE_GRASS_OVAL;
	const leftPct =
		side === 'left' ? cx - rx + TITLE_OUTER_INSET_PCT : cx + rx - TITLE_OUTER_INSET_PCT;
	return {
		id,
		leftPct,
		bottomPct: cy,
		scale,
		delayMs,
		durationMs,
		mirrored: side === 'left',
		footLiftPct: TITLE_OUTER_FOOT_LIFT_PCT
	};
}

/** Place one anchor on the grass oval at a compass angle (0° = right, 90° = top). */
function grassArcSlot(
	id: string,
	degrees: number,
	scale: number,
	delayMs: number,
	durationMs: number
): TitleMonSlot {
	const rad = (degrees * Math.PI) / 180;
	const { cx, cy, rx, ry } = TITLE_GRASS_OVAL;
	const leftPct = cx + rx * Math.cos(rad);
	const sin = Math.sin(rad);
	const bottomPct = Math.abs(sin) < 1e-9 ? cy : cy + ry * sin;
	return {
		id,
		leftPct,
		bottomPct,
		scale,
		delayMs,
		durationMs,
		mirrored: leftPct < cx
	};
}

/**
 * Four mons on the far arc — outer pair on the horizontal diameter (180°/0°) so
 * feet share one baseline; inner angles tuned for even horizontal spacing.
 */
export const TITLE_MON_SLOTS: readonly TitleMonSlot[] = [
	grassBaselineSlot('slot-a', 'left', 1.85, 0, 5200),
	grassArcSlot('slot-b', 105, 1.95, 900, 6000),
	grassArcSlot('slot-c', 75, 1.95, 1800, 5600),
	grassBaselineSlot('slot-d', 'right', 1.85, 2700, 4800)
] as const;

export function zipTitleMonSprites(
	slots: readonly TitleMonSlot[],
	spriteSrcs: readonly string[]
): Array<TitleMonSlot & { spriteSrc: string }> {
	const fallback = spriteSrcs[0] ?? '/game/sprites/hatchling-silhouette@128.png';
	return slots.map((slot, index) => ({
		...slot,
		spriteSrc: spriteSrcs[index % spriteSrcs.length] ?? fallback
	}));
}
