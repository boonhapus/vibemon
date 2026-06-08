<script lang="ts">
	import { goto } from '$app/navigation';

	import { setPendingUsername } from '$lib/domains/trainer/trainerRegisterStore.svelte';
	import TrainerRegistrationScene from '$lib/domains/trainer/TrainerRegistrationScene.svelte';

	function handleAccepted(username: string) {
		setPendingUsername(username);
		goto('/hatch');
	}
</script>

<svelte:head>
	<title>Register · Vibemon</title>
</svelte:head>

<TrainerRegistrationScene embedded onAccepted={handleAccepted} />
