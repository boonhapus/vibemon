import { validateUsername } from './validateUsername';

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

export type TrainerSession = {
	id: string;
	username: string;
	crew_count: number;
	reference_url: string | null;
	reference_selected_revision: number | null;
	reference_max_revision: number | null;
};

export type TrainerRegistrationResult =
	| { status: 'ok'; session: TrainerSession }
	| { status: 'reference_failed'; message: string; session: TrainerSession }
	| { status: 'session_failed'; message: string };

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

export type TrainerLoginResult =
	| { status: 'ok'; session: TrainerSession }
	| { status: 'not_found'; message: string }
	| { status: 'invalid'; message: string }
	| { status: 'error'; message: string };

async function loginTrainerSession(username: string): Promise<TrainerSession | null> {
	const result = await loginTrainer(username);
	return result.status === 'ok' ? result.session : null;
}

/** Sign in with an existing trainer username and return the session payload. */
export async function loginTrainer(username: string): Promise<TrainerLoginResult> {
	const validationError = validateUsername(username);
	if (validationError) {
		return { status: 'invalid', message: validationError };
	}

	let response: Response;
	try {
		response = await fetch('/api/trainers/login', {
			method: 'POST',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ username: username.trim() })
		});
	} catch {
		return { status: 'error', message: 'Could not reach the server. Check your connection and try again.' };
	}

	if (response.status === 404) {
		return {
			status: 'not_found',
			message: readErrorDetail(await response.json().catch(() => null)) ?? 'No Trainer found with that name.'
		};
	}

	if (!response.ok) {
		return { status: 'error', message: 'Could not sign in. Try again.' };
	}

	return { status: 'ok', session: (await response.json()) as TrainerSession };
}

async function registerTrainerSession(username: string): Promise<TrainerSession | null> {
	const response = await fetch('/api/trainers/register', {
		method: 'POST',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ username })
	});
	if (response.ok) {
		return (await response.json()) as TrainerSession;
	}
	if (response.status === 409) {
		return loginTrainerSession(username);
	}
	return null;
}

function referenceUploadFailureMessage(status: number, detail: string | null): string {
	if (detail) return detail;
	if (status === 401) return 'Sign in first, then try the camera again.';
	if (status === 413) return 'That photo is too large. Use an image under 10 MB.';
	if (status >= 500) return 'Something went wrong while generating your look. Try again.';
	return 'Could not upload your reference. Try again.';
}

export type TrainerReferenceFileUploadResult =
	| { status: 'ok'; session: TrainerSession }
	| { status: 'failed'; message: string };

export type TrainerReferenceUploadResult =
	| { status: 'ok'; session: TrainerSession }
	| { status: 'needs_username'; message: string }
	| { status: 'session_failed'; message: string }
	| { status: 'reference_failed'; message: string; session: TrainerSession };

function sessionMatchesUsername(session: TrainerSession, username: string): boolean {
	return session.username.toLowerCase() === username.trim().toLowerCase();
}

/** Ensure a trainer session exists, then generate a styled reference from a likeness photo. */
export async function uploadTrainerReferenceWithSession(
	file: File,
	username: string
): Promise<TrainerReferenceUploadResult> {
	const validationError = validateUsername(username);
	if (validationError) {
		return { status: 'needs_username', message: validationError };
	}

	const trimmed = username.trim();
	let session = await fetchTrainerMe();
	if (session && !sessionMatchesUsername(session, trimmed)) {
		session = null;
	}

	if (!session) {
		session = await registerTrainerSession(trimmed);
		if (!session) {
			return {
				status: 'session_failed',
				message: 'Could not create your trainer. Try again.'
			};
		}
	}

	const withReference = await uploadTrainerReference(file);
	if (withReference.status === 'failed') {
		return {
			status: 'reference_failed',
			message: withReference.message,
			session
		};
	}

	return { status: 'ok', session: withReference.session };
}

/** Upload a likeness photo and generate a styled trainer reference (session required). */
export async function uploadTrainerReference(file: File): Promise<TrainerReferenceFileUploadResult> {
	const formData = new FormData();
	formData.append('image', file);

	let response: Response;
	try {
		response = await fetch('/api/trainers/reference', {
			method: 'POST',
			body: formData,
			credentials: 'include'
		});
	} catch {
		return {
			status: 'failed',
			message: 'Could not reach the server. Check your connection and try again.'
		};
	}

	if (!response.ok) {
		const payload = await response.json().catch(() => null);
		return {
			status: 'failed',
			message: referenceUploadFailureMessage(response.status, readErrorDetail(payload))
		};
	}

	return { status: 'ok', session: (await response.json()) as TrainerSession };
}

/** Return the signed-in trainer, if any. */
export async function fetchTrainerMe(): Promise<TrainerSession | null> {
	const response = await fetch('/api/trainers/me', { credentials: 'include' });
	if (!response.ok) {
		return null;
	}
	return (await response.json()) as TrainerSession;
}

/** Clear the server session cookie. */
export async function logoutTrainer(): Promise<boolean> {
	const response = await fetch('/api/trainers/logout', {
		method: 'POST',
		credentials: 'include'
	});
	return response.ok;
}

/**
 * Create the trainer account and optionally generate a reference from a pending photo.
 * GenAI + storage require a session, so reference generation runs after register.
 */
export async function finalizeTrainerRegistration(
	username: string,
	referenceFile?: File | null
): Promise<TrainerRegistrationResult> {
	const trimmed = username.trim();
	let session = await fetchTrainerMe();
	if (session && !sessionMatchesUsername(session, trimmed)) {
		session = null;
	}

	if (!session) {
		session = await registerTrainerSession(trimmed);
		if (!session) {
			return { status: 'session_failed', message: 'Could not create your trainer. Try again.' };
		}
	}

	if (!referenceFile) {
		return { status: 'ok', session };
	}

	const withReference = await uploadTrainerReference(referenceFile);
	if (withReference.status === 'failed') {
		return {
			status: 'reference_failed',
			message: withReference.message,
			session
		};
	}

	return { status: 'ok', session: withReference.session };
}

/** Sign in or register, returning the trainer session payload from the response. */
export async function ensureTrainerSession(username: string): Promise<TrainerSession | null> {
	const loggedIn = await loginTrainerSession(username);
	if (loggedIn) return loggedIn;
	return registerTrainerSession(username);
}

/** Return an authenticated trainer session for onboarding, reusing an existing cookie when possible. */
export async function resolveTrainerSession(username: string): Promise<TrainerSession | null> {
	const trimmed = username.trim();
	const existing = await fetchTrainerMe();
	if (existing && sessionMatchesUsername(existing, trimmed)) {
		return existing;
	}
	return ensureTrainerSession(trimmed);
}
