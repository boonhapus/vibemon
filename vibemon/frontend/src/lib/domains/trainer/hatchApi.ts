/** Hatch / candidate review API types and helpers. */

export type BaseStats = {
	hp: number;
	attack: number;
	defense: number;
	sp_attack: number;
	sp_defense: number;
	speed: number;
	total: number;
};

export type MoveSummary = {
	name: string;
	element: string;
	category: string;
	power: number | null;
	pp: number;
	flavor_text: string;
	accuracy?: number | null;
	priority?: number;
	combat_hints?: string[];
};

export type EvolutionLine = {
	form_index: number;
	form_count: number;
	line_rarity: 'normal' | 'deep';
};

export type CandidateDisplay = {
	anchor_x: number | null;
	baseline_y: number | null;
	size_class: 'small' | 'mid' | 'large';
};

export type HatchCandidate = {
	id: string;
	name: string;
	nickname: string | null;
	elements: string[];
	base_stats: BaseStats;
	bst: number;
	power_pips: number;
	is_radiant: boolean;
	evo_seed: number;
	evolution_line: EvolutionLine;
	moves: MoveSummary[];
	display: CandidateDisplay;
	lifecycle: string;
	reference_url: string | null;
	/** Audit-only; display PNGs are oriented screen-left at generation time. */
	reference_facing: 'left' | 'right';
	providers: string[];
};

export type CandidateAction = {
	candidate: HatchCandidate;
	crew_count: number;
};

export type SpriteFacing = 'LEFT' | 'CENTER' | 'RIGHT';

export type CrewMember = {
	id: string;
	name: string;
	nickname: string | null;
	level: number;
	current_hp: number;
	max_hp: number;
	crew_slot: number;
	sprite_url: string | null;
	reference_detected_facing: SpriteFacing | null;
	detail: HatchCandidate;
};

export type CrewList = {
	members: CrewMember[];
	max_size: number;
};

function readErrorDetail(payload: unknown): string | null {
	if (!payload || typeof payload !== 'object') return null;
	const detail = (payload as { detail?: unknown }).detail;
	return typeof detail === 'string' ? detail : null;
}

export async function fetchCurrentCandidate(): Promise<CandidateAction | null> {
	const response = await fetch('/api/candidates/current', { credentials: 'include' });
	if (response.status === 404 || response.status === 204) return null;
	if (!response.ok) {
		throw new Error('Could not load your current Vibemon.');
	}
	const payload = await response.json();
	return payload ?? null;
}

export async function generateCandidate(input: {
	providers: string[];
	latitude?: number | null;
	longitude?: number | null;
	bypassCredits?: boolean;
}): Promise<CandidateAction> {
	const params = new URLSearchParams();
	if (input.bypassCredits) {
		params.set('bypass-credits', 'true');
	}
	const query = params.toString();
	const response = await fetch(`/api/candidates/generate${query ? `?${query}` : ''}`, {
		method: 'POST',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			providers: input.providers,
			latitude: input.latitude ?? null,
			longitude: input.longitude ?? null
		})
	});
	if (!response.ok) {
		const payload = await response.json().catch(() => null);
		throw new Error(readErrorDetail(payload) ?? 'Could not hatch a Vibemon.');
	}
	return (await response.json()) as CandidateAction;
}

export async function refreshCandidate(vibemonId: string): Promise<CandidateAction> {
	const response = await fetch(`/api/candidates/${vibemonId}/refresh`, {
		method: 'POST',
		credentials: 'include'
	});
	if (!response.ok) {
		const payload = await response.json().catch(() => null);
		throw new Error(readErrorDetail(payload) ?? 'Could not refresh this Vibemon.');
	}
	return (await response.json()) as CandidateAction;
}

export async function rejectCandidate(vibemonId: string): Promise<void> {
	const response = await fetch(`/api/candidates/${vibemonId}/reject`, {
		method: 'POST',
		credentials: 'include'
	});
	if (!response.ok) {
		const payload = await response.json().catch(() => null);
		throw new Error(readErrorDetail(payload) ?? 'Could not release this Vibemon.');
	}
}

export async function adoptCandidate(vibemonId: string, nickname?: string | null): Promise<CandidateAction> {
	const response = await fetch(`/api/candidates/${vibemonId}/adopt`, {
		method: 'POST',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ nickname: nickname ?? null })
	});
	if (!response.ok) {
		const payload = await response.json().catch(() => null);
		throw new Error(readErrorDetail(payload) ?? 'Could not adopt this Vibemon.');
	}
	return (await response.json()) as CandidateAction;
}

export async function fetchCrew(): Promise<CrewList> {
	const response = await fetch('/api/trainers/crew', { credentials: 'include' });
	if (!response.ok) {
		throw new Error('Could not load your crew.');
	}
	return (await response.json()) as CrewList;
}

export type CrewSlotAssignment = {
	id: string;
	crew_slot: number;
};

/** Persist a full crew_slot assignment (every owned mon exactly once). */
export async function reorderCrew(members: CrewSlotAssignment[]): Promise<CrewList> {
	const response = await fetch('/api/trainers/crew/order', {
		method: 'PUT',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ members })
	});
	if (!response.ok) {
		const payload = await response.json().catch(() => null);
		throw new Error(readErrorDetail(payload) ?? 'Could not save your crew order.');
	}
	return (await response.json()) as CrewList;
}

export function candidateDisplayName(candidate: HatchCandidate): string {
	return candidate.nickname?.trim() || candidate.name;
}
