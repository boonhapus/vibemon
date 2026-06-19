export type EffectivenessPhrase = 'Super effective' | 'Not very effective' | 'No effect' | null;

export function effectivenessPhrase(multiplier: number): EffectivenessPhrase {
	if (multiplier === 0) return 'No effect';
	if (multiplier > 1) return 'Super effective';
	if (multiplier < 1) return 'Not very effective';
	return null;
}

export function effectivenessGlyph(multiplier: number): string {
	if (multiplier === 0) return '×';
	if (multiplier > 1) return '▲';
	if (multiplier < 1) return '▼';
	return '●';
}
