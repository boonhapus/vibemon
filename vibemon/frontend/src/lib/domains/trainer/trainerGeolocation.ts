/** Restore trainer onboarding coordinates across reloads when geolocation is already granted. */

export type TrainerCoordinates = {
	latitude: number;
	longitude: number;
};

const STORAGE_KEY = 'vibemon:onboarding-coordinates';

export function readStoredTrainerCoordinates(): TrainerCoordinates | null {
	if (typeof sessionStorage === 'undefined') return null;
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw) as TrainerCoordinates;
		if (
			typeof parsed.latitude !== 'number' ||
			typeof parsed.longitude !== 'number' ||
			!Number.isFinite(parsed.latitude) ||
			!Number.isFinite(parsed.longitude)
		) {
			return null;
		}
		return parsed;
	} catch {
		return null;
	}
}

export function storeTrainerCoordinates(coords: TrainerCoordinates) {
	if (typeof sessionStorage === 'undefined') return;
	sessionStorage.setItem(STORAGE_KEY, JSON.stringify(coords));
}

export function clearStoredTrainerCoordinates() {
	if (typeof sessionStorage === 'undefined') return;
	sessionStorage.removeItem(STORAGE_KEY);
}

export async function geolocationPermissionGranted(): Promise<boolean> {
	if (typeof navigator === 'undefined' || !('geolocation' in navigator)) return false;
	if (!('permissions' in navigator)) return true;
	try {
		const status = await navigator.permissions.query({ name: 'geolocation' });
		return status.state === 'granted';
	} catch {
		return true;
	}
}

export function readCurrentPosition(
	options: PositionOptions = { enableHighAccuracy: true, timeout: 12_000, maximumAge: 300_000 }
): Promise<TrainerCoordinates> {
	return new Promise((resolve, reject) => {
		navigator.geolocation.getCurrentPosition(
			(position) => {
				resolve({
					latitude: position.coords.latitude,
					longitude: position.coords.longitude
				});
			},
			reject,
			options
		);
	});
}

export async function restoreTrainerCoordinates(): Promise<TrainerCoordinates | null> {
	if (typeof navigator === 'undefined' || !('geolocation' in navigator)) return null;

	const stored = readStoredTrainerCoordinates();
	if (!(await geolocationPermissionGranted())) {
		return stored;
	}

	try {
		const coords = await readCurrentPosition();
		storeTrainerCoordinates(coords);
		return coords;
	} catch {
		return stored;
	}
}
