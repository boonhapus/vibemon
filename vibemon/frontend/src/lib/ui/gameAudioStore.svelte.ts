/** Game SFX playback — DESIGN.md §7.3. Wired when audio assets ship. */

export type GameAudioCue = 'menu-nav' | 'confirm' | 'swap-commit';

export const gameAudioStore = $state({
	muted: false
});

export function playGameAudio(_cue: GameAudioCue): void {
	if (gameAudioStore.muted) return;
}
