<script lang="ts">
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';
	import PixelIcon from '$lib/ui/PixelIcon.svelte';

	const HOVER_CLEAR_MS = 250;

	let {
		actionHint = $bindable<'refresh' | 'adopt' | 'release' | null>(null),
		releaseDisabled = false,
		busy = false,
		embedded = false,
		onRelease,
		onRefresh,
		onAdopt
	}: {
		actionHint?: 'refresh' | 'adopt' | 'release' | null;
		releaseDisabled?: boolean;
		busy?: boolean;
		embedded?: boolean;
		onRelease?: () => void;
		onRefresh?: () => void;
		onAdopt?: () => void;
	} = $props();

	let clearHintTimer: ReturnType<typeof setTimeout> | undefined;

	function cancelHintClear() {
		if (clearHintTimer) {
			clearTimeout(clearHintTimer);
			clearHintTimer = undefined;
		}
	}

	function showHint(kind: 'refresh' | 'adopt' | 'release') {
		cancelHintClear();
		actionHint = kind;
	}

	function clearHint(kind: 'refresh' | 'adopt' | 'release') {
		cancelHintClear();
		clearHintTimer = setTimeout(() => {
			if (actionHint === kind) {
				actionHint = null;
			}
			clearHintTimer = undefined;
		}, HOVER_CLEAR_MS);
	}
</script>

<div class="hatch-controls" class:hatch-controls--embedded={embedded}>
	<FreeFormButton
		class="hatch-controls__button hatch-controls__button--refresh"
		ariaLabel="Refresh this Vibemon"
		disabled={busy}
		onclick={onRefresh}
		onmouseenter={() => showHint('refresh')}
		onmouseleave={() => clearHint('refresh')}
		onfocus={() => showHint('refresh')}
		onblur={() => clearHint('refresh')}
	>
		<PixelIcon name="refresh" class="vm-icon--raised hatch-controls__icon" />
	</FreeFormButton>

	<FreeFormButton
		class="hatch-controls__button hatch-controls__button--adopt"
		ariaLabel="Adopt this Vibemon to your crew"
		disabled={busy}
		onclick={onAdopt}
		onmouseenter={() => showHint('adopt')}
		onmouseleave={() => clearHint('adopt')}
		onfocus={() => showHint('adopt')}
		onblur={() => clearHint('adopt')}
	>
		<PixelIcon name="heart" class="vm-icon--raised hatch-controls__icon" />
	</FreeFormButton>

	<FreeFormButton
		class="hatch-controls__button hatch-controls__button--release"
		ariaLabel="Release this Vibemon"
		disabled={busy || releaseDisabled}
		onclick={onRelease}
		onmouseenter={() => showHint('release')}
		onmouseleave={() => clearHint('release')}
		onfocus={() => showHint('release')}
		onblur={() => clearHint('release')}
	>
		<PixelIcon name="wind" class="vm-icon--raised hatch-controls__icon" />
	</FreeFormButton>
</div>

<style>
	.hatch-controls {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: clamp(0.9rem, 2.6vw, 1.35rem);
		height: calc(var(--vm-hud-icon-slot-height) * 0.62);
	}

	.hatch-controls--embedded {
		height: auto;
		gap: clamp(0.65rem, 2vw, 1rem);
	}

	.hatch-controls--embedded :global(.hatch-controls__button) {
		width: clamp(2.25rem, 6vw, 2.75rem);
		height: clamp(2.25rem, 6vw, 2.75rem);
	}

	:global(.hatch-controls__button) {
		display: grid;
		place-items: center;
		height: 100%;
		width: auto;
		aspect-ratio: 1;
		padding: 0;
		color: currentColor;
	}

	/* Stepped two-frame lift — smooth eased scaling reads modern (DESIGN.md §6.1) */
	:global(.hatch-controls__button:hover:not(:disabled)),
	:global(.hatch-controls__button:focus-visible:not(:disabled)) {
		animation: hatch-controls-lift 240ms steps(2, jump-none) forwards;
	}

	@keyframes hatch-controls-lift {
		from {
			transform: translateY(0);
		}
		to {
			transform: translateY(-3px);
		}
	}

	:global(.hatch-controls__icon) {
		width: calc(100% * 0.72);
		height: calc(100% * 0.72);
		color: currentColor;
		transition: color 120ms ease;
		pointer-events: none;
		user-select: none;
	}

	:global(.hatch-controls__button--refresh:hover:not(:disabled) .hatch-controls__icon),
	:global(.hatch-controls__button--refresh:focus-visible:not(:disabled) .hatch-controls__icon) {
		color: var(--vm-plum);
	}

	:global(.hatch-controls__button--adopt:hover:not(:disabled) .hatch-controls__icon),
	:global(.hatch-controls__button--adopt:focus-visible:not(:disabled) .hatch-controls__icon) {
		color: var(--vm-status-sage);
	}

	:global(.hatch-controls__button--release:hover:not(:disabled) .hatch-controls__icon),
	:global(.hatch-controls__button--release:focus-visible:not(:disabled) .hatch-controls__icon) {
		color: #6e8fa8;
	}
</style>
