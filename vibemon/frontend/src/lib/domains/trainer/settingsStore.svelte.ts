/** Global settings menu — shared by SceneFrame knob and flow blockers. */

export const settingsStore = $state({
	open: false
});

export function closeSettings() {
	settingsStore.open = false;
}
