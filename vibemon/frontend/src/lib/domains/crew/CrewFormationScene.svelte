<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	import HatchCandidatePanel from '$lib/domains/trainer/HatchCandidatePanel.svelte';
	import { fetchCrew, reorderCrew, type CrewMember } from '$lib/domains/trainer/hatchApi';
	import { fetchTrainerMe } from '$lib/domains/trainer/trainerApi';
	import DialogBox from '$lib/ui/DialogBox.svelte';
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';

	import CrewClockFormation from './CrewClockFormation.svelte';
	import CrewMemberPanel from './CrewMemberPanel.svelte';
	import { buildParty, mod, PARTY_SIZE, type PartySlot } from './crewSlots';

	const DEFAULT_TRAINER_SPRITE = '/game/sprites/trainer@128.png';
	const FIRST_VISIT_HINT_KEY = 'vm-crew-formation-hint-seen';
	const EMPTY_SEAT_HINT_MS = 2600;
	const POSITION_LABELS = ['Lead', '2', '3', '4', '5', '6'];

	let members = $state<CrewMember[]>([]);
	let loading = $state(true);
	let firstVisit = $state(false);
	let emptySeatHint = $state(false);
	let trainerSpriteSrc = $state(DEFAULT_TRAINER_SPRITE);
	let detailHint = $state<string | null>(null);
	let swapBusy = $state(false);

	/** Cumulative view rotation in slot units; mod 6 picks the active (front)
	 * crew_slot. Turning the ring never persists — only the position buttons do. */
	let rotation = $state(0);
	let emptySeatTimer: ReturnType<typeof setTimeout> | undefined;

	let party = $derived(buildParty(members));
	let filledCount = $derived(members.length);
	let activeSlot = $derived(party[mod(rotation, PARTY_SIZE)]);

	let dialogText = $derived.by(() => {
		if (loading) return 'Loading your crew...';
		if (filledCount === 0) return 'No Vibemon adopted yet.';
		if (emptySeatHint) return 'No Vibemon here — hatch one from your vibes.';
		if (detailHint) return detailHint;
		if (firstVisit) return 'Turn the crew, then set your active mon\'s position.';
		return 'Choose your active mon.';
	});

	function rotateBy(delta: number) {
		if (loading || filledCount === 0) return;
		rotation += delta;
	}

	function rotateSlotToFront(slot: PartySlot) {
		let delta = mod(slot.crewSlot - rotation, PARTY_SIZE);
		if (delta > PARTY_SIZE / 2) delta -= PARTY_SIZE;
		if (delta === 0) return;
		rotation += delta;
	}

	/** Move the active mon into `target`; if occupied, the two mons swap seats. */
	async function moveActiveToSlot(target: number) {
		const active = activeSlot;
		if (!active || active.empty || swapBusy) return;
		const from = active.crewSlot;
		if (target === from) return;

		const previous = members;
		members = members.map((member) => {
			if (member.crew_slot === from) return { ...member, crew_slot: target };
			if (member.crew_slot === target) return { ...member, crew_slot: from };
			return member;
		});
		// Keep the active mon at the front anchor after it changes seats.
		rotation += target - from;

		swapBusy = true;
		try {
			await reorderCrew(
				members.map((member) => ({ id: member.id, crew_slot: member.crew_slot }))
			);
		} catch (error) {
			members = previous;
			rotation -= target - from;
			const message = error instanceof Error ? error.message : 'Could not save your crew order.';
			showGameToast(message, 'brick');
		} finally {
			swapBusy = false;
		}
	}

	function handleTapEmpty() {
		if (emptySeatTimer) clearTimeout(emptySeatTimer);
		emptySeatHint = true;
		emptySeatTimer = setTimeout(() => {
			emptySeatHint = false;
			emptySeatTimer = undefined;
		}, EMPTY_SEAT_HINT_MS);
	}

	function handleCancel() {
		void goto('/hatch');
	}

	function handleRoster() {
		void goto('/deck/crew/roster');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.defaultPrevented) return;
		switch (event.key) {
			case 'ArrowLeft':
				event.preventDefault();
				rotateBy(1);
				break;
			case 'ArrowRight':
				event.preventDefault();
				rotateBy(-1);
				break;
			case 'Escape':
				event.preventDefault();
				handleCancel();
				break;
		}
	}

	onMount(() => {
		try {
			firstVisit = localStorage.getItem(FIRST_VISIT_HINT_KEY) === null;
			if (firstVisit) localStorage.setItem(FIRST_VISIT_HINT_KEY, '1');
		} catch {
			firstVisit = false;
		}

		void (async () => {
			try {
				const [crew, session] = await Promise.all([fetchCrew(), fetchTrainerMe()]);
				members = crew.members;
				if (session?.reference_url) {
					trainerSpriteSrc = session.reference_url;
				}
			} catch {
				showGameToast('Could not load your crew.', 'brick');
			} finally {
				loading = false;
			}
		})();

		return () => {
			if (emptySeatTimer) clearTimeout(emptySeatTimer);
		};
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<SceneFrame bandedTop="#8a9460" bandedBase="#4f5734" bandedShadow="#2f3622" class="scene-frame--crew-formation">
	<div class="crew-formation-scene">
		<div class="crew-formation-scene__play-area">
			<CrewClockFormation
				slots={party}
				{rotation}
				selectedId={activeSlot?.id ?? ''}
				{trainerSpriteSrc}
				onSelectSlot={rotateSlotToFront}
				onTapEmpty={handleTapEmpty}
			/>

			<div class="crew-formation-scene__stats">
				<CrewMemberPanel member={activeSlot ?? null} />
				<div class="crew-formation-scene__positions" role="group" aria-label="Crew position">
					{#each POSITION_LABELS as label, slotIndex (slotIndex)}
						<FreeFormButton
							ariaLabel={slotIndex === 0 ? 'Set as lead' : `Move to position ${label}`}
							disabled={loading || !activeSlot || activeSlot.empty || swapBusy}
							onclick={() => moveActiveToSlot(slotIndex)}
						>
							<GamePanel
								tone="command"
								class={[
									'crew-formation-scene__position-panel',
									activeSlot?.crewSlot === slotIndex &&
										'crew-formation-scene__position-panel--current'
								]
									.filter(Boolean)
									.join(' ')}
							>
								<span class="crew-formation-scene__position-label">{label}</span>
							</GamePanel>
						</FreeFormButton>
					{/each}
				</div>
				{#if activeSlot?.detail}
					{#key activeSlot.id}
						<HatchCandidatePanel candidate={activeSlot.detail} showActions={false} bind:detailHint />
					{/key}
				{/if}
			</div>
		</div>

		<div class="crew-formation-scene__footer">
			<div class="crew-formation-scene__dialog">
				<DialogBox text={dialogText} showCursor={false} typewriter={false} />
			</div>

			<div class="crew-formation-scene__footer-actions">
				<FreeFormButton ariaLabel="Open roster view" onclick={handleRoster}>
					<GamePanel tone="command" class="crew-formation-scene__footer-panel">
						<span class="crew-formation-scene__footer-label">Roster</span>
					</GamePanel>
				</FreeFormButton>

				<FreeFormButton ariaLabel="Cancel" onclick={handleCancel}>
					<GamePanel tone="command" class="crew-formation-scene__footer-panel">
						<span class="crew-formation-scene__footer-label">Cancel</span>
					</GamePanel>
				</FreeFormButton>
			</div>
		</div>
	</div>
</SceneFrame>

<style>
	.crew-formation-scene {
		position: relative;
		min-height: 100dvh;
		padding: clamp(1rem, 3vh, 1.75rem) clamp(1rem, 3vw, 1.75rem) clamp(1.25rem, 4vh, 2rem);
		display: grid;
		grid-template-rows: minmax(0, 1fr) auto;
		gap: clamp(0.85rem, 2.4vh, 1.35rem);
	}

	/* Spotlight mons scale up past their layout box; don't clip wings at the bezel. */
	:global(.scene-frame.scene-frame--crew-formation) {
		overflow: visible;
	}

	.crew-formation-scene__play-area {
		position: relative;
		min-height: 50dvh;
		overflow: visible;
	}

	/* Sit the ring left of center so the oval reads in the play area beside
	   the stats column. */
	.crew-formation-scene__play-area :global(.crew-formation) {
		--ring-x: 54%;
	}

	.crew-formation-scene__positions {
		display: grid;
		grid-template-columns: minmax(0, 1.6fr) repeat(5, minmax(0, 1fr));
		gap: clamp(0.25rem, 0.8vw, 0.45rem);
	}

	:global(.crew-formation-scene__position-panel) {
		min-width: 0;
	}

	:global(.crew-formation-scene__position-panel--current) {
		--panel-command-accent: var(--vm-mustard);
		--panel-command-surface: color-mix(in srgb, var(--vm-mustard) 22%, var(--vm-panel-command-bg));
	}

	.crew-formation-scene__position-label {
		display: block;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.75rem);
		line-height: 1.5;
		letter-spacing: 0.05em;
		text-align: center;
	}

	.crew-formation-scene__stats {
		position: absolute;
		top: clamp(0.25rem, 1.5vh, 0.75rem);
		left: clamp(0.25rem, 1vw, 0.75rem);
		z-index: 30;
		display: flex;
		flex-direction: column;
		gap: clamp(0.4rem, 1.2vh, 0.65rem);
		width: min(30rem, 42vw);
		max-width: calc(100% - 2rem);
		max-height: calc(100% - 1rem);
	}

	@media (max-width: 700px) {
		.crew-formation-scene__play-area :global(.crew-formation) {
			--ring-x: 48%;
		}

		.crew-formation-scene__stats {
			width: min(16rem, 86vw);
		}

		.crew-formation-scene__stats :global(.hatch-candidate-panel-shell) {
			display: none;
		}
	}

	.crew-formation-scene__footer {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: clamp(0.75rem, 2vw, 1rem);
		align-items: end;
	}

	.crew-formation-scene__dialog {
		display: flex;
		justify-content: flex-start;
	}

	.crew-formation-scene__dialog :global(.dialog-box) {
		width: min(100%, var(--vm-hud-dialog-width));
	}

	.crew-formation-scene__footer-actions {
		display: flex;
		gap: clamp(0.5rem, 1.5vw, 0.75rem);
		flex-shrink: 0;
	}

	:global(.crew-formation-scene__footer-panel) {
		min-width: clamp(5rem, 16vw, 7rem);
	}

	.crew-formation-scene__footer-label {
		display: block;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.6875rem, 2vw, 0.875rem);
		line-height: 1.5;
		letter-spacing: 0.06em;
		text-align: center;
	}

	@media (max-width: 480px) {
		.crew-formation-scene__footer {
			grid-template-columns: 1fr;
			justify-items: stretch;
		}

		.crew-formation-scene__footer-actions {
			justify-content: flex-end;
		}
	}
</style>
