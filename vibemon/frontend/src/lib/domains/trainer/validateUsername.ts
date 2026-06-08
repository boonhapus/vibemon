const MIN = 2;

const MAX = 16;

export function validateUsername(value: string): string | null {
	const normalized = value.trim().toLowerCase();

	if (!normalized) {
		return 'Enter a name other Trainers can call you.';
	}

	if (normalized.length < MIN || normalized.length > MAX) {
		return `Use ${MIN}-${MAX} characters.`;
	}

	return null;
}

export function displayUsername(value: string): string {
	return value.trim().toUpperCase();
}
