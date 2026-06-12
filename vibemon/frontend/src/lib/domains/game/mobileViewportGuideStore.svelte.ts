import { browser } from '$app/environment';

const DISMISS_KEY = 'vibemon.mobileViewportGuide.dismissed';

export const mobileViewportGuideStore = $state({
	open: false
});

type ShowOptions = {
	/** Bypass mobile detection and session dismiss — for manual buttons and QA. */
	force?: boolean;
};

type FullscreenElement = HTMLElement & {
	webkitRequestFullscreen?: () => Promise<void>;
};

export type FullscreenRequestResult = 'ok' | 'unsupported' | 'denied';

export function isMobileViewport(): boolean {
	if (!browser) return false;
	return (
		window.matchMedia('(hover: none) and (pointer: coarse)').matches ||
		window.matchMedia('(max-width: 48rem)').matches
	);
}

export function isPortraitOrientation(): boolean {
	if (!browser) return false;
	return window.matchMedia('(orientation: portrait)').matches;
}

export function isFullscreenActive(): boolean {
	if (!browser) return false;
	return Boolean(document.fullscreenElement);
}

export async function requestBrowserFullscreen(): Promise<FullscreenRequestResult> {
	if (!browser) return 'unsupported';

	const element = document.documentElement as FullscreenElement;
	const request =
		element.requestFullscreen?.bind(element) ?? element.webkitRequestFullscreen?.bind(element);
	if (!request) return 'unsupported';

	try {
		await request();
	} catch {
		return 'denied';
	}

	try {
		await screen.orientation?.lock?.('landscape-primary');
	} catch {
		// Orientation lock is optional and often blocked outside installed PWAs.
	}

	return 'ok';
}

function wasDismissedThisSession(): boolean {
	if (!browser) return false;
	return sessionStorage.getItem(DISMISS_KEY) === '1';
}

function markDismissedThisSession(): void {
	if (!browser) return;
	sessionStorage.setItem(DISMISS_KEY, '1');
}

/** Open the mobile viewport guide. Use `{ force: true }` to bypass auto-show guards. */
export function showMobileViewportGuide(options: ShowOptions = {}): void {
	if (!browser) return;
	if (!options.force && !isMobileViewport()) return;
	mobileViewportGuideStore.open = true;
}

export function acknowledgeMobileViewportGuide(): void {
	markDismissedThisSession();
}

export function dismissMobileViewportGuide(): void {
	mobileViewportGuideStore.open = false;
}

/** Show once per session on mobile viewports. */
export function maybeAutoShowMobileViewportGuide(): void {
	if (!browser || wasDismissedThisSession() || !isMobileViewport()) return;
	showMobileViewportGuide();
}
