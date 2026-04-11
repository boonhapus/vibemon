export type Hsl = [number, number, number];

export interface VibemonStats {
	hp: number;
	attack: number;
	defense: number;
	sp_attack: number;
	sp_defense: number;
	speed: number;
	element: string;
	element_secondary: string | null;
}

export interface Move {
	name: string;
	type: string;
	category: string;
	power: number;
	accuracy: number;
	is_signature: boolean;
	effect: string | null;
}

export interface VisualDNA {
	n_points: number;
	spikiness: number;
	limb_count: number;
	limb_style: string;
	eye_count: number;
	eye_size: number;
	eye_shape: string;
	mouth_style: string;
	texture_pattern: string;
	color_primary: Hsl;
	color_secondary: Hsl;
	color_accent: Hsl;
	color_eye: Hsl;
	outline_weight: number;
	glow_intensity: number;
	size_scale: number;
	animation_speed: number;
}

export interface VibemonPayload {
	uid: string;
	name: string;
	source: string;
	stats: VibemonStats;
	moves: Move[];
	visual_dna: VisualDNA;
	flavour_text: string;
	stat_origins: Record<string, string>;
	fallback: boolean;
}

export interface GenerateResponse {
	player: VibemonPayload;
	enemy: VibemonPayload;
}
