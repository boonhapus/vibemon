import { describe, expect, it } from 'vitest';

import type { BattleCombatant, BattleTurn } from './battleApi';
import {
	advanceWonBeat,
	applyHeroProgression,
	buildReplayQueue,
	createBattleSession,
	hpTweenDurationMs,
	patchHeroProgression,
	replayStepDelayMs,
	startXpGainAnimation,
	xpGainedDialogText
} from './battleSession.svelte';

function combatant(overrides: Partial<BattleCombatant> = {}): BattleCombatant {
	return {
		vibemon_id: 'hero-1',
		name: 'Hero',
		types: ['normal'],
		level: 5,
		current_hp: 40,
		max_hp: 40,
		xp: 120,
		xp_to_next: 80,
		moves: [
			{
				id: 'climate.tap',
				name: 'Tap',
				type: 'normal',
				category: 'physical',
				power: 40,
				accuracy: 1,
				pp_current: 20,
				pp_max: 20,
				effectiveness: 1,
				flavor_text: ''
			}
		],
		is_fainted: false,
		status: 'none',
		stat_stages: {},
		volatiles: {},
		sprite_url: null,
		xp_bar_ratio: 0.4,
		...overrides
	};
}

function turn(overrides: Partial<BattleTurn> = {}): BattleTurn {
	const player = combatant();
	const opponent = combatant({
		vibemon_id: 'wild-1',
		name: 'Fodder',
		current_hp: 0,
		max_hp: 20,
		moves: [
			{
				id: 'test.tap',
				name: 'Scratch',
				type: 'normal',
				category: 'special',
				power: 30,
				accuracy: 1,
				pp_current: 20,
				pp_max: 20,
				effectiveness: 1,
				flavor_text: ''
			}
		]
	});
	return {
		events: [],
		messages: [],
		state: {
			battle_id: 'battle-1',
			turn_number: 1,
			concluded: true,
			fled: false,
			player_trainer_id: 'trainer-1',
			wild_vibemon_id: 'wild-1',
			player,
			opponent,
			weather: 'clear',
			winner_trainer_id: 'trainer-1'
		},
		...overrides
	};
}

describe('buildReplayQueue', () => {
	it('orders player move, animation, hurt, hp, and faint message', () => {
		const payload = turn({
			events: [
				{ kind: 'move_used', user: 'Hero', move: 'Tap', targets: ['Fodder'] },
				{ kind: 'damage', source: 'Hero', target: 'Fodder', move: 'Tap', amount: 20, hp_after: 0, is_crit: false, effectiveness: 1 },
				{ kind: 'faint', target: 'Fodder' }
			],
			messages: ['Hero used Tap!', 'It dealt 20 damage.', 'The wild Fodder faints.']
		});

		expect(buildReplayQueue(payload)).toEqual([
			{
				kind: 'message',
				text: 'Hero used Tap!',
				moveHighlight: { name: 'Tap', type: 'normal', category: 'physical' }
			},
			{ kind: 'animation', profile: 'physical', actor: 'player', moveType: 'normal' },
			{
				kind: 'hurt',
				side: 'opponent',
				effectiveness: 1,
				crit: false,
				sourceType: 'normal',
				category: 'physical'
			},
			{ kind: 'hp', side: 'opponent', hp: 0 },
			{ kind: 'message', text: 'It dealt 20 damage.' },
			{ kind: 'faint', side: 'opponent' },
			{ kind: 'message', text: 'The wild Fodder faints.' }
		]);
	});

	it('uses opponent actor and player hp for wild moves', () => {
		const payload = turn({
			events: [
				{ kind: 'move_used', user: 'Fodder', move: 'Scratch', targets: ['Hero'] },
				{
					kind: 'damage',
					source: 'Fodder',
					target: 'Hero',
					move: 'Scratch',
					amount: 8,
					hp_after: 32,
					is_crit: false,
					effectiveness: 1
				}
			],
			messages: ['Fodder used Scratch!', 'It dealt 8 damage.']
		});

		expect(buildReplayQueue(payload)).toEqual([
			{
				kind: 'message',
				text: 'Fodder used Scratch!',
				moveHighlight: { name: 'Scratch', type: 'normal', category: 'special' }
			},
			{ kind: 'animation', profile: 'special', actor: 'opponent', moveType: 'normal' },
			{
				kind: 'hurt',
				side: 'player',
				effectiveness: 1,
				crit: false,
				sourceType: 'normal',
				category: 'special'
			},
			{ kind: 'hp', side: 'player', hp: 32 },
			{ kind: 'message', text: 'It dealt 8 damage.' }
		]);
	});

	it('orders status stat messages after the move animation', () => {
		const payload = turn({
			state: {
				battle_id: 'battle-1',
				turn_number: 1,
				concluded: false,
				fled: false,
				player_trainer_id: 'trainer-1',
				wild_vibemon_id: 'wild-1',
				player: combatant({
					moves: [
						{
							id: 'test.growl',
							name: 'Growl',
							type: 'normal',
							category: 'status',
							power: null,
							accuracy: 1,
							pp_current: 20,
							pp_max: 20,
							effectiveness: 1,
							flavor_text: ''
						}
					]
				}),
				opponent: combatant({ vibemon_id: 'wild-1', name: 'Fodder' }),
				weather: 'clear',
				winner_trainer_id: null
			},
			events: [
				{ kind: 'move_used', user: 'Hero', move: 'Growl', targets: ['Fodder'] },
				{ kind: 'stat_change', target: 'Fodder', changes: { attack: -1 } }
			],
			messages: ['Hero used Growl!', 'Their Attack has dropped!']
		});

		expect(buildReplayQueue(payload)).toEqual([
			{
				kind: 'message',
				text: 'Hero used Growl!',
				moveHighlight: { name: 'Growl', type: 'normal', category: 'status' }
			},
			{ kind: 'animation', profile: 'status', actor: 'player', moveType: 'normal' },
			{ kind: 'message', text: 'Their Attack has dropped!' }
		]);
	});

	it('threads effectiveness, crit, and source type into the hurt step', () => {
		const payload = turn({
			events: [
				{ kind: 'move_used', user: 'Hero', move: 'Tap', targets: ['Fodder'] },
				{
					kind: 'damage',
					source: 'Hero',
					target: 'Fodder',
					move: 'Tap',
					amount: 40,
					hp_after: 0,
					is_crit: true,
					effectiveness: 2
				}
			],
			messages: ['Hero used Tap!', 'It dealt 40 damage. A critical hit!']
		});

		const hurt = buildReplayQueue(payload).find((step) => step.kind === 'hurt');
		expect(hurt).toEqual({
			kind: 'hurt',
			side: 'opponent',
			effectiveness: 2,
			crit: true,
			sourceType: 'normal',
			category: 'physical'
		});
	});

	it('routes status damage to the correct side', () => {
		const payload = turn({
			events: [
				{
					kind: 'status_damage',
					source: 'burn',
					target: 'Hero',
					amount: 4,
					hp_after: 28
				}
			],
			messages: ['Hero took 4 status damage.']
		});

		expect(buildReplayQueue(payload)).toEqual([
			{ kind: 'hurt', side: 'player', effectiveness: 1, crit: false },
			{ kind: 'hp', side: 'player', hp: 28 },
			{ kind: 'message', text: 'Hero took 4 status damage.' }
		]);
	});
});

