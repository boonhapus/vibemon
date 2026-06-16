<script lang="ts">
	import { getContext } from 'svelte';

	import DialogBox from '$lib/ui/DialogBox.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';
	import TrainerNameInput from '$lib/ui/TrainerNameInput.svelte';

	import { checkUsernameAvailability, fetchTrainerMe, finalizeTrainerRegistration } from './trainerApi';
	import { applyTrainerReferenceUrl, type TrainerOnboardingUi } from './trainerOnboardingUi';
	import TrainerReference from './TrainerReference.svelte';
	import TrainerReferenceCamera from './TrainerReferenceCamera.svelte';
	import { validateUsername } from './validateUsername';

	const REFERENCE_HINT_TEXT = `Tap the camera and we'll give your Trainer a new look.`;
	const REFERENCE_LOADING_TEXT = `Giving your Trainer a new look...`;
	const SETUP_LOADING_TEXT = `One sec, Trainer...`;
	const ONBOARDING_UI_KEY = 'trainer-onboarding-ui';

	let {
		dialogText = 'Right on, Trainer! First.. what do folks call you?',
		showDialogCursor = true,
		typeDialogOnLoad = true,
		initialUsername = '',
		embedded = false,
		onAccepted
	}: {
		dialogText?: string;
		showDialogCursor?: boolean;
		typeDialogOnLoad?: boolean;
		initialUsername?: string;
		embedded?: boolean;
		onAccepted?: (username: string) => void;
	} = $props();

	const onboardingUi = getContext<TrainerOnboardingUi | undefined>(ONBOARDING_UI_KEY);
	let username = $state(initialUsername.trim());
	let referenceHintVisible = $state(false);
	let referenceSpriteSrc = $state('/game/sprites/trainer@128.png');
	let pendingReferenceFile = $state<File | null>(null);
	let referencePreviewUrl = $state<string | null>(null);
	let checking = $state(false);
	let hintVisible = $derived(embedded ? (onboardingUi?.referenceHintVisible ?? false) : referenceHintVisible);
	let setupBusy = $derived(embedded ? (onboardingUi?.setupInProgress ?? false) : checking);
	let loadingText = $derived(
		embedded && onboardingUi?.referenceGenerating ? REFERENCE_LOADING_TEXT : SETUP_LOADING_TEXT
	);
	let canContinue = $derived(!setupBusy && validateUsername(username) === null);

	$effect(() => {
		if (embedded && onboardingUi) {
			onboardingUi.registrationUsername = username;
		}
	});

	function stageLocalReference(file: File, previewUrl: string) {
		if (referencePreviewUrl?.startsWith('blob:')) {
			URL.revokeObjectURL(referencePreviewUrl);
		}
		pendingReferenceFile = file;
		referencePreviewUrl = previewUrl;
		referenceSpriteSrc = previewUrl;
	}

	function resolvePendingReferenceFile(): File | null {
		if (embedded) {
			return onboardingUi?.pendingReferenceFile ?? null;
		}
		return pendingReferenceFile;
	}

	function applyReferenceFromSession(referenceUrl: string | null) {
		if (!referenceUrl) return;
		if (embedded && onboardingUi) {
			applyTrainerReferenceUrl(onboardingUi, referenceUrl);
			return;
		}
		if (referencePreviewUrl?.startsWith('blob:')) {
			URL.revokeObjectURL(referencePreviewUrl);
		}
		pendingReferenceFile = null;
		referencePreviewUrl = null;
		referenceSpriteSrc = referenceUrl;
	}

	async function attemptContinue() {
		if (setupBusy) return;
		const validationError = validateUsername(username);
		if (validationError) {
			showGameToast(validationError, 'amber');
			return;
		}

		checking = true;
		if (embedded && onboardingUi) {
			onboardingUi.setupInProgress = true;
		}

		try {
			const trimmed = username.trim();
			const existingSession = await fetchTrainerMe();
			const sessionMatches =
				existingSession !== null &&
				existingSession.username.toLowerCase() === trimmed.toLowerCase();

			if (!sessionMatches) {
				const availability = await checkUsernameAvailability(trimmed);
				if (availability.status === 'taken' || availability.status === 'invalid') {
					showGameToast(availability.message, 'amber');
					return;
				}
				if (availability.status === 'error') {
					showGameToast(availability.message, 'brick');
					return;
				}
			}

			const pendingFile = resolvePendingReferenceFile();
			if (sessionMatches && existingSession?.reference_url && !pendingFile) {
				applyReferenceFromSession(existingSession.reference_url);
				onAccepted?.(trimmed);
				return;
			}

			const result = await finalizeTrainerRegistration(trimmed, pendingFile);
			if (result.status === 'session_failed') {
				showGameToast(result.message, 'brick');
				return;
			}
			if (result.status === 'reference_failed') {
				showGameToast(result.message, 'amber');
			}

			applyReferenceFromSession(result.session.reference_url);
			onAccepted?.(username.trim());
		} catch {
			showGameToast('Could not set up your trainer. Try again.', 'brick');
		} finally {
			checking = false;
			if (embedded && onboardingUi) {
				onboardingUi.setupInProgress = false;
			}
		}
	}
