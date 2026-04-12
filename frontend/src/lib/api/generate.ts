import type { GenerateResponse } from '$lib/types';

export type GenerateRequestBody = {
	user_id: string;
	latitude: number;
	longitude: number;
	auth_tokens?: Record<string, string>;
	timestamp?: string;
	render_assets?: 'none' | 'raster';
};

export class ApiError extends Error {
	constructor(public readonly status: number) {
		super(`HTTP ${status}`);
		this.name = 'ApiError';
	}
}

export async function postGenerate(body: GenerateRequestBody): Promise<GenerateResponse> {
	const res = await fetch('/api/v1/generate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
	if (res.status === 422) {
		throw new ApiError(422);
	}
	if (!res.ok) {
		throw new ApiError(res.status);
	}
	return (await res.json()) as GenerateResponse;
}
