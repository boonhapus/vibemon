<script lang="ts">
	import { page } from '$app/state';
	import BattleScene from '$lib/domains/battle/BattleScene.svelte';

	const battleId = $derived(page.params.id ?? '');
</script>

<svelte:head>
	<title>Battle · Vibemon</title>
</svelte:head>

{#if battleId}
	{#key battleId}
		<BattleScene {battleId} />
	{/key}
{/if}
