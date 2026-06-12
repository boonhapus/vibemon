const DISMISS_MS = 4200;

export type GameToastStatus = 'sage' | 'amber' | 'brick';

export const toastStore = $state<{ message: string | null; status: GameToastStatus }>({
	message: null,
	status: 'amber'
});

let timer: ReturnType<typeof setTimeout> | undefined;

export function showGameToast(text: string, status: GameToastStatus = 'amber') {
	toastStore.message = text;
	toastStore.status = status;
	if (timer) clearTimeout(timer);
	timer = setTimeout(() => {
		toastStore.message = null;
		timer = undefined;
	}, DISMISS_MS);
}

export function dismissGameToast() {
	if (timer) clearTimeout(timer);
	timer = undefined;
	toastStore.message = null;
}