describe('replayStepDelayMs', () => {
	it('returns null for dialog steps and ms for visual beats', () => {
		expect(replayStepDelayMs({ kind: 'message', text: 'Hero used Tap!' })).toBeNull();
		expect(
			replayStepDelayMs({ kind: 'animation', profile: 'physical', actor: 'player', moveType: 'normal' })
		).toBe(220);
		expect(
			replayStepDelayMs({
				kind: 'animation',
				profile: 'special',
				actor: 'opponent',
				moveType: 'normal'
			})
		).toBe(620);
		expect(
			replayStepDelayMs({ kind: 'hurt', side: 'opponent', effectiveness: 2, crit: true })
		).toBe(1050);
		expect(replayStepDelayMs({ kind: 'hp', side: 'player', hp: 32 })).toBe(630);
		expect(replayStepDelayMs({ kind: 'faint', side: 'opponent' })).toBe(720);
	});
});

describe('hpTweenDurationMs', () => {
	it('scales drain time with HP lost and caps big drops', () => {
		expect(hpTweenDurationMs(20, 20)).toBe(0);
		// Chip hit drains far quicker than a big hit...
		const chip = hpTweenDurationMs(100, 96);
		const big = hpTweenDurationMs(100, 10);
		expect(chip).toBeLessThan(big);
		expect(chip).toBe(4 * 45);
		// ...but a huge drop is capped at HP_TWEEN_MAX_STEPS (30) frames.
		expect(big).toBe(30 * 45);
		expect(hpTweenDurationMs(255, 0)).toBeLessThanOrEqual(30 * 45);
		// Direction-agnostic (healing reads the same as damage of equal size).
		expect(hpTweenDurationMs(10, 100)).toBe(big);
	});
});

describe('applyHeroProgression', () => {
	it('updates HUD state without level-up dialog', () => {
		const hero = combatant();

		const dialog = applyHeroProgression(hero, {
			vibemon_id: 'hero-1',
			previous_xp: 120,
			new_xp: 145,
			previous_level: 5,
			new_level: 5,
			xp_to_next: 55,
			xp_bar_ratio: 0.55,
			leveled_up: false
		});

		expect(dialog).toBe('');
		expect(hero.xp).toBe(145);
		expect(hero.level).toBe(5);
		expect(hero.xp_to_next).toBe(55);
		expect(hero.xp_bar_ratio).toBe(0.55);
	});

	it('updates level and returns level-up dialog', () => {
		const hero = combatant();

		const dialog = applyHeroProgression(hero, {
			vibemon_id: 'hero-1',
			previous_xp: 120,
			new_xp: 200,
			previous_level: 5,
			new_level: 6,
			xp_to_next: 90,
			xp_bar_ratio: 0.1,
			leveled_up: true,
			stat_deltas: [
				{ stat: 'hp', previous: 40, new: 43, delta: 3 },
				{ stat: 'attack', previous: 12, new: 13, delta: 1 }
			]
		});

		expect(dialog).toBe('Hero grew to Lv 6!\nHP +3  ATK +1');
		expect(hero.level).toBe(6);
		expect(hero.max_hp).toBe(43);
		expect(hero.current_hp).toBe(43);
	});
});

