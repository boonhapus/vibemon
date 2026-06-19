<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Tween, prefersReducedMotion } from 'svelte/motion';
	import { linear } from 'svelte/easing';

	import { fetchCrew, reorderCrew, type CrewMember } from '$lib/domains/trainer/hatchApi';
	import { fetchTrainerMe } from '$lib/domains/trainer/trainerApi';
	import DialogBox from '$lib/ui/DialogBox.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import { sceneSolarPhase } from '$lib/domains/game/gameSolarContext.svelte';
	import { sceneBackgroundSrc } from '$lib/domains/game/sceneBackgrounds';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import { playGameAudio } from '$lib/ui/gameAudioStore.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';

	import CrewClockFormation from './CrewClockFormation.svelte';
	import CrewFormationMenu from './CrewFormationMenu.svelte';
	import CrewShowcasePanel from './CrewShowcasePanel.svelte';
	import {
		CREW_FORMATION_COMMANDS,
		CREW_SWAP_EMPTY_TOAST,
		crewMenuHint,
		navigateCrewPositionGrid,
		type CrewCommandId
	} from './crewFormationMenu';
	import {
		CREW_COMMAND_MENU_INDEX,
		resolveCrewFormationKeydown,
		resolveCrewFormationKeyup
	} from './crewFormationKeyboard';
	import { navigateBattleGrid } from '$lib/domains/battle/battleGridMenu';
	import { isMacOs } from '$lib/ui/platform';
	import { buildSwapPairs, rotationDeltaToFront } from './crewRingMath';
	import { buildParty, mod, PARTY_SIZE, type PartySlot, type SwapAnimPair } from './crewSlots';

	const DEFAULT_TRAINER_SPRITE = '/game/sprites/trainer@128.png';
	const INTRO_RITUAL_KEY = 'vm-crew-formation-intro-seen';
	const EMPTY_SEAT_HINT_MS = 2600;
	const SWAP_ANIM_MS = 600;
	const POSITION_LABELS = ['Lead', '2', '3', '4', '5', '6'] as const;

	let members = $state<CrewMember[]>([]);
	let loading = $state(true);
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
	let menuIndex = $state(0);
	let contextHeld = $state(false);

	let rotation = $state(0);
	let emptySeatTimer: ReturnType<typeof setTimeout> | undefined;
	let panelShell = $state<HTMLDivElement | null>(null);
	let lastHintSlotId = $state('');

	const swapProgress = new Tween(0, { duration: SWAP_ANIM_MS, easing: linear });
	let swapAnimation = $derived(
		swapAnimPairs ? { pairs: swapAnimPairs, progress: swapProgress.current } : null
	);
	let crewBackgroundSrc = $derived(sceneBackgroundSrc('crew-showcase', sceneSolarPhase()));

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

	let showControlsHint = $derived(
		!contextHeld &&
			!swapConfirm &&
			!loading &&
			filledCount > 0 &&
			introDone &&
			!swapMode &&
			!emptySeatHint
	);

	let dialogText = $derived.by(() => {
		if (contextHeld && !swapConfirm && !loading) {
			return crewMenuHint(swapMode ? 'position' : 'command', menuIndex);
		}
		if (swapConfirm) return swapConfirm;
		if (loading) return 'Gathering your crew...';
		if (filledCount === 0) return 'No Vibemon in your crew yet.';
		if (swapMode && activeSlot && !activeSlot.empty) {
			return `Where should ${activeSlot.name} stand?`;
		}
		if (emptySeatHint) return 'Open seat. Hatch a Vibemon from your vibes.';
		if (!introDone && filledCount > 0) return 'Your crew gathers.';
		return '';
	});

	let swapDisabled = $derived(
		loading || !activeSlot || activeSlot.empty || swapBusy || !introDone
	);

	let spinModifierLabel = $derived(isMacOs() ? 'OPTION' : 'ALT');
	let spinControlsHint = $derived(
		`Hold ${spinModifierLabel} and use the arrow keys to spin the ring.`
	);

	function notifySwapBlocked() {
		if (!activeSlot || activeSlot.empty) {
			showGameToast(CREW_SWAP_EMPTY_TOAST, 'amber');
		}
	}

	function handleDetailHintChange(hint: string | null) {
		detailHint = hint;
	}

	function clearDetailHint() {
		detailHint = null;
	}

	function rotateBy(delta: number) {
		if (loading || filledCount === 0 || swapBusy || !introDone) return;
		clearDetailHint();
		rotation += delta;
	}

	function rotateSlotToFront(slot: PartySlot) {
		if (swapBusy || !introDone) return;
		const delta = rotationDeltaToFront(rotation, slot.crewSlot);
		if (delta === 0) return;
		clearDetailHint();
		rotation += delta;
	}

	function spinRingToSlot(slotIndex: number) {
		if (loading || filledCount === 0 || swapBusy || !introDone) return;
		const slot = party[slotIndex];
		if (slot) rotateSlotToFront(slot);
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
		menuIndex = 0;

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

	function tryToggleSwapMode() {
		if (loading || swapBusy || !introDone) return;
		if (!activeSlot || activeSlot.empty) {
			notifySwapBlocked();
			return;
		}
		swapMode = !swapMode;
		menuIndex = 0;
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
			menuIndex = 0;
			return;
		}
		void goto('/hatch');
	}

	function handleRoster() {
		void goto('/deck/crew/roster');
	}

	function handleSeekWild() {
		void goto('/encounters');
	}

	function handleCommand(command: CrewCommandId) {
		switch (command) {
			case 'swap':
				tryToggleSwapMode();
				break;
			case 'wild':
				handleSeekWild();
				break;
			case 'roster':
				handleRoster();
				break;
			case 'cancel':
				handleCancel();
				break;
		}
	}

	function confirmMenuSelection() {
		if (swapMode) {
			void moveActiveToSlot(menuIndex);
			return;
		}

		const command = CREW_FORMATION_COMMANDS[menuIndex];
		if (!command) return;
		if (command.id === 'swap' && swapDisabled) {
			notifySwapBlocked();
			return;
		}
		handleCommand(command.id);
	}

	function navigateMenu(key: string) {
		menuIndex = swapMode
			? navigateCrewPositionGrid(menuIndex, key)
			: navigateBattleGrid(menuIndex, key);
		playGameAudio('menu-nav');
	}

	function handleKeydown(event: KeyboardEvent) {
		const action = resolveCrewFormationKeydown(event, { swapMode });
		if (!action) return;

		switch (action.type) {
			case 'hold-read':
				contextHeld = true;
				return;
			case 'consume':
				event.preventDefault();
				return;
		}

		if (swapBusy || loading) return;

		switch (action.type) {
			case 'ring-step':
				event.preventDefault();
				rotateBy(action.delta);
				return;
			case 'ring-slot':
				event.preventDefault();
				spinRingToSlot(action.slotIndex);
				return;
			case 'menu-nav':
				event.preventDefault();
				navigateMenu(action.key);
				return;
			case 'menu-confirm':
				event.preventDefault();
				confirmMenuSelection();
				return;
			case 'position-pick':
				event.preventDefault();
				menuIndex = action.slotIndex;
				void moveActiveToSlot(action.slotIndex);
				return;
			case 'command': {
				event.preventDefault();
				menuIndex = CREW_COMMAND_MENU_INDEX[action.commandId];
				if (action.commandId === 'swap' && swapDisabled) {
					notifySwapBlocked();
					return;
				}
				handleCommand(action.commandId);
				return;
			}
		}
	}

	function handleKeyup(event: KeyboardEvent) {
		if (resolveCrewFormationKeyup(event) === 'release-read') {
			contextHeld = false;
		}
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

	onMount(() => {
		let introSeen = true;
		try {
			introSeen = localStorage.getItem(INTRO_RITUAL_KEY) !== null;
			if (!introSeen) localStorage.setItem(INTRO_RITUAL_KEY, '1');
		} catch {
			introSeen = true;
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

<svelte:window onkeydown={handleKeydown} onkeyup={handleKeyup} />

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
							xp={activeSlot.xp}
							xpToNext={activeSlot.xpToNext}
							xpBarRatio={activeSlot.xpBarRatio}
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
			<div class="crew-formation-scene__dialog-bar">
				<div class="crew-formation-scene__dialog">
					{#if detailHint && !dialogBlocked}
						<GamePanel tone="status" class="hud-dialog-slot battle-hud-dialog crew-formation-scene__detail-hint">
							<p>{detailHint}</p>
						</GamePanel>
					{:else if showControlsHint}
						<DialogBox
							class="battle-hud-dialog"
							text={spinControlsHint}
							showCursor={false}
							typewriter={false}
						>
							{#snippet children()}
								<p class="crew-formation-scene__controls-copy">
									Hold <span class="crew-formation-scene__hotkey">{spinModifierLabel}</span> and use the
									<span class="crew-formation-scene__hotkey">arrow keys</span> to spin the ring!
								</p>
							{/snippet}
						</DialogBox>
					{:else}
						<DialogBox class="battle-hud-dialog" text={dialogText} showCursor={false} typewriter={false} />
					{/if}
				</div>

				<div class="crew-formation-scene__menu-overlay">
					<CrewFormationMenu
						mode={swapMode ? 'position' : 'command'}
						selected={menuIndex}
						{contextHeld}
						swapDisabled={swapDisabled}
						positionDisabled={swapDisabled}
						currentSlotIndex={activeSlot?.crewSlot ?? null}
						onSelect={(index) => {
							menuIndex = index;
							playGameAudio('menu-nav');
						}}
						onCommand={handleCommand}
						onSwapBlocked={notifySwapBlocked}
						onPosition={(slotIndex) => moveActiveToSlot(slotIndex)}
					/>
				</div>
			</div>
		</div>
	</div>
</SceneFrame>

<style>
	.crew-formation-scene {
		--vm-battle-hud-inset: var(--vm-hud-bottom-inset);
		--vm-battle-hud-column-width: 30%;

		position: relative;
		min-height: 100dvh;
		padding-left: var(--vm-battle-hud-inset);
		padding-right: var(--vm-battle-hud-inset);
		padding-bottom: var(--vm-battle-hud-inset);
		box-sizing: border-box;
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
		min-height: 0;
		overflow: visible;
	}

	.crew-formation-scene__play-area :global(.crew-formation) {
		--ring-x: 54%;
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
		position: relative;
		z-index: 3;
		height: var(--vm-hud-dialog-slot-height);
		width: 100%;
		overflow: hidden;
	}

	.crew-formation-scene__dialog-bar {
		position: relative;
		width: 100%;
		height: 100%;
	}

	.crew-formation-scene__dialog {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: stretch;
	}

	.crew-formation-scene__dialog :global(.dialog-box.battle-hud-dialog),
	.crew-formation-scene__dialog :global(.game-panel.battle-hud-dialog) {
		display: flex;
		flex: 1 1 auto;
		flex-direction: column;
		align-self: stretch;
		width: 100%;
		height: 100%;
		min-height: 0;
		min-width: 0;
	}

	.crew-formation-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__frame),
	.crew-formation-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__inset),
	.crew-formation-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__surface),
	.crew-formation-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__content),
	.crew-formation-scene__dialog :global(.game-panel.battle-hud-dialog .game-panel__frame),
	.crew-formation-scene__dialog :global(.game-panel.battle-hud-dialog .game-panel__inset),
	.crew-formation-scene__dialog :global(.game-panel.battle-hud-dialog .game-panel__surface),
	.crew-formation-scene__dialog :global(.game-panel.battle-hud-dialog .game-panel__content) {
		display: flex;
		flex: 1 1 auto;
		flex-direction: column;
		width: 100%;
		height: 100%;
		min-height: 0;
		min-width: 0;
		box-sizing: border-box;
	}

	.crew-formation-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__frame),
	.crew-formation-scene__dialog :global(.game-panel.battle-hud-dialog .game-panel__frame) {
		box-shadow: none;
	}

	.crew-formation-scene__dialog :global(.dialog-box.battle-hud-dialog .game-panel__surface) {
		flex: 1 1 auto;
	}

	.crew-formation-scene__dialog :global(.dialog-box.battle-hud-dialog .dialog-box__content) {
		flex: 1 1 auto;
		height: auto;
		min-height: 0;
	}

	.crew-formation-scene__dialog :global(.hud-dialog-slot) {
		width: 100%;
		height: 100%;
	}

	/* Keep hover-hint text clear of the command menu overlaying the right side:
	   reserve its width and let the copy wrap to a second/third line instead of
	   sliding under (and being clipped by) the actions panel. */
	.crew-formation-scene__dialog :global(.crew-formation-scene__detail-hint .game-panel__content) {
		justify-content: center;
		padding-right: calc(var(--vm-battle-hud-column-width) + 0.85rem);
	}

	.crew-formation-scene__dialog :global(.crew-formation-scene__detail-hint p) {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: var(--vm-hud-font-dialog-ui);
		line-height: var(--vm-hud-dialog-line-height);
		color: inherit;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		overflow: hidden;
	}

	.crew-formation-scene__menu-overlay {
		position: absolute;
		top: 0;
		right: 0;
		bottom: 0;
		z-index: 2;
		display: flex;
		flex-direction: column;
		width: var(--vm-battle-hud-column-width);
	}

	.crew-formation-scene__menu-overlay :global(.crew-formation-menu.game-panel) {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		width: 100%;
		height: 100%;
		min-height: 0;
		box-shadow: none;
	}

	.crew-formation-scene__menu-overlay :global(.crew-formation-menu .game-panel__frame) {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		box-shadow: none;
	}

	.crew-formation-scene__menu-overlay :global(.crew-formation-menu .game-panel__inset),
	.crew-formation-scene__menu-overlay :global(.crew-formation-menu .game-panel__surface),
	.crew-formation-scene__menu-overlay :global(.crew-formation-menu .game-panel__content) {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}

	@media (max-width: 480px) {
		.crew-formation-scene {
			--vm-battle-hud-column-width: 34%;
		}
	}

	.crew-formation-scene__controls-copy {
		margin: 0;
		flex: 1;
		min-width: 0;
		font-family: var(--vm-font-ui);
		font-weight: 400;
		font-size: var(--vm-hud-font-dialog-ui);
		line-height: var(--vm-hud-dialog-line-height);
		color: inherit;
	}

	.crew-formation-scene__hotkey {
		color: var(--vm-burnt-orange);
	}
</style>
