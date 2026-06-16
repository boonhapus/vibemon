<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Tween, prefersReducedMotion } from 'svelte/motion';
	import { linear } from 'svelte/easing';

	import { fetchCrew, reorderCrew, type CrewMember } from '$lib/domains/trainer/hatchApi';
	import { fetchTrainerMe } from '$lib/domains/trainer/trainerApi';
	import DialogBox from '$lib/ui/DialogBox.svelte';
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import { gameSolarContext } from '$lib/domains/game/gameSolarContext.svelte';
	import { sceneBackgroundSrc } from '$lib/domains/game/sceneBackgrounds';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import { playGameAudio } from '$lib/ui/gameAudioStore.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';

	import CrewClockFormation from './CrewClockFormation.svelte';
	import CrewShowcasePanel from './CrewShowcasePanel.svelte';
	import { buildSwapPairs, rotationDeltaToFront } from './crewRingMath';
	import { buildParty, mod, PARTY_SIZE, type PartySlot, type SwapAnimPair } from './crewSlots';

	const DEFAULT_TRAINER_SPRITE = '/game/sprites/trainer@128.png';
	const INTRO_RITUAL_KEY = 'vm-crew-formation-intro-seen';
	const HINT_KEY = 'vm-crew-formation-hint-seen';
	const EMPTY_SEAT_HINT_MS = 2600;
	const SWAP_ANIM_MS = 600;
	const POSITION_LABELS = ['Lead', '2', '3', '4', '5', '6'] as const;

	let members = $state<CrewMember[]>([]);
	let loading = $state(true);
	let showHint = $state(false);
	let introRitual = $state<'full' | 'short' | 'none'>('short');
	let introDone = $state(false);
	let emptySeatHint = $state(false);
	let trainerSpriteSrc = $state(DEFAULT_TRAINER_SPRITE);
	let trainerName = $state('');
	let detailHint = $state<string | null>(null);
	let panelTab = $state<'stats' | 'moves' | 'sources' | 'story'>('stats');
	let swapBusy = $state(false);
	let swapMode = $state(false);
	let swapAnimPairs = $state<SwapAnimPair[] | null>(null);
	let swapConfirm = $state<string | null>(null);

	let rotation = $state(0);
	let emptySeatTimer: ReturnType<typeof setTimeout> | undefined;
	let panelShell = $state<HTMLDivElement | null>(null);
	let lastHintSlotId = $state('');

	const swapProgress = new Tween(0, { duration: SWAP_ANIM_MS, easing: linear });
	let swapAnimation = $derived(
		swapAnimPairs ? { pairs: swapAnimPairs, progress: swapProgress.current } : null
	);
	let crewBackgroundSrc = $derived(sceneBackgroundSrc('crew-showcase', gameSolarContext.phase));

	let party = $derived(buildParty(members));
	let filledCount = $derived(members.length);
	let activeSlot = $derived(party[mod(rotation, PARTY_SIZE)]);

	let dialogBlocked = $derived(
		Boolean(swapConfirm) ||
			loading ||
			filledCount === 0 ||
			(Boolean(swapMode && activeSlot && !activeSlot.empty)) ||
			emptySeatHint
	);

	let dialogText = $derived.by(() => {
		if (swapConfirm) return swapConfirm;
		if (loading) return 'Gathering your crew...';
		if (filledCount === 0) return 'No Vibemon in your crew yet.';
		if (swapMode && activeSlot && !activeSlot.empty) {
			return `Where should ${activeSlot.name} stand?`;
		}
		if (emptySeatHint) return 'Open seat — hatch a Vibemon from your vibes.';
		if (!introDone && filledCount > 0) return 'Your crew gathers.';
		if (showHint && introDone) return 'Turn the ring to review your crew.';
		return 'Choose who to look at.';
	});

	function handleDetailHintChange(hint: string | null) {
		detailHint = hint;
	}

	function clearDetailHint() {
		detailHint = null;
	}

	function rotateBy(delta: number) {
		if (loading || filledCount === 0 || swapMode || swapBusy || !introDone) return;
		clearDetailHint();
		rotation += delta;
	}

	function rotateSlotToFront(slot: PartySlot) {
		if (swapMode || swapBusy || !introDone) return;
		const delta = rotationDeltaToFront(rotation, slot.crewSlot);
		if (delta === 0) return;
		clearDetailHint();
		rotation += delta;
	}

	function slotLabel(slotIndex: number): string {
		return POSITION_LABELS[slotIndex] ?? String(slotIndex + 1);
	}

	async function animateSwap(pairs: SwapAnimPair[]): Promise<void> {
		if (pairs.length === 0) return;
		swapAnimPairs = pairs;
		await swapProgress.set(1, {
			duration: prefersReducedMotion.current ? 0 : SWAP_ANIM_MS
		});
		swapAnimPairs = null;
		await swapProgress.set(0, { duration: 0 });
	}

	async function moveActiveToSlot(target: number) {
		const active = activeSlot;
		if (!active || active.empty || swapBusy) return;
		const from = active.crewSlot;
		if (target === from) {
			if (swapMode) swapMode = false;
			return;
		}

		const previous = members;
		const pairs = buildSwapPairs(active.id, from, target, members);
		const occupant = members.find((member) => member.crew_slot === target);
		const activeName = active.name;
		const targetLabel = slotLabel(target);

		swapBusy = true;
		swapMode = false;

		try {
			await animateSwap(pairs);

			members = members.map((member) => {
				if (member.crew_slot === from) return { ...member, crew_slot: target };
				if (member.crew_slot === target) return { ...member, crew_slot: from };
				return member;
			});
			rotation += target - from;

			await reorderCrew(
				members.map((member) => ({ id: member.id, crew_slot: member.crew_slot }))
			);

			playGameAudio('swap-commit');
			swapConfirm =
				occupant && occupant.id !== active.id
					? `${activeName} and ${(occupant.nickname?.trim() || occupant.name).toUpperCase()} trade places.`
					: `${activeName} takes the ${targetLabel} spot.`;
			setTimeout(() => {
				if (swapConfirm?.includes(activeName)) swapConfirm = null;
			}, 2400);
		} catch (error) {
			members = previous;
			const message = error instanceof Error ? error.message : 'Could not save your crew order.';
			showGameToast(message, 'brick');
		} finally {
			swapBusy = false;
		}
	}

	function handleSelectSwapTarget(slotIndex: number) {
		void moveActiveToSlot(slotIndex);
	}

	function toggleSwapMode() {
		if (loading || !activeSlot || activeSlot.empty || swapBusy || !introDone) return;
		swapMode = !swapMode;
		if (swapMode) panelTab = 'stats';
	}

	function handleTapEmpty() {
		if (emptySeatTimer) clearTimeout(emptySeatTimer);
		emptySeatHint = true;
		emptySeatTimer = setTimeout(() => {
			emptySeatHint = false;
			emptySeatTimer = undefined;
		}, EMPTY_SEAT_HINT_MS);
	}

	function handleEmptyHatch() {
		void goto('/hatch');
	}

	function handleCancel() {
		if (swapMode) {
			swapMode = false;
			return;
		}
		void goto('/hatch');
	}

	function handleRoster() {
		void goto('/deck/crew/roster');
	}

	function handleIntroComplete() {
		introDone = true;
	}

	function handleRotationSettled() {
		playGameAudio('menu-nav');
	}

	function handleSpotlightGreet() {
		playGameAudio('confirm');
	}

	function focusShowcase() {
		panelTab = 'stats';
		panelShell?.querySelector<HTMLElement>('.crew-showcase-panel__tab')?.focus();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.defaultPrevented) return;

		if (event.key >= '1' && event.key <= '6') {
			event.preventDefault();
			const slotIndex = Number(event.key) - 1;
			if (swapMode) {
				void moveActiveToSlot(slotIndex);
				return;
			}
			const slot = party[slotIndex];
			if (slot) rotateSlotToFront(slot);
			return;
		}

		switch (event.key) {
			case 'ArrowLeft':
				event.preventDefault();
				rotateBy(-1);
				break;
			case 'ArrowRight':
				event.preventDefault();
				rotateBy(1);
				break;
			case 'Enter':
				event.preventDefault();
				if (swapMode) return;
				focusShowcase();
				break;
			case 'm':
			case 'M':
				event.preventDefault();
				toggleSwapMode();
				break;
			case 'Escape':
				event.preventDefault();
				handleCancel();
				break;
		}
	}

	onMount(() => {
		let introSeen = true;
		try {
			introSeen = localStorage.getItem(INTRO_RITUAL_KEY) !== null;
			if (!introSeen) localStorage.setItem(INTRO_RITUAL_KEY, '1');
			showHint = localStorage.getItem(HINT_KEY) === null;
			if (showHint) localStorage.setItem(HINT_KEY, '1');
		} catch {
			introSeen = true;
			showHint = false;
		}

		void (async () => {
			try {
				const [crew, session] = await Promise.all([fetchCrew(), fetchTrainerMe()]);
				members = crew.members;
				if (session?.reference_url) {
					trainerSpriteSrc = session.reference_url;
				}
				if (session?.username) {
					trainerName = session.username;
				}
				if (crew.members.length === 0) {
					introRitual = 'none';
					introDone = true;
				} else {
					introRitual = introSeen ? 'short' : 'full';
				}
			} catch {
				showGameToast('Could not load your crew.', 'brick');
				introDone = true;
			} finally {
				loading = false;
			}
		})();

		return () => {
			if (emptySeatTimer) clearTimeout(emptySeatTimer);
		};
	});

	$effect(() => {
		const slotId = activeSlot?.id ?? '';
		if (slotId === lastHintSlotId) return;
		lastHintSlotId = slotId;
		clearDetailHint();
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<SceneFrame backgroundSrc={crewBackgroundSrc} class="scene-frame--crew-formation">
	<div class="crew-formation-scene">
		<div class="crew-formation-scene__stats">
			{#if activeSlot?.detail}
				<div bind:this={panelShell}>
					{#key activeSlot.id}
						<CrewShowcasePanel
							candidate={activeSlot.detail}
							level={activeSlot.level}
							currentHp={activeSlot.currentHp}
							maxHp={activeSlot.maxHp}
							onDetailHintChange={handleDetailHintChange}
							bind:activeTab={panelTab}
						/>
					{/key}
				</div>
			{/if}
		</div>

		<div class="crew-formation-scene__play-area">
			<CrewClockFormation
				slots={party}
				{rotation}
				selectedId={activeSlot?.id ?? ''}
				{trainerSpriteSrc}
				{trainerName}
				{swapMode}
				{swapBusy}
				introReady={!loading}
				{introRitual}
				{swapAnimation}
				onSelectSlot={rotateSlotToFront}
				onTapEmpty={handleTapEmpty}
				onTapEmptyHatch={handleEmptyHatch}
				onSelectSwapTarget={handleSelectSwapTarget}
				onIntroComplete={handleIntroComplete}
				onRotationSettled={handleRotationSettled}
				onSpotlightGreet={handleSpotlightGreet}
			/>
		</div>

		<div class="crew-formation-scene__footer">
			<div class="crew-formation-scene__dialog">
				{#if detailHint && !dialogBlocked}
					<GamePanel tone="status" class="hud-dialog-slot crew-formation-scene__detail-hint">
						<p>{detailHint}</p>
					</GamePanel>
				{:else}
					<DialogBox text={dialogText} showCursor={false} typewriter={false} />
				{/if}
			</div>

			<div class="crew-formation-scene__footer-actions">
				{#if swapMode}
					<div class="crew-formation-scene__positions" role="group" aria-label="Crew position">
						{#each POSITION_LABELS as label, slotIndex (slotIndex)}
							<FreeFormButton
								ariaLabel={slotIndex === 0 ? 'Set as lead' : `Move to position ${label}`}
								disabled={loading || !activeSlot || activeSlot.empty || swapBusy || !introDone}
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
				{/if}

				<FreeFormButton
					ariaLabel="Move crew member to another seat"
					disabled={loading || !activeSlot || activeSlot.empty || swapBusy || !introDone}
					onclick={toggleSwapMode}
				>
					<GamePanel
						tone="command"
						class={[
							'crew-formation-scene__footer-panel',
							swapMode && 'crew-formation-scene__footer-panel--active'
						]
							.filter(Boolean)
							.join(' ')}
					>
						<span class="crew-formation-scene__footer-label">Move</span>
					</GamePanel>
				</FreeFormButton>

				<FreeFormButton ariaLabel="Open roster view" onclick={handleRoster}>
					<GamePanel tone="command" class="crew-formation-scene__footer-panel">
						<span class="crew-formation-scene__footer-label">Roster</span>
					</GamePanel>
				</FreeFormButton>

				<FreeFormButton ariaLabel="Cancel" onclick={handleCancel}>
					<GamePanel tone="command" class="crew-formation-scene__footer-panel">
						<span class="crew-formation-scene__footer-label">{swapMode ? 'Back' : 'Cancel'}</span>
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
		padding-left: var(--vm-hud-bottom-inset);
		padding-right: max(var(--vm-hud-bottom-inset), var(--vm-settings-corner-reserve));
		padding-bottom: var(--vm-hud-bottom-inset);
		display: grid;
		grid-template-rows: minmax(0, 1fr) auto;
		gap: clamp(0.85rem, 2.4vh, 1.35rem);
	}

	:global(.scene-frame.scene-frame--crew-formation) {
		overflow: visible;
	}

	.crew-formation-scene__stats {
		position: absolute;
		top: var(--vm-bezel-w);
		left: var(--vm-bezel-w);
		z-index: 30;
		display: flex;
		flex-direction: column;
		width: min(var(--vm-hud-candidate-rail-max-width), calc(100% - var(--vm-bezel-w) * 2));
		height: min(
			var(--vm-hud-candidate-panel-min-height),
			calc(100dvh - var(--vm-bezel-w) * 2 - clamp(1.25rem, 4vh, 2rem))
		);
		pointer-events: auto;
	}

	.crew-formation-scene__stats > div {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		height: 100%;
	}

	.crew-formation-scene__play-area {
		position: relative;
		min-height: 50dvh;
		overflow: visible;
	}

	.crew-formation-scene__play-area :global(.crew-formation) {
		--ring-x: 54%;
	}

	.crew-formation-scene__positions {
		display: grid;
		grid-template-columns: repeat(6, minmax(0, 1fr));
		gap: clamp(0.25rem, 0.8vw, 0.45rem);
		width: 100%;
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

	@media (max-width: 700px) {
		.crew-formation-scene__play-area :global(.crew-formation) {
			--ring-x: 48%;
		}

		.crew-formation-scene__stats {
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
		flex-wrap: wrap;
		justify-content: flex-end;
		align-items: end;
	}

	:global(.crew-formation-scene__footer-panel) {
		min-width: clamp(4.5rem, 14vw, 6.5rem);
	}

	:global(.crew-formation-scene__footer-panel--active) {
		--panel-command-accent: var(--vm-mustard);
		--panel-command-surface: color-mix(in srgb, var(--vm-mustard) 22%, var(--vm-panel-command-bg));
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
	}
</style>
