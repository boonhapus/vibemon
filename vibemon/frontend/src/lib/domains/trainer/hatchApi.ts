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
	size_factor: number;
};

export type CandidateReview = {
	id: string;
	trainer_id: string;
	status: string;
	shown_at: string;
	timeout_at: string;
	resolved_at: string | null;
	resolution: string | null;
	status_label: string;
	resolved_label: string | null;
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
	candidate_review?: CandidateReview | null;
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

/** Matches backend `crew.MAX_CREW_SIZE`. */
export const MAX_CREW_SIZE = 6;

export type AdoptEligibility =
	| { eligible: true; current: CandidateAction; needs_swap: boolean }
	| { eligible: false; message: string; current: CandidateAction | null };

export function assessAdoptEligibility(
	current: CandidateAction | null,
	vibemonId: string
): AdoptEligibility {
	if (!current) {
		return {
			eligible: false,
			message: 'No pending Vibemon to adopt.',
			current: null
		};
	}
	if (current.candidate.id !== vibemonId) {
		return {
			eligible: false,
			message: 'Finish reviewing your current Vibemon first.',
			current
		};
	}
	if (current.crew_count >= MAX_CREW_SIZE) {
		return { eligible: true, current, needs_swap: true };
	}
	const review = current.candidate.candidate_review;
	if (!review || review.status !== 'pending') {
		return {
			eligible: false,
			message: 'This Vibemon is no longer available to adopt.',
			current
		};
	}
	if (Date.parse(review.timeout_at) <= Date.now()) {
		return {
			eligible: false,
			message: 'Candidate review has timed out.',
			current
		};
	}
	return { eligible: true, current, needs_swap: false };
}

export async function fetchAdoptEligibility(vibemonId: string): Promise<AdoptEligibility> {
	const current = await fetchCurrentCandidate();
	return assessAdoptEligibility(current, vibemonId);
}

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

export type AdoptCandidateInput = {
	nickname?: string | null;
	releaseVibemonId?: string | null;
};

export async function adoptCandidate(
	vibemonId: string,
	input: AdoptCandidateInput = {}
): Promise<CandidateAction> {
	const response = await fetch(`/api/candidates/${vibemonId}/adopt`, {
		method: 'POST',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			nickname: input.nickname ?? null,
			release_vibemon_id: input.releaseVibemonId ?? null
		})
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