describe('xpGainedDialogText', () => {
	it('reports how much xp was earned', () => {
		const hero = combatant();
		expect(
			xpGainedDialogText(hero, {
				vibemon_id: 'hero-1',
				previous_xp: 120,
				new_xp: 145,
				previous_level: 5,
				new_level: 5,
				xp_to_next: 55,
				xp_bar_ratio: 0.55,
				leveled_up: false
			})
		).toBe('Hero gained 25 XP!');
	});
});

describe('advanceWonBeat', () => {
	it('advances from xp dialog to level-up dialog', () => {
		const session = createBattleSession('battle-1');
		session.phase = 'won';
		session.state = turn().state;
		session.finishResult = {
			progression: {
				vibemon_id: 'hero-1',
				previous_xp: 120,
				new_xp: 200,
				previous_level: 5,
				new_level: 6,
				xp_to_next: 90,
				xp_bar_ratio: 0.1,
				leveled_up: true,
				stat_deltas: [
					{ stat: 'hp', previous: 40, new: 43, delta: 3 },
					{ stat: 'attack', previous: 12, new: 13, delta: 1 }
				]
			}
		};
		patchHeroProgression(session.state!.player, session.finishResult.progression!);
		session.wonBeat = 'xp';
		session.dialogText = xpGainedDialogText(session.state!.player, session.finishResult.progression!);

		expect(advanceWonBeat(session)).toBe(false);
		expect(session.wonBeat).toBe('levelUp');
		expect(session.dialogText).toBe('Hero grew to Lv 6!\nHP +3  ATK +1');

		expect(advanceWonBeat(session)).toBe(true);
		expect(session.wonBeat).toBe('idle');
	});

	it('enters move learn beat when finish includes offers', () => {
		const session = createBattleSession('battle-1');
		session.phase = 'won';
		session.state = turn().state;
		session.finishResult = {
			progression: null,
			move_offers: [
				{
					vibemon_id: 'hero-1',
					vibemon_name: 'Hero',
					requires_replace: false,
					moves: [
						{
							id: 'climate.learn_a',
							name: 'Learn A',
							type: 'normal',
							category: 'physical',
							power: 40,
							accuracy: 1,
							pp: 20,
							level_requirement: 1,
							flavor_text: ''
						}
					]
				}
			]
		};
		session.wonBeat = 'levelUp';

		expect(advanceWonBeat(session)).toBe(false);
		expect(session.wonBeat).toBe('moveLearnIntro');
		expect(session.dialogText).toBe('Hero is ready to learn a new move.');

		expect(advanceWonBeat(session)).toBe(false);
		expect(session.wonBeat).toBe('moveLearn');
	});

	it('allows leaving after xp dialog when no level-up occurred', () => {
		const session = createBattleSession('battle-1');
		session.phase = 'won';
		session.wonBeat = 'xp';
		session.finishResult = {
			progression: {
				vibemon_id: 'hero-1',
				previous_xp: 120,
				new_xp: 145,
				previous_level: 5,
				new_level: 5,
				xp_to_next: 55,
				xp_bar_ratio: 0.55,
				leveled_up: false
			}
		};

		expect(advanceWonBeat(session)).toBe(true);
		expect(session.wonBeat).toBe('idle');
	});
});

describe('startXpGainAnimation', () => {
	it('completes xp fill and opens the xp dialog', () => {
		const session = createBattleSession('battle-1');
		session.phase = 'won';
		session.state = turn().state;
		session.state.player.xp_bar_ratio = 0.4;
		session.displayXpRatio = 0.4;
		const progression = {
			vibemon_id: 'hero-1',
			previous_xp: 120,
			new_xp: 145,
			previous_level: 5,
			new_level: 5,
			xp_to_next: 55,
			xp_bar_ratio: 0.55,
			leveled_up: false
		};
		session.finishResult = { progression };

		startXpGainAnimation(session, progression);

		expect(session.wonBeat).toBe('animating');

		// Snap the tween to completion.
		expect(advanceWonBeat(session)).toBe(false);
		expect(session.wonBeat).toBe('xp');
		expect(session.dialogText).toBe('Hero gained 25 XP!');
		expect(session.state!.player.xp).toBe(145);
		expect(session.displayXpRatio).toBe(0.55);
	});
});
