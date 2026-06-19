import { describe, expect, it } from 'vitest';

import { resolveCrewFormationKeydown } from './crewFormationKeyboard';

const baseEvent = {
	altKey: false,
	ctrlKey: false,
	repeat: false,
	defaultPrevented: false
};

describe('resolveCrewFormationKeydown', () => {
	const commandMode = { swapMode: false };
	const swapMode = { swapMode: true };

	it('routes alt overlay exclusively to ring controls', () => {
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 's', altKey: true }, commandMode)).toEqual({
			type: 'consume'
		});
		expect(
			resolveCrewFormationKeydown({ ...baseEvent, key: 'ArrowRight', altKey: true }, commandMode)
		).toEqual({ type: 'ring-step', delta: 1 });
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: '3', altKey: true }, commandMode)).toEqual({
			type: 'ring-slot',
			slotIndex: 2
		});
	});

	it('binds basic command shortcuts without alt', () => {
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 's' }, commandMode)).toEqual({
			type: 'command',
			commandId: 'swap'
		});
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 'W' }, commandMode)).toEqual({
			type: 'command',
			commandId: 'wild'
		});
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 'r' }, commandMode)).toEqual({
			type: 'command',
			commandId: 'roster'
		});
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 'Escape' }, commandMode)).toEqual({
			type: 'command',
			commandId: 'cancel'
		});
	});

	it('blocks wild and roster shortcuts while swapping positions', () => {
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 'w' }, swapMode)).toBeNull();
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 's' }, swapMode)).toEqual({
			type: 'command',
			commandId: 'swap'
		});
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: '2' }, swapMode)).toEqual({
			type: 'position-pick',
			slotIndex: 1
		});
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 'l' }, swapMode)).toEqual({
			type: 'position-pick',
			slotIndex: 0
		});
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: '1' }, swapMode)).toEqual({
			type: 'position-pick',
			slotIndex: 0
		});
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 'l' }, commandMode)).toBeNull();
	});

	it('keeps arrow keys on the menu when alt is not held', () => {
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 'ArrowDown' }, commandMode)).toEqual({
			type: 'menu-nav',
			key: 'ArrowDown'
		});
	});

	it('ignores hotkeys while control is held', () => {
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 's', ctrlKey: true }, commandMode)).toBeNull();
		expect(resolveCrewFormationKeydown({ ...baseEvent, key: 'c', ctrlKey: true }, commandMode)).toBeNull();
		expect(
			resolveCrewFormationKeydown({ ...baseEvent, key: 'ArrowRight', altKey: true, ctrlKey: true }, commandMode)
		).toBeNull();
	});
});
