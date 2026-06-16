<script lang="ts">
	import { onMount, setContext, type Snippet } from 'svelte';

	import TrainerReference from '$lib/domains/trainer/TrainerReference.svelte';
	import TrainerReferenceCamera from '$lib/domains/trainer/TrainerReferenceCamera.svelte';
	import { uploadTrainerReferenceWithSession } from '$lib/domains/trainer/trainerApi';
	import {
		applyTrainerReferenceUrl,
		createTrainerOnboardingUi,
		type TrainerOnboardingUi
	} from '$lib/domains/trainer/trainerOnboardingUi';
	import { gameSolarContext } from '$lib/domains/game/gameSolarContext.svelte';
	import { sceneBackgroundSrc } from '$lib/domains/game/sceneBackgrounds';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';

	const REGISTER_UI_KEY = 'trainer-onboarding-ui';

	let { children }: { children: Snippet } = $props();

	let registerUi = $state(createTrainerOnboardingUi());
	let registerBackgroundSrc = $derived(
		sceneBackgroundSrc('register', gameSolarContext.phase)
	);

	setContext<TrainerOnboardingUi>(REGISTER_UI_KEY, registerUi);

	onMount(() => {
		registerUi.referenceSpriteReady = true;
	});

	async function uploadRegisterReference(file: File): Promise<string | null> {
		registerUi.setupInProgress = true;
		registerUi.referenceGenerating = true;
		try {
			const result = await uploadTrainerReferenceWithSession(file, registerUi.registrationUsername);
			if (result.status === 'ok') {
				return result.session.reference_url;
			}

			showGameToast(result.message, result.status === 'needs_username' ? 'amber' : 'brick');
			return null;
		} finally {
			registerUi.referenceGenerating = false;
			registerUi.setupInProgress = false;
		}
	}
</script>

<SceneFrame backgroundSrc={registerBackgroundSrc} backgroundFadeMs={720}>
	<div class="register-scene">
		<div class="register-scene__reference" aria-hidden="true">
			<div class="register-scene__reference-stage">
				{#key registerUi.referenceSpriteSrc}
					<TrainerReference spriteSrc={registerUi.referenceSpriteSrc} />
				{/key}
				<TrainerReferenceCamera
					bind:hovered={registerUi.referenceHintVisible}
					disabled={registerUi.setupInProgress}
					uploadReference={uploadRegisterReference}
					onReferenceUrl={(referenceUrl) => {
						applyTrainerReferenceUrl(registerUi, referenceUrl);
					}}
				/>
			</div>
		</div>

		<div class="register-scene__content">
			{@render children()}
		</div>
	</div>
</SceneFrame>

<style>
	.register-scene {
		position: relative;
		min-height: 100dvh;
		--register-scene-stage-bottom: clamp(12.5rem, 24vh, 15.5rem);
		--register-scene-stage-platform-h: clamp(2.35rem, 5vw, 3.5rem);
	}

	.register-scene__reference {
		position: absolute;
		left: 70%;
		bottom: var(--register-scene-stage-bottom);
		z-index: 1;
		transform: translateX(-50%);
		pointer-events: auto;
	}

	.register-scene__reference-stage {
		position: relative;
	}

	.register-scene__reference :global(.trainer-reference) {
		--platform-h: var(--register-scene-stage-platform-h);
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

	.register-scene__content {
		position: relative;
		z-index: 2;
		min-height: 100dvh;
		pointer-events: none;
	}
</style>
