import { browser } from '$app/environment';

/** True when running on macOS or iOS/iPadOS (Option key maps to Alt in browsers). */
export function isMacOs(): boolean {
	if (!browser) return false;
	return (
		/Mac|iPhone|iPad|iPod/.test(navigator.platform) ||
		navigator.userAgent.includes('Mac')
	);
}
