<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { setContext, type Snippet } from 'svelte';
	import { prefersReducedMotion } from 'svelte/motion';

	import HatchlingSilhouette from '$lib/domains/trainer/HatchlingSilhouette.svelte';
	import ProviderConfigModal from '$lib/domains/trainer/ProviderConfigModal.svelte';
	import { providerConfigModalStore } from '$lib/domains/trainer/providerConfigModalStore.svelte';
	import SettingsModal from '$lib/domains/trainer/SettingsModal.svelte';
	import TrainerPortrait from '$lib/domains/trainer/TrainerPortrait.svelte';
	import TrainerPortraitCamera from '$lib/domains/trainer/TrainerPortraitCamera.svelte';
	import GameToast from '$lib/ui/GameToast.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';

	const ONBOARDING_UI_KEY = 'trainer-onboarding-ui';

	let { children }: { children: Snippet } = $props();

	let onboardingUi = $state({
		portraitHintVisible: false,
		hatchHintVisible: false,
		settingsOpen: false
	});
	setContext(ONBOARDING_UI_KEY, onboardingUi);

	let isRegister = $derived(page.url.pathname.endsWith('/register'));
	let isHatch = $derived(page.url.pathname.endsWith('/hatch'));
	let crossing = $state<'none' | 'forward' | 'back'>('none');

	// The facing flip is driven entirely in CSS (swapped at the wipe's pinch),
	// so the resting orientation only needs to follow the active route.
	let mirrored = $derived(isHatch);

	afterNavigate(({ from, to }) => {
		const fromRegister = from?.url.pathname.endsWith('/register');
		const toHatch = to?.url.pathname.endsWith('/hatch');
		const fromHatch = from?.url.pathname.endsWith('/hatch');
		const toRegister = to?.url.pathname.endsWith('/register');

		if (fromRegister && toHatch) {
			crossing = 'forward';
			return;
		}
		if (fromHatch && toRegister) {
			crossing = 'back';
			return;
		}
		crossing = 'none';
		if (!to?.url.pathname.endsWith('/hatch')) {
			onboardingUi.settingsOpen = false;
			providerConfigModalStore.open = false;
			providerConfigModalStore.entry = null;
		}
	});

	let portraitClass = $derived(
		[
			'trainer-onboarding__portrait',
			crossing === 'forward' && 'trainer-onboarding__portrait--cross-forward',
			crossing === 'back' && 'trainer-onboarding__portrait--cross-back',
			crossing === 'none' && isRegister && 'trainer-onboarding__portrait--register',
			crossing === 'none' && isHatch && 'trainer-onboarding__portrait--hatch'
		]
			.filter(Boolean)
			.join(' ')
	);

	function finishCross() {
		crossing = 'none';
	}

	function handlePortraitAnimationEnd(event: AnimationEvent) {
		if (event.animationName === 'trainer-onboarding-platform-in') {
			finishCross();
			return;
		}

		if (
			prefersReducedMotion.current &&
			(event.animationName === 'trainer-onboarding-slide-forward' ||
				event.animationName === 'trainer-onboarding-slide-back')
		) {
			finishCross();
		}
	}
</script>

<GameToast />

