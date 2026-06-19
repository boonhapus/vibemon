export type CommandId = 'moves' | 'deck' | 'crew' | 'run';

export const DECK_COMING_SOON_TOAST =
	'Coming soon -- access the Vibe Deck during battles!';

export const CREW_COMING_SOON_TOAST =
	'Coming soon -- switch to another Vibemon for this battle!';

export type BattleCommand = {
	id: CommandId;
	label: string;
	disabled?: boolean;
	disabledToast?: string;
};

export const BATTLE_COMMANDS: BattleCommand[] = [
	{ id: 'moves', label: 'MOVES' },
	{ id: 'deck', label: 'DECK', disabled: true, disabledToast: DECK_COMING_SOON_TOAST },
	{ id: 'crew', label: 'CREW', disabled: true, disabledToast: CREW_COMING_SOON_TOAST },
	{ id: 'run', label: 'RUN' }
];
