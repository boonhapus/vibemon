<script lang="ts">
	import { onMount, setContext, type Snippet } from 'svelte';

	import TrainerReference from '$lib/domains/trainer/TrainerReference.svelte';
	import {
		createTrainerOnboardingUi,
		type TrainerOnboardingUi
	} from '$lib/domains/trainer/trainerOnboardingUi';
	import { sceneSolarPhase } from '$lib/domains/game/gameSolarContext.svelte';
	import { sceneBackgroundSrc } from '$lib/domains/game/sceneBackgrounds';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';

	const LOGIN_UI_KEY = 'trainer-onboarding-ui';

	let { children }: { children: Snippet } = $props();

	let loginUi = $state(createTrainerOnboardingUi());
	let loginBackgroundSrc = $derived(sceneBackgroundSrc('register', sceneSolarPhase()));

	setContext<TrainerOnboardingUi>(LOGIN_UI_KEY, loginUi);

	onMount(() => {
		loginUi.referenceSpriteReady = true;
	});
</script>

<SceneFrame backgroundSrc={loginBackgroundSrc} backgroundFadeMs={720}>
	<div class="login-scene">
		<div class="login-scene__reference" aria-hidden="true">
			<div class="login-scene__reference-stage">
				{#key loginUi.referenceSpriteSrc}
					<TrainerReference spriteSrc={loginUi.referenceSpriteSrc} />
				{/key}
			</div>
		</div>

		<div class="login-scene__content">
			{@render children()}
		</div>
	</div>
</SceneFrame>

<style>
	.login-scene {
		position: relative;
		min-height: 100dvh;
		--login-scene-stage-bottom: clamp(12.5rem, 24vh, 15.5rem);
		--login-scene-stage-platform-h: clamp(2.35rem, 5vw, 3.5rem);
	}

	.login-scene__reference {
		position: absolute;
		left: 70%;
		bottom: var(--login-scene-stage-bottom);
		z-index: 1;
		transform: translateX(-50%);
		pointer-events: none;
	}

	.login-scene__reference-stage {
		position: relative;
	}

	.login-scene__reference :global(.trainer-reference) {
		--platform-h: var(--login-scene-stage-platform-h);
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

	.login-scene__content {
		position: relative;
		z-index: 2;
		min-height: 100dvh;
		pointer-events: none;
	}
</style>
