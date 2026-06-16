const TITLE_MON_COUNT = 4;
const FALLBACK_SPRITE = '/game/sprites/hatchling-silhouette@128.png';

export async function fetchTitleMonSprites(): Promise<string[]> {
	try {
		const response = await fetch(`/api/title/mons?count=${TITLE_MON_COUNT}`);
		if (!response.ok) return repeatFallback();
		const payload = (await response.json()) as { mons?: Array<{ reference_url?: string | null }> };
		const urls = (payload.mons ?? [])
			.map((mon) => mon.reference_url)
			.filter((url): url is string => Boolean(url));
		if (urls.length === 0) return repeatFallback();
		while (urls.length < TITLE_MON_COUNT) {
			urls.push(urls[urls.length % urls.length]!);
		}
		return urls.slice(0, TITLE_MON_COUNT);
	} catch {
		return repeatFallback();
	}
}

function repeatFallback(): string[] {
	return Array.from({ length: TITLE_MON_COUNT }, () => FALLBACK_SPRITE);
}
