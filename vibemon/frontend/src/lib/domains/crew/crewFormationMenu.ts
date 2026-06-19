export type CrewCommandId = 'swap' | 'wild' | 'roster' | 'cancel';

export type CrewCommand = {
	id: CrewCommandId;
	label: string;
	hint: string;
	/** Burnt-orange keyboard hint on the label; omit when the letter is reserved elsewhere. */
	hotkey?: string;
	disabled?: boolean;
};

/** Player hints — short, cozy register (VOICE.md). */
export const CREW_FORMATION_COMMANDS: CrewCommand[] = [
	{
		id: 'swap',
		label: 'SWAP',
		hint: 'Change this Vibemon\'s place in the crew.',
		hotkey: 'S'
	},
	{
		id: 'wild',
		label: 'WILD',
		hint: 'Seek Wild Vibemon and grow your crew.',
		hotkey: 'W'
	},
	{
		id: 'roster',
		label: 'ROSTER',
		hint: 'See the classic view of your crew.',
		hotkey: 'R'
	},
	{
		id: 'cancel',
		label: 'CANCEL',
		hint: 'Return to the previous scene.'
	}
];

export const CREW_POSITION_LABELS = ['LEAD', '2', '3', '4', '5', '6'] as const;

export type CrewPositionSlot = {
	label: (typeof CREW_POSITION_LABELS)[number];
	hotkeys: readonly string[];
};

/** Swap-mode position grid — LEAD accepts 1 or L. */
export const CREW_POSITION_SLOTS: CrewPositionSlot[] = [
	{ label: 'LEAD', hotkeys: ['1', 'L'] },
	{ label: '2', hotkeys: ['2'] },
	{ label: '3', hotkeys: ['3'] },
	{ label: '4', hotkeys: ['4'] },
	{ label: '5', hotkeys: ['5'] },
	{ label: '6', hotkeys: ['6'] }
];

export function resolveCrewPositionPick(key: string, swapMode: boolean): number | null {
	if (!swapMode) return null;
	const lower = key.toLowerCase();
	for (let slotIndex = 0; slotIndex < CREW_POSITION_SLOTS.length; slotIndex += 1) {
		const slot = CREW_POSITION_SLOTS[slotIndex];
		if (slot.hotkeys.some((hotkey) => hotkey.toLowerCase() === lower)) return slotIndex;
	}
	return null;
}

export const CREW_SWAP_EMPTY_TOAST = 'Spin to a Vibemon before swapping seats.';

const POSITION_COLS = 3;
const POSITION_ROWS = 2;

export function crewPositionHint(slotIndex: number): string {
	if (slotIndex === 0) return 'Set this Vibemon as lead.';
	return `Move to position ${slotIndex + 1}.`;
}

export function crewMenuHint(mode: 'command' | 'position', index: number): string {
	if (mode === 'position') return crewPositionHint(index);
	return CREW_FORMATION_COMMANDS[index]?.hint ?? '';
}

export function navigateCrewPositionGrid(index: number, key: string): number {
	const col = index % POSITION_COLS;
	const row = Math.floor(index / POSITION_COLS);

	switch (key) {
		case 'ArrowLeft':
			return col > 0 ? index - 1 : index;
		case 'ArrowRight':
			return col < POSITION_COLS - 1 ? index + 1 : index;
		case 'ArrowUp':
			return row > 0 ? index - POSITION_COLS : index;
		case 'ArrowDown':
			return row < POSITION_ROWS - 1 ? index + POSITION_COLS : index;
		default:
			return index;
	}
}
