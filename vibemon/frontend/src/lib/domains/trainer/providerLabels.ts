import type { PixelIconName } from '$lib/ui/PixelIcon.svelte';

/** Catalog provider id → player-facing label (matches backend display_label). */
export const PROVIDER_DISPLAY_LABELS: Record<string, string> = {
	climate: 'SKY',
	biome: 'GROUND',
	celestial: 'STARS',
	music: 'MUSIC',
	video: 'VIDEO',
	books: 'BOOKS',
	fitness: 'FITNESS'
};

export const PROVIDER_ICONS: Record<string, PixelIconName> = {
	music: 'note',
	climate: 'cloud',
	celestial: 'star',
	biome: 'mountain',
	video: 'screen',
	books: 'book',
	fitness: 'bolt'
};

export function providerDisplayLabel(id: string): string {
	return PROVIDER_DISPLAY_LABELS[id] ?? id.replace(/_/g, ' ').toUpperCase();
}

export function providerIcon(id: string): PixelIconName {
	return PROVIDER_ICONS[id] ?? 'note';
}

/** Stable display order — matches the hatch console patch panel. */
export const PROVIDER_CATALOG_ORDER = [
	'climate',
	'biome',
	'celestial',
	'music',
	'video',
	'books',
	'fitness'
] as const;
