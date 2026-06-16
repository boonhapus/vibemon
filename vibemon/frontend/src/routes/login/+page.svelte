<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';

	import TrainerLoginScene from '$lib/domains/trainer/TrainerLoginScene.svelte';
	import { fetchTrainerMe, type TrainerSession } from '$lib/domains/trainer/trainerApi';
	import {
		applyTrainerReferenceUrl,
		type TrainerOnboardingUi
	} from '$lib/domains/trainer/trainerOnboardingUi';
	import { setPendingUsername } from '$lib/domains/trainer/trainerRegisterStore.svelte';

	const loginUi = getContext<TrainerOnboardingUi | undefined>('trainer-onboarding-ui');

	let sessionChecked = $state(false);

	function redirectForSession(session: TrainerSession) {
		setPendingUsername(session.username);
		if (session.reference_url && loginUi) {
			applyTrainerReferenceUrl(loginUi, session.reference_url);
		}
		if (session.crew_count > 0) {
			void goto('/deck/crew');
			return;
		}
		void goto('/hatch');
	}

	onMount(async () => {
		const session = await fetchTrainerMe();
		if (session) {
			redirectForSession(session);
			return;
		}
		sessionChecked = true;
	});

	function handleAccepted(session: TrainerSession) {
		redirectForSession(session);
	}
</script>

<svelte:head>
	<title>Login · Vibemon</title>
</svelte:head>

{#if sessionChecked}
	<TrainerLoginScene embedded onAccepted={handleAccepted} />
{/if}
