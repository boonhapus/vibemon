import type { GenerateResponse } from '$lib/types';

class GenerationStore {
	payload = $state<GenerateResponse | null>(null);
}

export const generation = new GenerationStore();
