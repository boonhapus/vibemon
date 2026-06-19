import type { BattleMove } from './battleApi';

export type MoveCategory = BattleMove['category'];

export const MOVE_CATEGORY_STYLES: Record<
	MoveCategory,
	{ label: string; bg: string; fg: string }
> = {
	physical: { label: 'PHYSICAL', bg: '#8b3a2a', fg: 'var(--vm-parchment)' },
	special: { label: 'SPECIAL', bg: 'var(--vm-plum)', fg: 'var(--vm-parchment)' },
	status: { label: 'STATUS', bg: 'var(--vm-status-amber)', fg: 'var(--vm-tobacco)' }
};

/** Dialog text color — badge fill reads clearly on the parchment dialog surface. */
export function moveCategoryTextColor(category: MoveCategory): string {
	return MOVE_CATEGORY_STYLES[category].bg;
}
