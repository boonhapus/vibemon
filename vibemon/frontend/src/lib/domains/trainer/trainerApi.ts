function readErrorDetail(payload: unknown): string | null {
	if (!payload || typeof payload !== 'object') return null;

	const detail = (payload as { detail?: unknown }).detail;

	if (typeof detail === 'string') return detail;

	if (Array.isArray(detail) && detail.length > 0) {
		const first = detail[0];

		if (first && typeof first === 'object' && 'msg' in first) {
			return String((first as { msg: unknown }).msg);
		}
	}

	return null;
}

export type UsernameAvailability =
	| { status: 'available' }
	| { status: 'taken'; message: string }
	| { status: 'invalid'; message: string }
	| { status: 'error'; message: string };

/** Returns whether a trainer name is already registered (case-insensitive). */
export async function checkUsernameAvailability(username: string): Promise<UsernameAvailability> {
	const response = await fetch('/api/trainers/check-username', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ username })
	});

	if (response.status === 422) {
		const payload = await response.json().catch(() => null);
		return {
			status: 'invalid',
			message: readErrorDetail(payload) ?? 'That name will not work.'
		};
	}

	if (!response.ok) {
		return { status: 'error', message: 'Could not check that name. Try again.' };
	}

	const payload = (await response.json()) as { available?: boolean; detail?: string | null };
	if (payload.available) {
		return { status: 'available' };
	}
	return {
		status: 'taken',
		message: payload.detail ?? 'That username is already taken.'
	};
}

/** Ensure a backend session exists for onboarding after username selection. */
export async function ensureTrainerSession(username: string): Promise<boolean> {
	for (const path of ['/api/trainers/login', '/api/trainers/register'] as const) {
		const response = await fetch(path, {
			method: 'POST',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ username })
		});
		if (response.ok) {
			return true;
		}
		if (path === '/api/trainers/login' && response.status === 404) {
			continue;
		}
	}
	return false;
}
