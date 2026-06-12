/** Dev-only URL query overrides for local rehearsal. */

const TRUTHY_QUERY_VALUES = new Set(['', '1', 'true']);

/** Return true when a query flag is present with a truthy value. */
export function readDevQueryFlag(searchParams: URLSearchParams, name: string): boolean {
	const raw = searchParams.get(name);
	if (raw === null) return false;
	return TRUTHY_QUERY_VALUES.has(raw.toLowerCase());
}

export type HatchDevOverrides = {
	bypassCredits: boolean;
};

/** Read dev overrides for the onboarding hatch route from the page URL. */
export function readHatchDevOverrides(searchParams: URLSearchParams): HatchDevOverrides {
	return {
		bypassCredits: readDevQueryFlag(searchParams, 'bypass-credits')
	};
}
