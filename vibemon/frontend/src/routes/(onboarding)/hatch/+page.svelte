<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import TrainerConfigurationScene from '$lib/domains/trainer/TrainerConfigurationScene.svelte';
	import { readPendingUsername } from '$lib/domains/trainer/trainerRegisterStore.svelte';

	let username = $state('');

	onMount(() => {
		const pending = readPendingUsername();
		if (!pending) {
			void goto('/register');
			return;
		}
		username = pending;
	});
</script>

<svelte:head>
	<title>Hatch · Vibemon</title>
</svelte:head>

{#if username}
	<TrainerConfigurationScene embedded {username} />
{/if}
