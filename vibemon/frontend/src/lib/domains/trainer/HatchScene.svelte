<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onDestroy, onMount, setContext } from 'svelte';
	import { prefersReducedMotion } from 'svelte/motion';

	import AdoptCrewModal from '$lib/domains/trainer/AdoptCrewModal.svelte';
	import HatchCandidatePanel from '$lib/domains/trainer/HatchCandidatePanel.svelte';
	import HatchlingSilhouette from '$lib/domains/trainer/HatchlingSilhouette.svelte';
	import ProviderConfigModal from '$lib/domains/trainer/ProviderConfigModal.svelte';
	import { providerConfigModalStore } from '$lib/domains/trainer/providerConfigModalStore.svelte';
	import { closeSettings, settingsStore } from '$lib/domains/trainer/settingsStore.svelte';
	import TrainerConfigurationScene from '$lib/domains/trainer/TrainerConfigurationScene.svelte';
	import TrainerReference from '$lib/domains/trainer/TrainerReference.svelte';
	import { readHatchDevOverrides } from '$lib/domains/trainer/devOverrides';
	import {
		bootstrapHatchSessionOnce,
		clearHatchBootstrapCache,
		createHatchSession,
		createHatchSessionActions,
		hatchControlsBlocked,
		HATCH_SESSION_KEY,
		releaseDisabled,
		restoreHatchSession,
		type HatchSessionState
	} from '$lib/domains/trainer/hatchSession';
	import { trainerRelativeHeight } from '$lib/domains/trainer/hatchDisplaySize';
	import { readPendingUsername } from '$lib/domains/trainer/trainerRegisterStore.svelte';
	import {
		createTrainerOnboardingUi,
		type TrainerOnboardingUi
	} from '$lib/domains/trainer/trainerOnboardingUi';
	import { gameSolarContext } from '$lib/domains/game/gameSolarContext.svelte';
	import { sceneBackgroundSrc } from '$lib/domains/game/sceneBackgrounds';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';

	const HATCH_UI_KEY = 'trainer-onboarding-ui';

	let hatchUi = $state(createTrainerOnboardingUi());
	let hatchSession = $state(createHatchSession());
	let hatchSceneRestored = $state(false);
	let username = $state('');

	setContext<TrainerOnboardingUi>(HATCH_UI_KEY, hatchUi);
	setContext<HatchSessionState>(HATCH_SESSION_KEY, hatchSession);

	let hatchDevOverrides = $derived(readHatchDevOverrides(page.url.searchParams));

	const hatchActions = createHatchSessionActions(hatchSession, {
		bypassCredits: () => hatchDevOverrides.bypassCredits,
		showToast: showGameToast,
		goto,
		prefersReducedMotion: () => prefersReducedMotion.current
	});

	onMount(() => {
		const pending = readPendingUsername();
		if (!pending) {
			void goto('/register');
			return;
		}
		username = pending;
		restoreHatchSession(hatchSession);
		hatchUi.referenceSpriteSrc = hatchSession.referenceSpriteSrc;
		hatchSceneRestored = true;
	});

	onDestroy(() => {
		clearHatchBootstrapCache();
		providerConfigModalStore.open = false;
		providerConfigModalStore.entry = null;
		closeSettings();
	});

	let flowBlockers = $derived({
		settingsOpen: settingsStore.open,
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
	let hatchBackgroundSrc = $derived(sceneBackgroundSrc('hatch', gameSolarContext.phase));

	let hatchSceneStyle = $derived.by(() => {
		const candidate = hatchSession.candidate;
		if (!candidate || !hatchSession.spriteVisible) return '';
		const factor = trainerRelativeHeight(candidate);
		const parts = [
			`--hatch-scene-hatchling-sprite-h: calc(var(--hatch-scene-trainer-sprite-h) * ${factor.toFixed(3)})`
		];
		if (candidate.display?.anchor_x != null) {
			parts.push(`--hatchling-anchor-x: ${candidate.display.anchor_x.toFixed(4)}`);
		}
		if (candidate.display?.baseline_y != null) {
			parts.push(`--hatchling-baseline-y: ${candidate.display.baseline_y.toFixed(4)}`);
		}
		return parts.join('; ');
	});

	$effect(() => {
		if (!browser || !hatchSceneRestored || !username) return;

		void bootstrapHatchSessionOnce(hatchSession, username).then(() => {
			hatchUi.referenceSpriteSrc = hatchSession.referenceSpriteSrc;
			hatchUi.referenceSpriteReady = hatchSession.referenceSpriteReady;
		});
	});

	function handleHatchClick() {
		if (hatchControlsBlockedState || hatchSession.candidate) return;
		void hatchActions.generate(flowBlockers);
	}

	function handleHatchKeydown(event: KeyboardEvent) {
		if (event.key !== 'Enter' || event.defaultPrevented) return;
		if (
			event.target instanceof Element &&
			event.target.closest('input, textarea, select, [contenteditable="true"]')
		) {
			return;
		}
		if (!hatchable || hatchControlsBlockedState) return;
		event.preventDefault();
		handleHatchClick();
	}
</script>

<svelte:window onkeydown={handleHatchKeydown} />

<SceneFrame backgroundSrc={hatchBackgroundSrc} backgroundFadeMs={720}>
	<div class="hatch-scene" style={hatchSceneStyle}>
		<div
			class="hatch-scene__reference"
			class:hatch-scene__reference--pending={!hatchSession.referenceSpriteReady}
			aria-hidden="true"
		>
			<div class="hatch-scene__reference-stage">
				{#key hatchSession.referenceSpriteSrc}
					<TrainerReference mirrored spriteSrc={hatchSession.referenceSpriteSrc} />
				{/key}
			</div>
		</div>

		{#if hatchSession.candidate}
			<div
				class="hatch-scene__candidate-stack"
				class:hatch-scene__candidate-stack--revealing={hatchSession.revealing}
			>
				<HatchCandidatePanel
					candidate={hatchSession.candidate}
					bind:actionHint={hatchSession.actionHint}
					bind:detailHint={hatchSession.candidateHint}
					releaseDisabled={releaseBlocked}
					busy={hatchSession.busy}
					onRelease={() => hatchActions.reject(flowBlockers)}
					onRefresh={() => hatchActions.refresh(flowBlockers)}
					onAdopt={() => void hatchActions.openAdoptModal(flowBlockers)}
				/>
			</div>
		{/if}

		<div class="hatch-scene__hatchling">
			<HatchlingSilhouette
				{hatchable}
				spriteSrc={hatchSpriteSrc}
				showSilhouette={hatchShowSilhouette}
				generating={hatchSuspenseActive}
				beat={hatchSession.beat}
				revealing={hatchSession.revealing}
				onhatch={handleHatchClick}
			/>
		</div>

		<div class="hatch-scene__content">
			{#if username}
				<TrainerConfigurationScene embedded {username} />
			{/if}
		</div>

		<AdoptCrewModal
			bind:open={hatchSession.adoptModalOpen}
			bind:releaseTargetId={hatchSession.adoptReleaseTargetId}
			speciesName={hatchSession.candidate?.name ?? 'your Vibemon'}
			swapTargets={hatchSession.adoptSwapMembers}
			busy={hatchSession.busy}
			onConfirm={(nickname) => hatchActions.confirmAdopt(nickname)}
		/>
		<ProviderConfigModal />
	</div>
</SceneFrame>

<style>
	.hatch-scene {
		position: relative;
		min-height: 100dvh;
		--hatch-scene-stage-bottom: clamp(12.5rem, 24vh, 15.5rem);
		--hatch-scene-stage-platform-h: clamp(2.35rem, 5vw, 3.5rem);
		--hatch-scene-trainer-left: 24%;
		--hatch-scene-mon-left: 58%;
		--hatch-scene-mon-nudge: clamp(0.75rem, 1.5vh, 1.25rem);
		--hatch-scene-trainer-sprite-h: clamp(26rem, 58vh, 42rem);
		--hatch-scene-hatchling-sprite-h: clamp(13rem, 30vh, 22rem);
		--hatch-scene-hatchling-lift: min(var(--hatch-scene-hatchling-sprite-h), 42vh);
	}

	.hatch-scene__reference {
		position: absolute;
		left: var(--hatch-scene-trainer-left);
		bottom: var(--hatch-scene-stage-bottom);
		z-index: 1;
		transform: translateX(-50%);
		pointer-events: auto;
	}

	.hatch-scene__reference--pending {
		visibility: hidden;
		pointer-events: none;
	}

	.hatch-scene__reference-stage {
		position: relative;
	}

	.hatch-scene__reference :global(.trainer-reference) {
		--sprite-h: var(--hatch-scene-trainer-sprite-h);
		--sprite-w: calc(var(--sprite-h) * 0.56);
		--platform-w: calc(var(--sprite-h) * 0.82);
		--sprite-foot-nudge-y: 4%;
		--platform-h: var(--hatch-scene-stage-platform-h);
	}

	/* Dark contact shadow shared by both sprites. These vars are declared directly on
	   .trainer-reference in TrainerReference.svelte, so the override must target that
	   element directly on each — the hatchling renders its own inner .trainer-reference,
	   so an ancestor rule would lose to the component's own default. */
	.hatch-scene__reference :global(.trainer-reference),
	.hatch-scene__hatchling :global(.trainer-reference) {
		--platform-core-bg: radial-gradient(
			ellipse 100% 100% at 50% 50%,
			rgb(34 24 16 / 0.5) 0%,
			rgb(34 24 16 / 0.32) 48%,
			rgb(34 24 16 / 0.12) 78%,
			transparent 100%
		);
		--platform-feather-bg: radial-gradient(
			ellipse 100% 100% at 50% 54%,
			rgb(34 24 16 / 0.28) 0%,
			rgb(34 24 16 / 0.1) 100%
		);
	}

	.hatch-scene__hatchling {
		position: absolute;
		left: var(--hatch-scene-mon-left);
		bottom: calc(var(--hatch-scene-stage-bottom) - var(--hatch-scene-mon-nudge));
		transform: translateX(-50%);
		z-index: 3;
		pointer-events: auto;
	}

	.hatch-scene__hatchling :global(.hatchling-silhouette) {
		--hatchling-sprite-h: var(--hatch-scene-hatchling-sprite-h);
		--platform-h: var(--hatch-scene-stage-platform-h);
	}

	.hatch-scene__candidate-stack {
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
				100% - var(--hatch-scene-mon-left) - var(--hatch-scene-hatchling-sprite-h) * 0.52 -
					var(--vm-bezel-w) * 2
			),
			var(--vm-hud-candidate-rail-max-width)
		);
		min-width: 0;
		height: min(
			var(--vm-hud-candidate-panel-min-height),
			calc(100dvh - var(--vm-bezel-w) * 2 - clamp(1.25rem, 4vh, 2rem))
		);
	}

	.hatch-scene__candidate-stack :global(.hatch-candidate-panel-shell) {
		flex: 1;
		min-height: 0;
		height: 100%;
	}

	.hatch-scene__candidate-stack--revealing {
		animation: hatch-scene-candidate-in 720ms ease-out both;
	}

	@keyframes hatch-scene-candidate-in {
		from {
			opacity: 0;
			transform: translateY(6px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.hatch-scene__content {
		position: relative;
		z-index: 2;
		min-height: 100dvh;
		pointer-events: none;
	}
</style>
