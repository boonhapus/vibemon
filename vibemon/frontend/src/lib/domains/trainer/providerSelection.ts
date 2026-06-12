/** Shared provider opt-in state for configuration and hatch flows. */

export type ProviderCoordinates = {
	latitude: number;
	longitude: number;
};

export type ProviderSelectionState = {
	selectedIds: string[];
	warmedIds: string[];
	fetchingIds: string[];
	coordinates: ProviderCoordinates | null;
};

export const PROVIDER_SELECTION_KEY = 'trainer-provider-selection';

export function createProviderSelectionState(
	initial?: Partial<ProviderSelectionState>
): ProviderSelectionState {
	return {
		selectedIds: [...(initial?.selectedIds ?? [])],
		warmedIds: [...(initial?.warmedIds ?? [])],
		fetchingIds: [...(initial?.fetchingIds ?? [])],
		coordinates: initial?.coordinates ?? null
	};
}

export function isProviderSelected(state: ProviderSelectionState, providerId: string): boolean {
	return state.selectedIds.includes(providerId);
}

export function addSelectedProvider(state: ProviderSelectionState, providerId: string): void {
	if (state.selectedIds.includes(providerId)) return;
	state.selectedIds = [...state.selectedIds, providerId];
}

export function removeSelectedProvider(state: ProviderSelectionState, providerId: string): void {
	state.selectedIds = state.selectedIds.filter((value) => value !== providerId);
}

export function setSelectedProviders(state: ProviderSelectionState, providerIds: string[]): void {
	state.selectedIds = [...providerIds];
}

export function markProviderWarmed(state: ProviderSelectionState, providerId: string): void {
	if (state.warmedIds.includes(providerId)) return;
	state.warmedIds = [...state.warmedIds, providerId];
}

export function setProviderFetching(
	state: ProviderSelectionState,
	providerId: string,
	fetching: boolean
): void {
	if (fetching) {
		if (state.fetchingIds.includes(providerId)) return;
		state.fetchingIds = [...state.fetchingIds, providerId];
		return;
	}
	state.fetchingIds = state.fetchingIds.filter((value) => value !== providerId);
}

export function setProviderCoordinates(
	state: ProviderSelectionState,
	coordinates: ProviderCoordinates | null
): void {
	state.coordinates = coordinates;
}

export function applyCandidateProviderIds(
	state: ProviderSelectionState,
	providerIds: string[]
): void {
	if (providerIds.length === 0) return;
	setSelectedProviders(state, providerIds);
	for (const providerId of providerIds) {
		markProviderWarmed(state, providerId);
	}
}
