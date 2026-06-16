/** Vibemon type colors — docs/development/COLORS.md */

export const ELEMENT_TYPES = [
	'normal',
	'fire',
	'water',
	'electric',
	'grass',
	'ice',
	'fighting',
	'poison',
	'ground',
	'flying',
	'psychic',
	'bug',
	'rock',
	'ghost',
	'dragon',
	'dark',
	'steel',
	'fairy'
] as const;

const TYPE_COLOR_HEX: Record<string, string> = {
	normal: '#c4a882',
	fire: '#c0542a',
	water: '#3d8c8c',
	electric: '#d4a017',
	grass: '#6b7a2a',
	ice: '#a0bac8',
	fighting: '#8b3a2a',
	poison: '#7c4d8a',
	ground: '#a0784a',
	flying: '#6e8fa8',
	psychic: '#b0607a',
	bug: '#7a8c2a',
	rock: '#8c7a5a',
	ghost: '#524870',
	dragon: '#2a5c58',
	dark: '#4a3428',
	steel: '#8a8c8e',
	fairy: '#c4909a'
};

function relativeLuminance(hex: string): number {
	const value = hex.replace('#', '');
	const red = Number.parseInt(value.slice(0, 2), 16);
	const green = Number.parseInt(value.slice(2, 4), 16);
	const blue = Number.parseInt(value.slice(4, 6), 16);
	return (0.299 * red + 0.587 * green + 0.114 * blue) / 255;
}

export function normalizeElementType(type: string): string {
	return type.trim().toLowerCase();
}

export function elementTypeColor(type: string): string {
	const normalized = normalizeElementType(type);
	return TYPE_COLOR_HEX[normalized] ?? '#3d2b1f';
}

export function elementBadgeTextColor(type: string): string {
	return relativeLuminance(elementTypeColor(type)) > 0.55 ? '#3d2b1f' : '#f0e7ce';
}

export function elementTypeLabel(type: string): string {
	return normalizeElementType(type).toUpperCase();
}
