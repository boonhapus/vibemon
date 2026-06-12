/** Player copy for hatch review evolution-line facts (ui-cohesion-plan §5). */

import type { EvolutionLine } from './hatchApi';

const MORE_EVOLUTIONS: Record<number, string> = {
	1: 'one more evolution',
	2: 'two more evolutions',
	3: 'three more evolutions'
};

function moreEvolutionsPhrase(count: number): string {
	return MORE_EVOLUTIONS[count] ?? `${count} more evolutions`;
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
		return `${displayName} has no evolutions!`;
	}

	if (line.form_index >= line.form_count) {
		return `${displayName} is fully evolved!`;
	}

	const evolutionsAhead = line.form_count - line.form_index;
	const moreEvolutions = moreEvolutionsPhrase(evolutionsAhead);

	if (line.form_index === 1) {
		return `${displayName} is in its base form — with ${moreEvolutions}!`;
	}

	return `${displayName} has ${moreEvolutions}!`;
}
