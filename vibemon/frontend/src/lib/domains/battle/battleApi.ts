export type BattleMove = {
	id: string;
	name: string;
	type: string;
	category: 'physical' | 'special' | 'status';
	power: number | null;
	accuracy: number | null;
	pp_current: number;
	pp_max: number;
	effectiveness: number;
	flavor_text: string;
	combat_hints?: string[];
};

export type BattleCombatant = {
	vibemon_id: string;
	name: string;
	types: string[];
	level: number;
	current_hp: number;
	max_hp: number;
	xp: number;
	xp_to_next: number;
	moves: BattleMove[];
	is_fainted: boolean;
	status: string;
	stat_stages: Record<string, number>;
	volatiles: Record<string, number>;
	sprite_url: string | null;
	xp_bar_ratio: number;
};

export type BattleState = {
	battle_id: string;
	turn_number: number;
	concluded: boolean;
	fled: boolean;
	player_trainer_id: string;
	wild_vibemon_id: string;
	player: BattleCombatant;
	opponent: BattleCombatant;
	weather: string;
	winner_trainer_id: string | null;
};

export type TurnEvent = {
	kind: string;
	[key: string]: unknown;
};

export type BattleTurn = {
	events: TurnEvent[];
	messages: string[];
	state: BattleState;
};

export type StatDelta = {
	stat: string;
	previous: number;
	new: number;
	delta: number;
};

export type HeroProgression = {
	vibemon_id: string;
	previous_xp: number;
	new_xp: number;
	previous_level: number;
	new_level: number;
	xp_to_next: number;
	xp_bar_ratio: number;
	leveled_up: boolean;
	stat_deltas?: StatDelta[];
};

export type BattleFinish = {
	progression: HeroProgression | null;
	move_offers?: MoveLearnOffer[];
};

export type MoveLearnOption = {
	id: string;
	name: string;
	type: string;
	category: 'physical' | 'special' | 'status';
	power: number | null;
	accuracy: number | null;
	pp: number;
	level_requirement: number;
	flavor_text: string;
	combat_hints?: string[];
};

export type MoveLearnOffer = {
	vibemon_id: string;
	vibemon_name: string;
	moves: MoveLearnOption[];
	requires_replace: boolean;
};

async function readErrorDetail(payload: unknown): Promise<string | null> {
	if (!payload || typeof payload !== 'object') return null;
	const detail = (payload as { detail?: unknown }).detail;
	return typeof detail === 'string' ? detail : null;
}

export async function fetchBattle(battleId: string): Promise<BattleState> {
	const response = await fetch(`/api/battles/${battleId}`);
	if (!response.ok) {
		const detail = await readErrorDetail(await response.json().catch(() => null));
		throw new Error(detail ?? 'Could not load this battle.');
	}
	return response.json();
}

export async function submitBattleTurn(battleId: string, moveName: string): Promise<BattleTurn> {
	const response = await fetch(`/api/battles/${battleId}/turn`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ move_name: moveName })
	});
	if (!response.ok) {
		const detail = await readErrorDetail(await response.json().catch(() => null));
		throw new Error(detail ?? 'That move could not be used.');
	}
	return response.json();
}

export async function submitBattleRun(battleId: string): Promise<BattleTurn> {
	const response = await fetch(`/api/battles/${battleId}/run`, { method: 'POST' });
	if (!response.ok) {
		const detail = await readErrorDetail(await response.json().catch(() => null));
		throw new Error(detail ?? 'Could not run from battle.');
	}
	return response.json();
}

export async function finishBattle(battleId: string): Promise<BattleFinish> {
	const response = await fetch(`/api/battles/${battleId}/finish`, { method: 'POST' });
	if (!response.ok) {
		const detail = await readErrorDetail(await response.json().catch(() => null));
		throw new Error(detail ?? 'Could not finish battle.');
	}
	return response.json();
}

export async function acceptMoveLearn(
	battleId: string,
	body: { vibemon_id: string; move_content_id: string; replace_content_id?: string }
): Promise<void> {
	const response = await fetch(`/api/battles/${battleId}/move-learn/accept`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	if (!response.ok) {
		const detail = await readErrorDetail(await response.json().catch(() => null));
		throw new Error(detail ?? 'Could not learn that move.');
	}
}

export async function declineMoveLearn(
	battleId: string,
	body: { vibemon_id: string }
): Promise<void> {
	const response = await fetch(`/api/battles/${battleId}/move-learn/decline`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	if (!response.ok) {
		const detail = await readErrorDetail(await response.json().catch(() => null));
		throw new Error(detail ?? 'Could not decline that offer.');
	}
}

export async function startWildBattle(heroVibemonId: string, wildVibemonId: string): Promise<BattleState> {
	const response = await fetch('/api/battles', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ hero_vibemon_id: heroVibemonId, wild_vibemon_id: wildVibemonId })
	});
	if (!response.ok) {
		const detail = await readErrorDetail(await response.json().catch(() => null));
		throw new Error(detail ?? 'Could not start battle.');
	}
	return response.json();
}
