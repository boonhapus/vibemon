/** Player-facing timeline stub until the event ledger ships. */

import type { HatchCandidate } from '$lib/domains/trainer/hatchApi';
import { providerDisplayLabel } from '$lib/domains/trainer/providerLabels';

export type CrewStoryEntry = {
	id: string;
	title: string;
	body: string;
};

export function buildCrewStoryEntries(candidate: HatchCandidate): CrewStoryEntry[] {
	const entries: CrewStoryEntry[] = [];
	const providerLabels = candidate.providers.map(providerDisplayLabel);

	if (providerLabels.length > 0) {
		entries.push({
			id: 'birth',
			title: 'Hatched',
			body:
				providerLabels.length === 1
					? `Shaped by ${providerLabels[0]}.`
					: `Shaped by ${providerLabels.slice(0, -1).join(', ')} and ${providerLabels.at(-1)}.`
		});
	} else {
		entries.push({
			id: 'birth',
			title: 'Hatched',
			body: 'Arrived from the Generation.'
		});
	}

	const adopted = candidate.candidate_review?.resolved_at;
	entries.push({
		id: 'adoption',
		title: 'Joined your crew',
		body: adopted ? 'Welcome them aboard.' : 'Part of your crew now.'
	});

	return entries;
}
