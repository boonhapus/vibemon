import type { GenerateResponse } from '$lib/types';

class GenerationStore {
	payload = $state<GenerateResponse | null>(null);
	spotifyToken = $state<string | null>(null);
	spotifyExpiresAt = $state<number | null>(null);

	get spotifyConnected(): boolean {
		return this.spotifyToken !== null && !this.spotifyExpired;
	}

	get spotifyExpired(): boolean {
		if (!this.spotifyExpiresAt) return true;
		return Date.now() >= this.spotifyExpiresAt;
	}

	clearSpotify(): void {
		this.spotifyToken = null;
		this.spotifyExpiresAt = null;
	}
}

export const generation = new GenerationStore();
