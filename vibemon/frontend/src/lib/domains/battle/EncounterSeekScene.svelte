<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import { fetchCrew } from '$lib/domains/trainer/hatchApi';
	import { sceneBackgroundSrc } from '$lib/domains/game/sceneBackgrounds';
	import { sceneSolarPhase } from '$lib/domains/game/gameSolarContext.svelte';
	import DialogBox from '$lib/ui/DialogBox.svelte';
	import GameButton from '$lib/ui/GameButton.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import { playGameAudio } from '$lib/ui/gameAudioStore.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';

	import { startEncounter } from './encounterApi';

	let loading = $state(true);
	let seeking = $state(false);
	let leadName = $state('');
	let leadId = $state<string | null>(null);
	let dialogText = $state('A wild vibe stirs nearby...');

	let backgroundSrc = $derived(sceneBackgroundSrc('battle', sceneSolarPhase()));
	let canSeek = $derived(!loading && !seeking && leadId !== null);

	onMount(async () => {
		try {
			const crew = await fetchCrew();
			const lead = crew.members.find((member) => member.crew_slot === 0) ?? crew.members[0];
			if (!lead) {
				dialogText = 'Your crew is empty — hatch a Vibemon first.';
				return;
			}
			leadId = lead.id;
			leadName = lead.nickname ?? lead.name;
			dialogText = `${leadName} scouts the wild.`;
		} catch {
			dialogText = 'Could not reach your crew.';
		} finally {
			loading = false;
		}
	});

	async function seekWild() {
		if (!canSeek) return;
		seeking = true;
		dialogText = 'Searching the wild...';
		playGameAudio('confirm');
		try {
			const started = await startEncounter(leadId!);
			await goto(`/battle/${started.battle.battle_id}`);
		} catch (error) {
			showGameToast(error instanceof Error ? error.message : 'Encounter failed.', 'brick');
			dialogText = `${leadName} found no wild Vibemon nearby.`;
		} finally {
			seeking = false;
		}
	}

	function handleDialogContinue() {
		void seekWild();
	}

	function handleWindowKeydown(event: KeyboardEvent) {
		if (!canSeek) return;
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			void seekWild();
		}
	}
</script>

<svelte:window onkeydown={handleWindowKeydown} />

<SceneFrame backgroundSrc={backgroundSrc} backgroundAlt="Wild encounter field">
	<div class="encounter-seek">
		<div class="encounter-seek__footer">
			<div class="encounter-seek__dialog">
				<DialogBox
					text={dialogText}
					showCursor={canSeek}
					onContinue={canSeek ? handleDialogContinue : undefined}
				/>
			</div>

			<div class="encounter-seek__actions">
				<GameButton variant="tertiary" onclick={() => goto('/deck/crew')}>Back</GameButton>
			</div>
		</div>
	</div>
</SceneFrame>

<style>
	.encounter-seek {
		position: relative;
		min-height: 100dvh;
		display: grid;
		grid-template-rows: minmax(0, 1fr) auto;
		padding-left: max(var(--vm-hud-bottom-inset), var(--vm-guide-corner-reserve));
		padding-right: max(var(--vm-hud-bottom-inset), var(--vm-settings-corner-reserve));
		padding-bottom: var(--vm-hud-bottom-inset);
		box-sizing: border-box;
	}

	.encounter-seek__footer {
		grid-row: 2;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: clamp(0.75rem, 2vw, 1rem);
		align-items: end;
	}

	.encounter-seek__dialog {
		display: flex;
		justify-content: flex-start;
	}

	.encounter-seek__dialog :global(.dialog-box) {
		width: min(100%, var(--vm-hud-dialog-width));
	}

	.encounter-seek__actions {
		display: flex;
		gap: clamp(0.5rem, 1.5vw, 0.75rem);
		flex-shrink: 0;
		justify-content: flex-end;
		align-items: end;
	}

	@media (max-width: 480px) {
		.encounter-seek__footer {
			grid-template-columns: 1fr;
			justify-items: stretch;
		}
	}
</style>
