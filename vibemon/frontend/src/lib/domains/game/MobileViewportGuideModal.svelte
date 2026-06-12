<script lang="ts">
	import GameButton from '$lib/ui/GameButton.svelte';
	import GameModal from '$lib/ui/GameModal.svelte';

	import {
		acknowledgeMobileViewportGuide,
		dismissMobileViewportGuide,
		isFullscreenActive,
		isPortraitOrientation,
		mobileViewportGuideStore,
		requestBrowserFullscreen,
		type FullscreenRequestResult
	} from './mobileViewportGuideStore.svelte';

	let wasOpen = false;
	let fullscreenStatus = $state<FullscreenRequestResult | null>(null);
	let portrait = $derived(isPortraitOrientation());
	let fullscreen = $derived(isFullscreenActive());

	let hintText = $derived.by(() => {
		if (fullscreen) {
			return 'Fullscreen is on. Rotate back to landscape if the field still looks tall.';
		}
		if (portrait) {
			return 'Rotate your phone sideways for the field view, then enter browser fullscreen for the biggest play area.';
		}
		return 'You are already sideways. Enter browser fullscreen for the biggest play area.';
	});

	let fullscreenHint = $derived.by(() => {
		if (fullscreenStatus === 'ok' || fullscreen) {
			return 'Fullscreen is active.';
		}
		if (fullscreenStatus === 'denied') {
			return 'Your browser blocked fullscreen. Try again from the button, or hide Safari\'s bars by scrolling.';
		}
		if (fullscreenStatus === 'unsupported') {
			return 'This browser does not expose fullscreen here. Hide the browser bars by scrolling, or add Vibemon to your Home Screen.';
		}
		return null;
	});

	$effect(() => {
		const open = mobileViewportGuideStore.open;
		if (wasOpen && !open) {
			acknowledgeMobileViewportGuide();
			fullscreenStatus = null;
		}
		wasOpen = open;
	});

	function close() {
		dismissMobileViewportGuide();
	}

	async function handleFullscreen() {
		fullscreenStatus = await requestBrowserFullscreen();
	}
</script>

<GameModal
	bind:open={mobileViewportGuideStore.open}
	ariaLabel="Mobile display tips"
	placement="center"
	panelClass="mobile-viewport-guide__panel"
	width="min(100%, 22rem)"
>
	<div class="mobile-viewport-guide">
		<h2 class="mobile-viewport-guide__title">Widen the field</h2>
		<p class="mobile-viewport-guide__body">{hintText}</p>
		{#if fullscreenHint}
			<p class="mobile-viewport-guide__note">{fullscreenHint}</p>
		{/if}

		<div class="mobile-viewport-guide__actions">
			{#if !fullscreen}
				<GameButton
					variant="primary"
					class="mobile-viewport-guide__action"
					ariaLabel="Enter browser fullscreen"
					onclick={handleFullscreen}
				>
					Enter fullscreen
				</GameButton>
			{/if}
			<GameButton
				variant={fullscreen ? 'primary' : 'secondary'}
				class="mobile-viewport-guide__action"
				ariaLabel="Dismiss display tips"
				onclick={close}
			>
				Got it
			</GameButton>
		</div>
	</div>
</GameModal>

<style>
	:global(.mobile-viewport-guide__panel .game-modal__body) {
		padding: clamp(0.85rem, 2.4vw, 1.15rem);
	}

	.mobile-viewport-guide__title {
		margin: 0 0 0.65rem;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.6875rem, 2.2vw, 0.875rem);
		line-height: 1.5;
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}

	.mobile-viewport-guide__body,
	.mobile-viewport-guide__note {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.625rem, 2vw, 0.8125rem);
		line-height: 1.65;
		letter-spacing: 0.04em;
	}

	.mobile-viewport-guide__note {
		margin-top: 0.65rem;
		color: color-mix(in srgb, currentColor 82%, var(--vm-status-amber));
	}

	.mobile-viewport-guide__actions {
		margin-top: 0.85rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.mobile-viewport-guide__actions :global(.mobile-viewport-guide__action) {
		width: 100%;
		font-size: clamp(0.625rem, 2vw, 0.8125rem);
	}
</style>
