<script lang="ts">
	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';

	import DialogBox from '$lib/ui/DialogBox.svelte';
	import GameButton from '$lib/ui/GameButton.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import TrainerNameInput from '$lib/ui/TrainerNameInput.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';

	import {
		checkUsernameAvailability,
		loginTrainer,
		type TrainerSession
	} from './trainerApi';
	import {
		applyTrainerReferenceUrl,
		DEFAULT_TRAINER_REFERENCE_SPRITE,
		resolveTrainerReferenceUrl,
		type TrainerOnboardingUi
	} from './trainerOnboardingUi';
	import { validateUsername } from './validateUsername';

	const USERNAME_DIALOG_TEXT = `Welcome back, Trainer! What's your name?`;
	const CONFIRM_DIALOG_TEXT = `That's you! Ready to get back out there?`;
	const REGISTER_OFFER_DIALOG_TEXT = `No Trainer by that name yet. Want to register instead?`;
	const LOOKUP_LOADING_TEXT = `Finding your Trainer...`;
	const ONBOARDING_UI_KEY = 'trainer-onboarding-ui';
	const USERNAME_LOOKUP_DELAY_MS = 750;

	let {
		embedded = false,
		onAccepted
	}: {
		embedded?: boolean;
		onAccepted?: (session: TrainerSession) => void;
	} = $props();

	const onboardingUi = getContext<TrainerOnboardingUi | undefined>(ONBOARDING_UI_KEY);

	let username = $state('');
	let confirmedSession = $state<TrainerSession | null>(null);
	let registerOfferUsername = $state<string | null>(null);
	let lookupBusy = $state(false);
	let lookupRequestId = 0;

	let dialogText = $derived(
		confirmedSession
			? CONFIRM_DIALOG_TEXT
			: registerOfferUsername
				? REGISTER_OFFER_DIALOG_TEXT
				: USERNAME_DIALOG_TEXT
	);
	let setupBusy = $derived(lookupBusy);
	let canContinue = $derived(Boolean(confirmedSession) && !setupBusy);
	let showRegisterOffer = $derived(Boolean(registerOfferUsername) && !confirmedSession && !setupBusy);

	$effect(() => {
		if (embedded && onboardingUi) {
			onboardingUi.registrationUsername = username;
		}
	});

	function invalidatePendingLookups() {
		lookupRequestId += 1;
		lookupBusy = false;
	}

	function resetConfirmedSession() {
		confirmedSession = null;
		registerOfferUsername = null;
		if (embedded && onboardingUi) {
			onboardingUi.referenceSpriteSrc = DEFAULT_TRAINER_REFERENCE_SPRITE;
		}
	}

	function applySessionReference(session: TrainerSession) {
		const referenceUrl = resolveTrainerReferenceUrl(session, DEFAULT_TRAINER_REFERENCE_SPRITE);
		if (embedded && onboardingUi) {
			applyTrainerReferenceUrl(onboardingUi, referenceUrl);
		}
	}

	$effect(() => {
		const trimmed = username.trim();
		const validationError = validateUsername(trimmed);

		if (validationError || !trimmed) {
			invalidatePendingLookups();
			resetConfirmedSession();
			return;
		}

		if (
			registerOfferUsername &&
			registerOfferUsername.toLowerCase() !== trimmed.toLowerCase()
		) {
			registerOfferUsername = null;
		}

		const requestId = ++lookupRequestId;
		const timer = setTimeout(() => {
			void lookupTrainer(trimmed, requestId);
		}, USERNAME_LOOKUP_DELAY_MS);

		return () => {
			clearTimeout(timer);
		};
	});

	async function lookupTrainer(trimmed: string, requestId: number) {
		lookupBusy = true;
		try {
			const availability = await checkUsernameAvailability(trimmed);
			if (requestId !== lookupRequestId) return;

			if (availability.status === 'available') {
				confirmedSession = null;
				if (embedded && onboardingUi) {
					onboardingUi.referenceSpriteSrc = DEFAULT_TRAINER_REFERENCE_SPRITE;
				}
				registerOfferUsername = trimmed;
				return;
			}

			if (availability.status === 'invalid') {
				registerOfferUsername = null;
				confirmedSession = null;
				return;
			}

			if (availability.status === 'error') {
				registerOfferUsername = null;
				confirmedSession = null;
				showGameToast(availability.message, 'brick');
				return;
			}

			const result = await loginTrainer(trimmed);
			if (requestId !== lookupRequestId) return;

			if (result.status === 'not_found') {
				registerOfferUsername = trimmed;
				confirmedSession = null;
				if (embedded && onboardingUi) {
					onboardingUi.referenceSpriteSrc = DEFAULT_TRAINER_REFERENCE_SPRITE;
				}
				return;
			}

			if (result.status === 'invalid') {
				registerOfferUsername = null;
				confirmedSession = null;
				return;
			}

			if (result.status === 'error') {
				registerOfferUsername = null;
				confirmedSession = null;
				showGameToast(result.message, 'brick');
				return;
			}

			registerOfferUsername = null;
			confirmedSession = result.session;
			applySessionReference(result.session);
		} finally {
			if (requestId === lookupRequestId) {
				lookupBusy = false;
			}
		}
	}

	function attemptContinue() {
		if (setupBusy || !confirmedSession) return;
		onAccepted?.(confirmedSession);
	}

	function goToRegister() {
		const trimmed = registerOfferUsername ?? username.trim();
		if (validateUsername(trimmed)) return;
		void goto(`/register?username=${encodeURIComponent(trimmed)}`);
	}
