<script lang="ts">
	import { getContext } from 'svelte';

	import DialogBox from '$lib/ui/DialogBox.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';
	import TrainerNameInput from '$lib/ui/TrainerNameInput.svelte';

	import { checkUsernameAvailability } from './trainerApi';
	import TrainerPortrait from './TrainerPortrait.svelte';
	import TrainerPortraitCamera from './TrainerPortraitCamera.svelte';
	import { validateUsername } from './validateUsername';

	const PORTRAIT_HINT_TEXT = `Tap the camera and we'll give your Trainer a new look.`;
	const ONBOARDING_UI_KEY = 'trainer-onboarding-ui';

	let {
		dialogText = 'Right on, Trainer! First.. what do folks call you?',
		showDialogCursor = true,
		typeDialogOnLoad = true,
		embedded = false,
		onAccepted
	}: {
		dialogText?: string;
		showDialogCursor?: boolean;
		typeDialogOnLoad?: boolean;
		embedded?: boolean;
		onAccepted?: (username: string) => void;
	} = $props();

	const onboardingUi = getContext<{ portraitHintVisible: boolean } | undefined>(ONBOARDING_UI_KEY);
	let username = $state('');
	let portraitHintVisible = $state(false);
	let checking = $state(false);
	let hintVisible = $derived(embedded ? (onboardingUi?.portraitHintVisible ?? false) : portraitHintVisible);
	let canContinue = $derived(!checking && validateUsername(username) === null);

	async function attemptContinue() {
		if (checking) return;
		const validationError = validateUsername(username);
		if (validationError) {
			showGameToast(validationError, 'amber');
			return;
		}
		checking = true;
		try {
			const result = await checkUsernameAvailability(username.trim());
			if (result.status === 'taken' || result.status === 'invalid') {
				showGameToast(result.message, 'amber');
				return;
			}
			if (result.status === 'error') {
				showGameToast(result.message, 'brick');
				return;
			}
			onAccepted?.(username.trim());
		} catch {
			showGameToast('Could not check that name. Try again.', 'brick');
		} finally {
			checking = false;
		}
	}
</script>

{#snippet registrationBody()}
	<div class="trainer-registration" class:trainer-registration--embedded={embedded}>
		<div class="trainer-registration__name">
			<TrainerNameInput bind:username autofocus onSubmit={attemptContinue} disabled={checking} />
		</div>

		{#if !embedded}
			<div class="trainer-registration__portrait">
				<div class="trainer-registration__portrait-stage">
					<TrainerPortrait />

					<TrainerPortraitCamera bind:hovered={portraitHintVisible} disabled={checking} />
				</div>
			</div>
		{/if}

		<div class="trainer-registration__dialog">
			{#if hintVisible}
				<GamePanel tone="status" class="hud-dialog-slot trainer-registration__portrait-hint">
					<p class="trainer-registration__portrait-hint-text">{PORTRAIT_HINT_TEXT}</p>
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
		/* Let the layout-owned portrait camera receive hover through this shell. */
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
	.trainer-registration__portrait {
		position: absolute;
		left: 70%;
		bottom: clamp(12rem, 23vh, 14.5rem);
		transform: translateX(-50%);
		z-index: 1;
	}
	.trainer-registration__portrait-stage {
		position: relative;
	}
	@media (max-width: 480px) {
		.trainer-registration__portrait {
			left: 72%;
			bottom: clamp(10rem, 20vh, 12rem);
		}
	}
	.trainer-registration__portrait-hint-text {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: var(--vm-hud-font-dialog);
		line-height: var(--vm-hud-dialog-line-height);
		color: inherit;
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
