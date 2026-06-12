/** Provider catalog types and API helpers. */

export type RequirementKind = 'geolocation' | 'trainer_secrets' | 'oauth2_link' | 'secret_group';
export type RequirementStatus = 'satisfied' | 'missing' | 'unavailable';

export type DataSourceInfo = {
	name: string;
	description: string;
};

export type ProviderElement = {
	type: string;
	signal: string;
};

export type GeolocationRequirement = {
	kind: 'geolocation';
	id: string;
	label: string;
	description: string;
};

export type TrainerSecretsRequirement = {
	kind: 'trainer_secrets';
	id: string;
	label: string;
	description: string;
	secret_kinds: string[];
};

export type OAuth2LinkRequirement = {
	kind: 'oauth2_link';
	id: string;
	label: string;
	description: string;
	service: string;
	secret_kinds: string[];
	authorize_path: string;
};

export type SecretGroupRequirement = {
	kind: 'secret_group';
	id: string;
	label: string;
	description: string;
	branches: (TrainerSecretsRequirement | OAuth2LinkRequirement)[];
};

export type ProviderRequirement =
	| GeolocationRequirement
	| TrainerSecretsRequirement
	| OAuth2LinkRequirement
	| SecretGroupRequirement;

export type ProviderCatalogEntry = {
	id: string;
	label: string;
	tagline: string;
	lore: string[];
	data_sources: DataSourceInfo[];
	elements: ProviderElement[];
	requirements: ProviderRequirement[];
	implemented: boolean;
};

export type RequirementStatusEntry = {
	status: RequirementStatus;
	authorize_url?: string | null;
};

export type ProviderStatusEntry = {
	id: string;
	ready: boolean;
	requirements: Record<string, RequirementStatusEntry>;
	prefetched_at?: string | null;
};

export async function fetchProviderCatalog(): Promise<ProviderCatalogEntry[]> {
	const response = await fetch('/api/providers/');
	if (!response.ok) {
		throw new Error('Could not load provider catalog.');
	}
	const payload = (await response.json()) as { providers: ProviderCatalogEntry[] };
	return payload.providers;
}

export async function fetchProviderStatus(
	coords?: { latitude: number; longitude: number } | null
): Promise<ProviderStatusEntry[]> {
	const params = new URLSearchParams();
	if (coords) {
		params.set('latitude', String(coords.latitude));
		params.set('longitude', String(coords.longitude));
	}
	const query = params.toString();
	const response = await fetch(`/api/providers/status${query ? `?${query}` : ''}`, {
		credentials: 'include'
	});
	if (!response.ok) {
		throw new Error('Could not load provider status.');
	}
	const payload = (await response.json()) as { providers: ProviderStatusEntry[] };
	return payload.providers;
}

export async function prefetchProvider(
	providerId: string,
	options: { latitude?: number; longitude?: number; forceRefresh?: boolean } = {}
): Promise<{ prefetched_at: string }> {
	const response = await fetch(`/api/providers/${providerId}/prefetch`, {
		method: 'POST',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			latitude: options.latitude ?? null,
			longitude: options.longitude ?? null,
			force_refresh: options.forceRefresh ?? false
		})
	});
	if (!response.ok) {
		const payload = await response.json().catch(() => null);
		const detail =
			payload && typeof payload === 'object' && 'detail' in payload
				? String((payload as { detail: unknown }).detail)
				: 'Prefetch failed.';
		throw new Error(detail);
	}
	const payload = (await response.json()) as { prefetched_at: string };
	return { prefetched_at: payload.prefetched_at };
}

export function requirementNeedsGeolocation(requirements: ProviderRequirement[]): boolean {
	return requirements.some((requirement) => requirement.kind === 'geolocation');
}

export function isProviderReady(
	entry: ProviderCatalogEntry,
	status: ProviderStatusEntry | undefined,
	locationGranted: boolean
): boolean {
	if (!entry.implemented) return false;
	for (const requirement of entry.requirements) {
		if (requirement.kind === 'geolocation') {
			if (!locationGranted) return false;
			continue;
		}
		const requirementStatus = status?.requirements[requirement.id]?.status;
		if (requirementStatus !== 'satisfied') return false;
	}
	return true;
}
