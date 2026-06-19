import type { BattleState } from '$lib/domains/battle/battleApi';

export type EncounterSelection = {
	vibemon_id: string;
	weight: number;
};

export type EncounterStartResponse = {
	selection: EncounterSelection;
	battle: BattleState;
};

async function readErrorDetail(payload: unknown): Promise<string | null> {
	if (!payload || typeof payload !== 'object') return null;
	const detail = (payload as { detail?: unknown }).detail;
	return typeof detail === 'string' ? detail : null;
}

export async function startEncounter(heroVibemonId: string): Promise<EncounterStartResponse> {
	const response = await fetch('/api/encounters/start', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ hero_vibemon_id: heroVibemonId })
	});
	if (!response.ok) {
		const detail = await readErrorDetail(await response.json().catch(() => null));
		throw new Error(detail ?? 'No Wild Vibemon are available nearby.');
	}
	return response.json();
}