</script>

{#snippet loginBody()}
	<div class="trainer-login" class:trainer-login--embedded={embedded}>
		<div class="trainer-login__name">
			<TrainerNameInput
				bind:username
				autofocus
				testId="trainer-login-username"
				onSubmit={attemptContinue}
				disabled={setupBusy}
			/>
		</div>

		{#if showRegisterOffer}
			<div class="trainer-login__register-offer">
				<GameButton variant="primary" class="trainer-login__register-button" onclick={goToRegister}>
					Register
				</GameButton>
			</div>
		{/if}

		<div class="trainer-login__dialog">
			{#if setupBusy}
				<GamePanel tone="status" class="hud-dialog-slot trainer-login__loading">
					<p class="trainer-login__loading-text" aria-live="polite">{LOOKUP_LOADING_TEXT}</p>
				</GamePanel>
			{:else if showRegisterOffer}
				<DialogBox text={dialogText} showCursor typewriter={false} />
			{:else}
				<DialogBox
					text={dialogText}
					showCursor
					typewriter={!confirmedSession}
					continueDisabled={!canContinue}
					continueTestId="trainer-login-continue"
					onContinue={attemptContinue}
				/>
			{/if}
		</div>
	</div>
{/snippet}

{#if embedded}
	{@render loginBody()}
{:else}
	<SceneFrame>
		{@render loginBody()}
	</SceneFrame>
{/if}

<style>
	.trainer-login {
		position: relative;
		min-height: 100dvh;
		--trainer-login-dialog-bottom: clamp(1.25rem, 5vh, 2.5rem);
	}

	.trainer-login--embedded {
		min-height: 100dvh;
		pointer-events: none;
	}

	.trainer-login--embedded .trainer-login__name,
	.trainer-login--embedded .trainer-login__dialog,
	.trainer-login--embedded .trainer-login__register-offer {
		pointer-events: auto;
	}

	.trainer-login__name {
		position: absolute;
		top: clamp(1.25rem, 5vh, 2.5rem);
		left: clamp(1.25rem, 4vw, 2.5rem);
		z-index: 2;
		max-width: calc(100% - 2.5rem);
	}

	:global(.trainer-login__loading) {
		--panel-status-accent: var(--vm-status-amber);
		--panel-status-surface: color-mix(in srgb, var(--vm-status-amber) 16%, var(--vm-panel-command-bg));
		animation: trainer-login-loading 900ms steps(2, end) infinite;
	}

	@keyframes trainer-login-loading {
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
		:global(.trainer-login__loading) {
			animation: none;
		}
	}

	.trainer-login__dialog {
		position: absolute;
		left: 50%;
		bottom: var(--trainer-login-dialog-bottom);
		transform: translateX(-50%);
		z-index: 2;
		width: var(--vm-hud-dialog-width);
		display: flex;
		justify-content: center;
	}

	.trainer-login__register-offer {
		position: absolute;
		left: 70%;
		bottom: calc(
			var(--trainer-login-dialog-bottom) + var(--vm-hud-dialog-slot-height) + var(--vm-space-sm)
		);
		transform: translateX(-50%);
		z-index: 2;
		width: 25%;
	}

	:global(.trainer-login__register-button) {
		width: 100%;
	}

	:global(.trainer-login__register-button .game-button__face) {
		width: 100%;
		justify-content: center;
		min-height: 52px;
	}
</style>
