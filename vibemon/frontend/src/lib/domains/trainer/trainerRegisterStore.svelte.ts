import { browser } from '$app/environment';

const STORAGE_KEY = 'vibemon.pendingUsername';

export const trainerRegisterStore = $state<{ username: string | null }>({ username: null });

export function setPendingUsername(username: string) {
	const normalized = username.trim();
	trainerRegisterStore.username = normalized;
	if (browser) {
		sessionStorage.setItem(STORAGE_KEY, normalized);
	}
}

export function readPendingUsername(): string | null {
	if (trainerRegisterStore.username) return trainerRegisterStore.username;
	if (browser) {
		trainerRegisterStore.username = sessionStorage.getItem(STORAGE_KEY);
	}
	return trainerRegisterStore.username;
}

export function clearPendingUsername() {
	trainerRegisterStore.username = null;
	if (browser) {
		sessionStorage.removeItem(STORAGE_KEY);
	}
}
