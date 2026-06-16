/** Player copy for hatch review evolution-line facts (VOICE.md §Hatch review panel). */

import type { EvolutionLine } from './hatchApi';

const MORE_EVOLUTIONS: Record<number, string> = {
	1: 'One more evolution',
	2: 'Two more evolutions',
	3: 'Three more evolutions'
};

function moreEvolutionsPhrase(count: number): string {
	return MORE_EVOLUTIONS[count] ?? `${count} more evolutions`;
}

const DEEP_LINE_NOTE =
	'A deep evolution line. Rarer and stronger than most three-stage paths.';

function withDeepLineNote(line: EvolutionLine, text: string): string {
	if (line.line_rarity !== 'deep' || line.form_count < 3) {
		return text;
	}

	return `${text} ${DEEP_LINE_NOTE}`;
}

export function evolutionLineHeader(line: EvolutionLine): string {
	if (line.form_count <= 1) {
		return 'Single-stage';
	}

	return `Stage ${line.form_index} of ${line.form_count}`;
}

export function evolutionLineHint(
	line: EvolutionLine,
	displayName: string,
	evoSeed: number
): string {
	if (evoSeed === 1 || line.form_count <= 1) {
		return `${displayName} has no evolutions ahead.`;
	}

	if (line.form_index >= line.form_count) {
		return withDeepLineNote(line, `${displayName} is fully evolved.`);
	}

	const evolutionsAhead = line.form_count - line.form_index;
	const aheadPhrase = `${moreEvolutionsPhrase(evolutionsAhead)} ahead.`;
	const stagePhrase = `${displayName} is at stage ${line.form_index}. ${aheadPhrase}`;

	return withDeepLineNote(line, stagePhrase);
}