</script>

{#snippet registrationBody()}
	<div class="trainer-registration" class:trainer-registration--embedded={embedded}>
		<div class="trainer-registration__name">
			<TrainerNameInput bind:username autofocus onSubmit={attemptContinue} disabled={setupBusy} />
		</div>

		{#if !embedded}
			<div class="trainer-registration__reference">
				<div class="trainer-registration__reference-stage">
					<TrainerReference spriteSrc={referenceSpriteSrc} />

					<TrainerReferenceCamera
						bind:hovered={referenceHintVisible}
						deferUpload
						disabled={setupBusy}
						onFileSelected={(file, previewUrl) => {
							stageLocalReference(file, previewUrl);
						}}
					/>
				</div>
			</div>
		{/if}

		<div class="trainer-registration__dialog">
			{#if setupBusy}
				<GamePanel tone="status" class="hud-dialog-slot trainer-registration__loading">
					<p class="trainer-registration__loading-text" aria-live="polite">{loadingText}</p>
				</GamePanel>
			{:else if hintVisible}
				<GamePanel tone="status" class="hud-dialog-slot trainer-registration__reference-hint">
					<p class="trainer-registration__reference-hint-text">{REFERENCE_HINT_TEXT}</p>
				</GamePanel>
			{:else}
				<DialogBox
					text={dialogText}
					showCursor={showDialogCursor}
					typewriter={typeDialogOnLoad}
					continueDisabled={!canContinue}
					onContinue={attemptContinue}
				/>
			{/if}
		</div>
	</div>
{/snippet}

{#if embedded}
	{@render registrationBody()}
{:else}
	<SceneFrame>
		{@render registrationBody()}
	</SceneFrame>
{/if}

<style>
	.trainer-registration {
		position: relative;
		min-height: 100dvh;
	}
	.trainer-registration--embedded {
		min-height: 100dvh;
		/* Let the layout-owned reference camera receive hover through this shell. */
		pointer-events: none;
	}
	.trainer-registration--embedded .trainer-registration__name,
	.trainer-registration--embedded .trainer-registration__dialog {
		pointer-events: auto;
	}
	.trainer-registration__name {
		position: absolute;
		top: clamp(1.25rem, 5vh, 2.5rem);
		left: clamp(1.25rem, 4vw, 2.5rem);
		z-index: 2;
		max-width: calc(100% - 2.5rem);
	}
	.trainer-registration__reference {
		position: absolute;
		left: 70%;
		bottom: clamp(12rem, 23vh, 14.5rem);
		transform: translateX(-50%);
		z-index: 1;
	}
	.trainer-registration__reference-stage {
		position: relative;
	}
	:global(.trainer-registration__loading) {
		--panel-status-accent: var(--vm-status-amber);
		--panel-status-surface: color-mix(in srgb, var(--vm-status-amber) 16%, var(--vm-panel-command-bg));
		animation: trainer-registration-loading 900ms steps(2, end) infinite;
	}
	@keyframes trainer-registration-loading {
		0%,
		49% {
			opacity: 1;
		}
		50%,
		100% {
			opacity: 0.68;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		:global(.trainer-registration__loading) {
			animation: none;
		}
	}
	.trainer-registration__dialog {
		position: absolute;
		left: 50%;
		bottom: clamp(1.25rem, 5vh, 2.5rem);
		transform: translateX(-50%);
		z-index: 2;
		width: var(--vm-hud-dialog-width);
		display: flex;
		justify-content: center;
	}
</style>
