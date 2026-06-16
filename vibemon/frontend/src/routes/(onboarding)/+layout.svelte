<script lang="ts">
	import { browser } from '$app/environment';
	import { afterNavigate, goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount, setContext, type Snippet } from 'svelte';
	import { prefersReducedMotion } from 'svelte/motion';

	import HatchlingSilhouette from '$lib/domains/trainer/HatchlingSilhouette.svelte';
	import ProviderConfigModal from '$lib/domains/trainer/ProviderConfigModal.svelte';
	import { providerConfigModalStore } from '$lib/domains/trainer/providerConfigModalStore.svelte';
	import SettingsModal from '$lib/domains/trainer/SettingsModal.svelte';
	import { uploadTrainerReferenceWithSession } from '$lib/domains/trainer/trainerApi';
	import {
		bootstrapHatchSessionOnce,
		clearHatchBootstrapCache,
		clearHatchSessionState,
		createHatchSession,
		createHatchSessionActions,
		hatchControlsBlocked,
		HATCH_SESSION_KEY,
		persistHatchSession,
		releaseDisabled,
		restoreHatchSession,
		type HatchSessionState
	} from '$lib/domains/trainer/hatchSession';
	import { readPendingUsername } from '$lib/domains/trainer/trainerRegisterStore.svelte';
	import {
		applyTrainerReferenceUrl,
		createTrainerOnboardingUi,
		type TrainerOnboardingUi
	} from '$lib/domains/trainer/trainerOnboardingUi';
	import {
		addSelectedProvider,
		isProviderSelected,
		markProviderWarmed,
		removeSelectedProvider,
		setProviderCoordinates,
		setProviderFetching
	} from '$lib/domains/trainer/providerSelection';
	import AdoptNicknameModal from '$lib/domains/trainer/AdoptNicknameModal.svelte';
	import HatchCandidatePanel from '$lib/domains/trainer/HatchCandidatePanel.svelte';
	import HatchSceneDepth from '$lib/domains/trainer/HatchSceneDepth.svelte';
	import SettingsNavButton from '$lib/domains/trainer/SettingsNavButton.svelte';
	import { readHatchDevOverrides } from '$lib/domains/trainer/devOverrides';
	import TrainerReference from '$lib/domains/trainer/TrainerReference.svelte';
	import TrainerReferenceCamera from '$lib/domains/trainer/TrainerReferenceCamera.svelte';
	import GameToast from '$lib/ui/GameToast.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';

	const ONBOARDING_UI_KEY = 'trainer-onboarding-ui';

	let { children }: { children: Snippet } = $props();

	let onboardingUi = $state(createTrainerOnboardingUi());
	let hatchSession = $state(createHatchSession());
	let hatchSceneRestored = $state(false);

	setContext<TrainerOnboardingUi>(ONBOARDING_UI_KEY, onboardingUi);
	setContext<HatchSessionState>(HATCH_SESSION_KEY, hatchSession);

	let isRegister = $derived(page.url.pathname.endsWith('/register'));
	let isHatch = $derived(page.url.pathname.endsWith('/hatch'));
	let hatchDevOverrides = $derived(
		isHatch ? readHatchDevOverrides(page.url.searchParams) : { bypassCredits: false }
	);

	const hatchActions = createHatchSessionActions(hatchSession, {
		bypassCredits: () => hatchDevOverrides.bypassCredits,
		showToast: showGameToast,
		goto,
		prefersReducedMotion: () => prefersReducedMotion.current
	});

	onMount(() => {
		restoreHatchSession(hatchSession);
		onboardingUi.referenceSpriteSrc = hatchSession.referenceSpriteSrc;
		hatchSceneRestored = true;
	});

	let flowBlockers = $derived({
		settingsOpen: onboardingUi.settingsOpen,
		providerModalOpen: providerConfigModalStore.open
	});
	let hatchSpriteSrc = $derived(
		hatchSession.spriteVisible && hatchSession.candidate?.reference_url
			? hatchSession.candidate.reference_url
			: '/game/sprites/hatchling-silhouette@128.png'
	);
	let hatchShowSilhouette = $derived(!hatchSession.spriteVisible);
	let releaseBlocked = $derived(releaseDisabled(hatchSession));
	let hatchControlsBlockedState = $derived(hatchControlsBlocked(hatchSession, flowBlockers));
	let hatchable = $derived(!hatchControlsBlockedState && !hatchSession.candidate);
	let hatchSuspenseActive = $derived(hatchSession.generating || hatchSession.busy);

	let crossing = $state<'none' | 'forward' | 'back'>('none');
	let mirrored = $derived(crossing === 'none' ? isHatch : crossing === 'back');

	const SIZE_BANDS: Record<string, [number, number]> = {
		small: [0.4, 0.55],
		mid: [0.7, 0.95],
		large: [1.1, 1.3]
	};

	let hatchSceneStyle = $derived.by(() => {
		const candidate = hatchSession.candidate;
		if (!candidate || !hatchSession.spriteVisible) return '';
		const band = SIZE_BANDS[candidate.display?.size_class ?? 'mid'] ?? SIZE_BANDS.mid;
		const t = (Math.min(Math.max(candidate.power_pips ?? 2, 1), 3) - 1) / 2;
		const factor = band[0] + (band[1] - band[0]) * t;
		const parts = [
			`--onboarding-hatchling-sprite-h: calc(var(--onboarding-trainer-sprite-h) * ${factor.toFixed(3)})`
		];
		if (candidate.display?.anchor_x != null) {
			parts.push(`--hatchling-anchor-x: ${candidate.display.anchor_x.toFixed(4)}`);
		}
		if (candidate.display?.baseline_y != null) {
			parts.push(`--hatchling-baseline-y: ${candidate.display.baseline_y.toFixed(4)}`);
		}
		return parts.join('; ');
	});

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
			clearHatchBootstrapCache();
			onboardingUi.settingsOpen = false;
			providerConfigModalStore.open = false;
			providerConfigModalStore.entry = null;
		}
	});

	let referenceClass = $derived(
		[
			'trainer-onboarding__reference',
			crossing === 'forward' && 'trainer-onboarding__reference--cross-forward',
			crossing === 'back' && 'trainer-onboarding__reference--cross-back',
			crossing === 'none' && isRegister && 'trainer-onboarding__reference--register',
			crossing === 'none' && isHatch && 'trainer-onboarding__reference--hatch'
		]
			.filter(Boolean)
			.join(' ')
	);

	function finishCross() {
		crossing = 'none';
	}

	async function uploadRegisterReference(file: File): Promise<string | null> {
		onboardingUi.setupInProgress = true;
		onboardingUi.referenceGenerating = true;
		try {
			const result = await uploadTrainerReferenceWithSession(file, onboardingUi.registrationUsername);
			if (result.status === 'ok') {
				return result.session.reference_url;
			}

			showGameToast(result.message, result.status === 'needs_username' ? 'amber' : 'brick');
			return null;
		} finally {
			onboardingUi.referenceGenerating = false;
			onboardingUi.setupInProgress = false;
		}
	}

	$effect(() => {
		if (!browser || !isRegister) return;
		onboardingUi.referenceSpriteReady = true;
	});

	$effect(() => {
		if (!browser || !isHatch || !hatchSceneRestored) return;
		const username = readPendingUsername();
		if (!username) return;

		void bootstrapHatchSessionOnce(hatchSession, username).then(() => {
			onboardingUi.referenceSpriteSrc = hatchSession.referenceSpriteSrc;
			onboardingUi.referenceSpriteReady = hatchSession.referenceSpriteReady;
		});
	});

	function handleHatchClick() {
		if (hatchControlsBlockedState || hatchSession.candidate) return;
		onboardingUi.hatchHintVisible = false;
		void hatchActions.generate(flowBlockers);
	}

	function handleReferenceAnimationEnd(event: AnimationEvent) {
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

{#snippet settingsCorner()}
	<SettingsNavButton bind:open={onboardingUi.settingsOpen} />
{/snippet}

<SceneFrame bezelCorner={isHatch ? settingsCorner : undefined}>
	<div class="trainer-onboarding" style={hatchSceneStyle}>
		{#if isHatch}
			<HatchSceneDepth />
		{/if}
		<div
			class={referenceClass}
			class:trainer-onboarding__reference--pending={isHatch && !hatchSession.referenceSpriteReady}
			onanimationend={handleReferenceAnimationEnd}
			aria-hidden="true"
		>
			<div class="trainer-onboarding__reference-stage">
				{#key hatchSession.referenceSpriteSrc}
					<TrainerReference {mirrored} spriteSrc={hatchSession.referenceSpriteSrc} />
				{/key}
				{#if isRegister}
					<TrainerReferenceCamera
						bind:hovered={onboardingUi.referenceHintVisible}
						disabled={onboardingUi.setupInProgress}
						uploadReference={uploadRegisterReference}
						onReferenceUrl={(referenceUrl) => {
							void hatchActions.applyReferenceUrl(referenceUrl);
						}}
					/>
				{/if}
			</div>
		</div>

		{#if isHatch}
			{#if hatchSession.candidate}
				<div
					class="trainer-onboarding__candidate-stack"
					class:trainer-onboarding__candidate-stack--revealing={hatchSession.revealing}
				>
					<HatchCandidatePanel
						candidate={hatchSession.candidate}
						bind:actionHint={hatchSession.actionHint}
						bind:detailHint={hatchSession.candidateHint}
						releaseDisabled={releaseBlocked}
						busy={hatchSession.busy}
						onRelease={() => hatchActions.reject(flowBlockers)}
						onRefresh={() => hatchActions.refresh(flowBlockers)}
						onAdopt={() => hatchActions.openAdoptModal(flowBlockers)}
					/>
				</div>
			{/if}

			<div class="trainer-onboarding__hatchling">
				<HatchlingSilhouette
					bind:hovered={onboardingUi.hatchHintVisible}
					{hatchable}
					spriteSrc={hatchSpriteSrc}
					showSilhouette={hatchShowSilhouette}
					generating={hatchSuspenseActive}
					beat={hatchSession.beat}
					revealing={hatchSession.revealing}
					onhatch={handleHatchClick}
				/>
			</div>

			<AdoptNicknameModal
				bind:open={hatchSession.adoptModalOpen}
				speciesName={hatchSession.candidate?.name ?? 'your Vibemon'}
				busy={hatchSession.busy}
				onConfirm={(nickname) => hatchActions.confirmAdopt(nickname)}
			/>
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
		--onboarding-cross-shift: 40vw;

		position: relative;
		min-height: 100dvh;
		--onboarding-stage-bottom: clamp(12.5rem, 24vh, 15.5rem);
		--onboarding-stage-platform-h: clamp(2.35rem, 5vw, 3.5rem);
		--onboarding-hatch-trainer-left: 24%;
		--onboarding-hatch-mon-left: 58%;
		--onboarding-hatch-mon-nudge: clamp(0.75rem, 1.5vh, 1.25rem);
		--onboarding-trainer-sprite-h: clamp(26rem, 58vh, 42rem);
		--onboarding-hatchling-sprite-h: clamp(13rem, 30vh, 22rem);
		--onboarding-hatchling-lift: min(var(--onboarding-hatchling-sprite-h), 42vh);
	}

	.trainer-onboarding__reference {
		position: absolute;
		bottom: var(--onboarding-stage-bottom);
		z-index: 1;
		transform: translateX(-50%);
		pointer-events: auto;
	}

	.trainer-onboarding__reference--pending {
		visibility: hidden;
		pointer-events: none;
	}

	.trainer-onboarding__reference-stage {
		position: relative;
	}

	.trainer-onboarding__hatchling {
		position: absolute;
		left: var(--onboarding-hatch-mon-left);
		bottom: calc(var(--onboarding-stage-bottom) - var(--onboarding-hatch-mon-nudge));
		transform: translateX(-50%);
		z-index: 1;
		pointer-events: none;
	}

	.trainer-onboarding__hatchling :global(.hatchling-silhouette) {
		--hatchling-sprite-h: var(--onboarding-hatchling-sprite-h);
	}

	.trainer-onboarding__candidate-stack {
		position: absolute;
		top: var(--vm-bezel-w);
		right: var(--vm-bezel-w);
		z-index: 4;
		pointer-events: auto;
		display: flex;
		flex-direction: column;
		align-items: stretch;
		width: min(
			calc(
				100% - var(--onboarding-hatch-mon-left) - var(--onboarding-hatchling-sprite-h) * 0.52 -
					var(--vm-bezel-w) * 2
			),
			var(--vm-hud-candidate-rail-max-width)
		);
		min-width: 0;
		min-height: var(--vm-hud-candidate-panel-min-height);
	}

	.trainer-onboarding__candidate-stack--revealing {
		animation: trainer-onboarding-candidate-in 720ms ease-out both;
	}

	@keyframes trainer-onboarding-candidate-in {
		from {
			opacity: 0;
			transform: translateY(6px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.trainer-onboarding__reference--hatch :global(.trainer-reference),
	.trainer-onboarding__hatchling :global(.trainer-reference) {
		--platform-h: var(--onboarding-stage-platform-h);
	}

	.trainer-onboarding__hatchling :global(.hatchling-silhouette) {
		--platform-h: var(--onboarding-stage-platform-h);
	}

	.trainer-onboarding__reference--hatch :global(.trainer-reference) {
		--sprite-h: var(--onboarding-trainer-sprite-h);
		--sprite-w: calc(var(--sprite-h) * 0.56);
		--platform-w: calc(var(--sprite-h) * 0.82);
		--sprite-foot-nudge-y: 4%;
	}

	.trainer-onboarding__reference--register {
		left: 70%;
	}

	.trainer-onboarding__reference--hatch {
		left: var(--onboarding-hatch-trainer-left);
	}

	.trainer-onboarding__reference--cross-forward {
		left: 70%;
		will-change: transform;
		animation: trainer-onboarding-slide-forward var(--onboarding-move-duration) var(--onboarding-transition-timing)
			var(--onboarding-move-delay) forwards;
	}

	.trainer-onboarding__reference--cross-back {
		left: var(--onboarding-hatch-trainer-left);
		will-change: transform;
		animation: trainer-onboarding-slide-back var(--onboarding-move-duration) var(--onboarding-transition-timing)
			var(--onboarding-move-delay) forwards;
	}

	.trainer-onboarding__reference--cross-forward .trainer-onboarding__reference-stage {
		will-change: transform;
		animation: trainer-onboarding-travel-forward var(--onboarding-move-duration) var(--onboarding-action-timing)
			var(--onboarding-move-delay) forwards;
	}

	.trainer-onboarding__reference--cross-back .trainer-onboarding__reference-stage {
		will-change: transform;
		animation: trainer-onboarding-travel-back var(--onboarding-move-duration) var(--onboarding-action-timing)
			var(--onboarding-move-delay) forwards;
	}

	.trainer-onboarding__reference--cross-forward :global(.trainer-reference__sprite) {
		will-change: transform;
		animation: trainer-onboarding-sprite-forward var(--onboarding-move-duration) ease-in-out
			var(--onboarding-move-delay) forwards;
	}

	.trainer-onboarding__reference--cross-back :global(.trainer-reference__sprite) {
		will-change: transform;
		animation: trainer-onboarding-sprite-back var(--onboarding-move-duration) ease-in-out
			var(--onboarding-move-delay) forwards;
	}

	.trainer-onboarding__reference--cross-forward :global(.trainer-reference),
	.trainer-onboarding__reference--cross-back :global(.trainer-reference) {
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

	@keyframes trainer-onboarding-sprite-forward {
		0%,
		54.99% {
			transform: perspective(600px) translateY(-2%) rotateY(0deg);
		}
		80% {
			transform: perspective(600px) translateY(-2%) rotateY(180deg);
		}
		100% {
			transform: perspective(600px) translateY(-2%) rotateY(180deg);
		}
	}

	@keyframes trainer-onboarding-sprite-back {
		0%,
		54.99% {
			transform: perspective(600px) translateY(-2%) rotateY(180deg);
		}
		80% {
			transform: perspective(600px) translateY(-2%) rotateY(0deg);
		}
		100% {
			transform: perspective(600px) translateY(-2%) rotateY(0deg);
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

	@media (prefers-reduced-motion: reduce) {
		.trainer-onboarding__reference--cross-forward,
		.trainer-onboarding__reference--cross-back {
			animation-duration: 1ms;
		}

		.trainer-onboarding__reference--cross-forward .trainer-onboarding__reference-stage,
		.trainer-onboarding__reference--cross-back .trainer-onboarding__reference-stage,
		.trainer-onboarding__reference--cross-forward :global(.trainer-reference__sprite),
		.trainer-onboarding__reference--cross-back :global(.trainer-reference__sprite),
		.trainer-onboarding__reference--cross-forward :global(.trainer-reference),
		.trainer-onboarding__reference--cross-back :global(.trainer-reference),
		.trainer-onboarding__page {
			animation: none;
		}
	}
</style>
