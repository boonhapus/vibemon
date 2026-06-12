<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';

	import { fetchTrainerMe } from '$lib/domains/trainer/trainerApi';
	import {
		applyTrainerReferenceUrl,
		type TrainerOnboardingUi
	} from '$lib/domains/trainer/trainerOnboardingUi';
	import { setPendingUsername } from '$lib/domains/trainer/trainerRegisterStore.svelte';
	import TrainerRegistrationScene from '$lib/domains/trainer/TrainerRegistrationScene.svelte';

	const onboardingUi = getContext<TrainerOnboardingUi | undefined>('trainer-onboarding-ui');

	let sessionChecked = $state(false);

	onMount(async () => {
		const session = await fetchTrainerMe();
		if (session) {
			setPendingUsername(session.username);
			if (session.reference_url && onboardingUi) {
				applyTrainerReferenceUrl(onboardingUi, session.reference_url);
			}
			await goto('/hatch');
			return;
		}
		sessionChecked = true;
	});

	function handleAccepted(username: string) {
		setPendingUsername(username);
		goto('/hatch');
	}
</script>

<svelte:head>
	<title>Register · Vibemon</title>
</svelte:head>

{#if sessionChecked}
	<TrainerRegistrationScene embedded onAccepted={handleAccepted} />
{/if}