<SceneFrame>
	<div class="trainer-onboarding">
		<div class={portraitClass} onanimationend={handlePortraitAnimationEnd} aria-hidden="true">
			<div class="trainer-onboarding__portrait-stage">
				<TrainerPortrait {mirrored} />
				{#if isRegister}
					<TrainerPortraitCamera bind:hovered={onboardingUi.portraitHintVisible} />
				{/if}
			</div>
		</div>

		{#if isHatch}
			<div class="trainer-onboarding__hatchling">
				<HatchlingSilhouette
					bind:hovered={onboardingUi.hatchHintVisible}
					disabled={onboardingUi.settingsOpen || providerConfigModalStore.open}
				/>
			</div>
		{/if}

		<div class="trainer-onboarding__content">
			{#key page.url.pathname}
				<div class="trainer-onboarding__page">
					{@render children()}
				</div>
			{/key}
		</div>

		{#if isHatch}
			<SettingsModal bind:open={onboardingUi.settingsOpen} />
			<ProviderConfigModal />
		{/if}
	</div>
</SceneFrame>

<style>
	@property --platform-strength {
		syntax: '<number>';
		inherits: true;
		initial-value: 1;
	}

	.trainer-onboarding {
		--onboarding-cross-duration: var(--anim-onboarding-cross-duration);
		--onboarding-transition-timing: steps(var(--anim-transition-steps), end);
		--onboarding-action-timing: steps(var(--anim-action-steps), end);
		--onboarding-ui-timing: steps(var(--anim-ui-reveal-steps), end);
		--onboarding-ring-timing: steps(4, end);
		--onboarding-ring-out-duration: 55ms;
		--onboarding-ring-in-duration: 140ms;
		--onboarding-move-delay: var(--onboarding-ring-out-duration);
		--onboarding-move-duration: calc(
			var(--onboarding-cross-duration) - var(--onboarding-move-delay) - var(--onboarding-ring-in-duration)
		);
		--onboarding-ring-in-delay: calc(var(--onboarding-move-delay) + var(--onboarding-move-duration));
		/* Horizontal travel distance: 70% - 30% of the full-bleed scene == 40vw. */
		--onboarding-cross-shift: 40vw;

		position: relative;
		min-height: 100dvh;
	}

	.trainer-onboarding__portrait {
		position: absolute;
		bottom: clamp(12rem, 23vh, 14.5rem);
		z-index: 1;
		transform: translateX(-50%);
		pointer-events: auto;
	}

	.trainer-onboarding__portrait-stage {
		position: relative;
	}

	.trainer-onboarding__hatchling {
		position: absolute;
		left: 65%;
		bottom: clamp(12rem, 23vh, 14.5rem);
		transform: translateX(-50%);
		z-index: 1;
		pointer-events: auto;
	}

	.trainer-onboarding__portrait--register {
		left: 70%;
	}

	.trainer-onboarding__portrait--hatch {
		left: 30%;
	}

	.trainer-onboarding__portrait--cross-forward {
		left: 70%;
		will-change: transform;
		animation: trainer-onboarding-slide-forward var(--onboarding-move-duration) var(--onboarding-transition-timing)
			var(--onboarding-move-delay) forwards;
	}

	.trainer-onboarding__portrait--cross-back {
		left: 30%;
		will-change: transform;
		animation: trainer-onboarding-slide-back var(--onboarding-move-duration) var(--onboarding-transition-timing)
			var(--onboarding-move-delay) forwards;
	}

	.trainer-onboarding__portrait--cross-forward .trainer-onboarding__portrait-stage {
		will-change: transform;
		animation: trainer-onboarding-travel-forward var(--onboarding-move-duration) var(--onboarding-action-timing)
			var(--onboarding-move-delay) forwards;
	}

	.trainer-onboarding__portrait--cross-back .trainer-onboarding__portrait-stage {
		will-change: transform;
		animation: trainer-onboarding-travel-back var(--onboarding-move-duration) var(--onboarding-action-timing)
			var(--onboarding-move-delay) forwards;
	}

	.trainer-onboarding__portrait--cross-forward :global(.trainer-portrait__sprite) {
		will-change: clip-path, transform;
		animation: trainer-onboarding-sprite-forward var(--onboarding-move-duration) var(--onboarding-transition-timing)
			var(--onboarding-move-delay) both;
	}

	.trainer-onboarding__portrait--cross-back :global(.trainer-portrait__sprite) {
		will-change: clip-path, transform;
		animation: trainer-onboarding-sprite-back var(--onboarding-move-duration) var(--onboarding-transition-timing)
			var(--onboarding-move-delay) both;
	}

	.trainer-onboarding__portrait--cross-forward :global(.trainer-portrait),
	.trainer-onboarding__portrait--cross-back :global(.trainer-portrait) {
		animation:
			trainer-onboarding-platform-out var(--onboarding-ring-out-duration) var(--onboarding-ring-timing) forwards,
			trainer-onboarding-platform-in var(--onboarding-ring-in-duration) var(--onboarding-ring-timing)
				var(--onboarding-ring-in-delay) forwards;
	}

	.trainer-onboarding__content {
		position: relative;
		z-index: 2;
		min-height: 100dvh;
		pointer-events: none;
	}

	.trainer-onboarding__page {
		position: relative;
		min-height: 100dvh;
		pointer-events: none;
		animation: trainer-onboarding-page-in 480ms var(--onboarding-ui-timing)
			calc(var(--onboarding-cross-duration) * 0.42) both;
	}

	@keyframes trainer-onboarding-slide-forward {
		from {
			transform: translateX(-50%);
		}
		to {
			transform: translateX(-50%) translateX(calc(-1 * var(--onboarding-cross-shift)));
		}
	}

	@keyframes trainer-onboarding-slide-back {
		from {
			transform: translateX(-50%);
		}
		to {
			transform: translateX(-50%) translateX(var(--onboarding-cross-shift));
		}
	}

	@keyframes trainer-onboarding-travel-forward {
		0% {
			transform: translateY(0) rotate(0deg) scale(1);
		}
		42% {
			transform: translateY(-1.35rem) rotate(-2deg) scale(1.015);
		}
		58% {
			transform: translateY(-1.35rem) rotate(0deg) scale(1.015);
		}
		100% {
			transform: translateY(0) rotate(1.5deg) scale(1);
		}
	}

	@keyframes trainer-onboarding-travel-back {
		0% {
			transform: translateY(0) rotate(1.5deg) scale(1);
		}
		42% {
			transform: translateY(-1.35rem) rotate(0deg) scale(1.015);
		}
		58% {
			transform: translateY(-1.35rem) rotate(2deg) scale(1.015);
		}
		100% {
			transform: translateY(0) rotate(0deg) scale(1);
		}
	}

	/* Combined wipe + facing flip: the sprite pinches shut, the scaleX flip
	   happens at the fully-pinched midpoint (invisible), then it reopens. */
	@keyframes trainer-onboarding-sprite-forward {
		0% {
			clip-path: inset(0 0 0 0);
			transform: translateY(-2%) scaleX(1);
		}
		49.99% {
			clip-path: inset(0 30% 0 30%);
			transform: translateY(-2%) scaleX(1);
		}
		50% {
			clip-path: inset(0 30% 0 30%);
			transform: translateY(-2%) scaleX(-1);
		}
		100% {
			clip-path: inset(0 0 0 0);
			transform: translateY(-2%) scaleX(-1);
		}
	}

	@keyframes trainer-onboarding-sprite-back {
		0% {
			clip-path: inset(0 0 0 0);
			transform: translateY(-2%) scaleX(-1);
		}
		49.99% {
			clip-path: inset(0 30% 0 30%);
			transform: translateY(-2%) scaleX(-1);
		}
		50% {
			clip-path: inset(0 30% 0 30%);
			transform: translateY(-2%) scaleX(1);
		}
		100% {
			clip-path: inset(0 0 0 0);
			transform: translateY(-2%) scaleX(1);
		}
	}

	@keyframes trainer-onboarding-platform-out {
		from {
			--platform-strength: 1;
		}
		to {
			--platform-strength: 0;
		}
	}

	@keyframes trainer-onboarding-platform-in {
		from {
			--platform-strength: 0;
		}
		to {
			--platform-strength: 1;
		}
	}

	@keyframes trainer-onboarding-page-in {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@media (max-width: 480px) {
		.trainer-onboarding {
			/* 72% - 28% of the scene == 44vw on narrow screens. */
			--onboarding-cross-shift: 44vw;
		}

		.trainer-onboarding__portrait--register,
		.trainer-onboarding__portrait--cross-forward {
			left: 72%;
		}

		.trainer-onboarding__portrait--hatch,
		.trainer-onboarding__portrait--cross-back {
			left: 28%;
		}

		.trainer-onboarding__portrait,
		.trainer-onboarding__hatchling {
			bottom: clamp(10rem, 20vh, 12rem);
		}

		.trainer-onboarding__hatchling {
			left: 67%;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.trainer-onboarding__portrait--cross-forward,
		.trainer-onboarding__portrait--cross-back {
			animation-duration: 1ms;
		}

		.trainer-onboarding__portrait--cross-forward .trainer-onboarding__portrait-stage,
		.trainer-onboarding__portrait--cross-back .trainer-onboarding__portrait-stage,
		.trainer-onboarding__portrait--cross-forward :global(.trainer-portrait__sprite),
		.trainer-onboarding__portrait--cross-back :global(.trainer-portrait__sprite),
		.trainer-onboarding__portrait--cross-forward :global(.trainer-portrait),
		.trainer-onboarding__portrait--cross-back :global(.trainer-portrait),
		.trainer-onboarding__page {
			animation: none;
		}
	}
</style>
