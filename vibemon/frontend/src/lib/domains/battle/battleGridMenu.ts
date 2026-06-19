export const BATTLE_GRID_SLOTS = 4;

export function navigateBattleGrid(
	index: number,
	key: string,
	validCount: number = BATTLE_GRID_SLOTS
): number {
	const step = (slot: number): number => {
		switch (key) {
			case 'ArrowUp':
			case 'ArrowDown':
				return (slot + 2) % BATTLE_GRID_SLOTS;
			case 'ArrowLeft':
				return (slot + 3) % BATTLE_GRID_SLOTS;
			case 'ArrowRight':
				return (slot + 1) % BATTLE_GRID_SLOTS;
			default:
				return slot;
		}
	};

	const next = step(index);
	if (next < validCount) return next;

	// Down into empty bottom-right (e.g. 3 moves): land on bottom-left instead.
	if (
		(key === 'ArrowUp' || key === 'ArrowDown') &&
		next === validCount &&
		next % 2 === 1
	) {
		return next - 1;
	}

	return index;
}
