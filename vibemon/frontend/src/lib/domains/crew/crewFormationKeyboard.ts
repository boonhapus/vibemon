import { resolveCrewPositionPick, type CrewCommandId } from './crewFormationMenu';

export const CREW_COMMAND_MENU_INDEX: Record<CrewCommandId, number> = {
	swap: 0,
	wild: 1,
	roster: 2,
	cancel: 3
};

export type CrewKeyboardAction =
	| { type: 'hold-read' }
	| { type: 'ring-step'; delta: -1 | 1 }
	| { type: 'ring-slot'; slotIndex: number }
	| { type: 'menu-nav'; key: string }
	| { type: 'menu-confirm' }
	| { type: 'command'; commandId: CrewCommandId }
	| { type: 'position-pick'; slotIndex: number }
	| { type: 'consume' };

type KeyEventLike = {
	key: string;
	altKey: boolean;
	ctrlKey: boolean;
	repeat: boolean;
	defaultPrevented: boolean;
};

type ModeLike = {
	swapMode: boolean;
};

/** Route keyboard input: Alt overlay (ring) vs basic menu/command layer. */
export function resolveCrewFormationKeydown(
	event: KeyEventLike,
	mode: ModeLike
): CrewKeyboardAction | null {
	if (event.ctrlKey) return null;

	if (event.key === 'c' || event.key === 'C') {
		return event.repeat ? null : { type: 'hold-read' };
	}

	if (event.defaultPrevented) return null;

	if (event.altKey) {
		if (event.key >= '1' && event.key <= '6') {
			return { type: 'ring-slot', slotIndex: Number(event.key) - 1 };
		}

		switch (event.key) {
			case 'ArrowLeft':
			case 'ArrowUp':
				return { type: 'ring-step', delta: -1 };
			case 'ArrowRight':
			case 'ArrowDown':
				return { type: 'ring-step', delta: 1 };
			default:
				return { type: 'consume' };
		}
	}

	const lower = event.key.toLowerCase();
	if (lower === 's') return { type: 'command', commandId: 'swap' };
	if (!mode.swapMode) {
		if (lower === 'w') return { type: 'command', commandId: 'wild' };
		if (lower === 'r') return { type: 'command', commandId: 'roster' };
	}
	if (event.key === 'Escape') return { type: 'command', commandId: 'cancel' };

	const positionPick = resolveCrewPositionPick(event.key, mode.swapMode);
	if (positionPick !== null) {
		return { type: 'position-pick', slotIndex: positionPick };
	}

	switch (event.key) {
		case 'ArrowLeft':
		case 'ArrowRight':
		case 'ArrowUp':
		case 'ArrowDown':
			return { type: 'menu-nav', key: event.key };
		case 'Enter':
		case ' ':
			return { type: 'menu-confirm' };
		default:
			return null;
	}
}

export function resolveCrewFormationKeyup(event: { key: string }): 'release-read' | null {
	if (event.key === 'c' || event.key === 'C') return 'release-read';
	return null;
}
