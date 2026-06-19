export const BATTLE_STAT_SHORT: Record<string, string> = {
	hp: 'HP',
	attack: 'ATK',
	defense: 'DEF',
	sp_attack: 'SPA',
	sp_defense: 'SPD',
	speed: 'SPE'
};

export type StatDelta = {
	stat: string;
	previous: number;
	new: number;
	delta: number;
};

export function formatStatDeltaLine(deltas: StatDelta[]): string {
	return deltas
		.map((entry) => {
			const label = BATTLE_STAT_SHORT[entry.stat] ?? entry.stat.toUpperCase();
			const sign = entry.delta > 0 ? '+' : '';
			return `${label} ${sign}${entry.delta}`;
		})
		.join('  ');
}
