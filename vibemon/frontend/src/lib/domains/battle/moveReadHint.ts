import type { BattleMove } from './battleApi';

export function moveReadHint(move: Pick<BattleMove, 'flavor_text' | 'combat_hints'>): string {
	const parts: string[] = [];
	const flavor = move.flavor_text?.trim();
	if (flavor) parts.push(flavor);
	if (move.combat_hints?.length) parts.push(...move.combat_hints);
	return parts.join(' ') || 'No lore recorded for this move yet.';
}
