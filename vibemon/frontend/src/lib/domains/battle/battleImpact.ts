/**
 * Maps a hit's type effectiveness + crit flag onto the visual intensity of the
 * battle hit-feedback (camera shake, flash, contact burst). DESIGN.md §6 keeps
 * motion stepped and cozy, so intensity is carried by burst size / flash lift
 * more than by camera violence — `impactStrength` stays bounded and small.
 */

export type ImpactTier = 'immune' | 'resisted' | 'neutral' | 'super';

export function impactTier(effectiveness: number): ImpactTier {
	if (effectiveness <= 0) return 'immune';
	if (effectiveness > 1) return 'super';
	if (effectiveness < 1) return 'resisted';
	return 'neutral';
}

const TIER_BASE_STRENGTH: Record<ImpactTier, number> = {
	immune: 0,
	resisted: 0.4,
	neutral: 0.7,
	super: 1
};

const CRIT_BONUS = 0.3;
const MAX_STRENGTH = 1.3;

/**
 * Relative intensity used to drive CSS `--impact-strength`. Neutral hits land
 * around 0.7; super-effective at 1; a crit lifts the result (capped) so a
 * critical, super-effective hit reads as the biggest on-screen.
 */
export function impactStrength(effectiveness: number, crit = false): number {
	const base = TIER_BASE_STRENGTH[impactTier(effectiveness)];
	if (base === 0) return 0;
	return crit ? Math.min(MAX_STRENGTH, base + CRIT_BONUS) : base;
}
