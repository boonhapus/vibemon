<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';

	import { bootstrapHatchSceneOnce } from './hatchSceneStore';
	import { createHatchFlowState, HATCH_FLOW_KEY, type HatchFlowState } from './hatchFlow';
	import {
		addSelectedProvider,
		applyCandidateProviderIds,
		createProviderSelectionState,
		isProviderSelected,
		markProviderWarmed,
		PROVIDER_SELECTION_KEY,
		removeSelectedProvider,
		setProviderCoordinates,
		setProviderFetching,
		type ProviderSelectionState
	} from './providerSelection';

	import CrewNavButton from '$lib/domains/crew/CrewNavButton.svelte';
	import type { TrainerOnboardingUi } from '$lib/domains/trainer/trainerOnboardingUi';
	import DialogBox from '$lib/ui/DialogBox.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import type { PixelIconName } from '$lib/ui/PixelIcon.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';

	import { providerConfigModalStore } from './providerConfigModalStore.svelte';
	import {
		fetchProviderCatalog,
		fetchProviderStatus,
		isProviderReady,
		prefetchProvider,
		type ProviderCatalogEntry,
		type ProviderStatusEntry
	} from './providerApi';
	import { resolveTrainerSession } from './trainerApi';
	import {
		clearStoredTrainerCoordinates,
		readCurrentPosition,
		readStoredTrainerCoordinates,
		restoreTrainerCoordinates,
		storeTrainerCoordinates
	} from './trainerGeolocation';
	import ProviderPatchPanel from './ProviderPatchPanel.svelte';
	import ProviderPatchRow from './ProviderPatchRow.svelte';
	import TrainerReference from './TrainerReference.svelte';
	import { PROVIDER_ICONS } from './providerLabels';
	import { displayUsername } from './validateUsername';

	type ProviderVisualState = 'connected' | 'needs-config' | 'disabled';

	const DIALOG_ANCHOR = `Sweet. Connect your vibes and let's get groovin'!`;
	const HATCH_HINT_TEXT = `When you're ready, double-tap to hatch from your vibes.`;
	const HATCH_ACTION_HINTS = {
		refresh: 'Redraw their look from your connected vibes.',
		adopt: 'Welcome them to your crew — add a nickname if you like.',
		release: 'Release them to the Wild and try another hatch.'
	} as const;
	const HATCH_TYPEWRITER_CHAR_DELAY = 38;
	const VIBE_DECK_HINT_TEXT = 'Your Vibe Deck — crew roster, encounter log, and field gear.';
	const CANDIDATE_PROVIDER_GUARD_TEXT =
		'Adopt or Release your current Vibemon before changing the vibes.';
	const HOVER_CLEAR_MS = 250;
	const LONG_PRESS_MS = 500;
	const DOUBLE_TAP_MS = 300;
	const ONBOARDING_UI_KEY = 'trainer-onboarding-ui';

	let {
		username,
		dialogText = DIALOG_ANCHOR,
		showDialogCursor = true,
		typeDialogOnLoad = true,
		embedded = false
	}: {
		username: string;
		dialogText?: string;
		showDialogCursor?: boolean;
		typeDialogOnLoad?: boolean;
		embedded?: boolean;
	} = $props();

	const onboardingUi = getContext<TrainerOnboardingUi | undefined>(ONBOARDING_UI_KEY);
	const hatchFlow = getContext<HatchFlowState | undefined>(HATCH_FLOW_KEY) ?? createHatchFlowState();
	const providerSelection =
		getContext<ProviderSelectionState | undefined>(PROVIDER_SELECTION_KEY) ??
		createProviderSelectionState();

	let providers = $state<ProviderCatalogEntry[]>([]);
	let providerStatuses = $state<Record<string, ProviderStatusEntry>>({});
	let hoveredKey = $state<string | null>(null);
	let configProviderId = $state<string | null>(null);
	let vibeDeckHintVisible = $state(false);
	let locationGranted = $state(false);
	let catalogError = $state(false);
	let locationBootstrapped = $state(false);

	let clearHoverTimer: ReturnType<typeof setTimeout> | undefined;
	let longPressTimer: ReturnType<typeof setTimeout> | undefined;
	let singleTapTimer: ReturnType<typeof setTimeout> | undefined;
	let longPressTriggered = false;
	let providerStatusFetchKey: string | null = null;
	let providerStatusFetchPromise: Promise<void> | null = null;

	let displayName = $derived(displayUsername(username));
	let statusById = $derived(providerStatuses);
	let activeProvider = $derived(
		configProviderId ? (providers.find((entry) => entry.id === configProviderId) ?? null) : null
	);
	let activeStatus = $derived(configProviderId ? statusById[configProviderId] : undefined);
	let activeFetching = $derived(
		configProviderId ? providerSelection.fetchingIds.includes(configProviderId) : false
	);
	let hoverDescription = $derived.by(() => {
		const provider = hoveredKey ? providers.find((entry) => entry.id === hoveredKey) : undefined;
		return provider ? providerDescription(provider) : '';
	});
	let candidateAppearedDialog = $derived(
		hatchFlow.candidate ? `The vibes settle... meet ${hatchFlow.candidate.name}!` : ''
	);
	let hatchActionHintText = $derived(
		hatchFlow.actionHint ? HATCH_ACTION_HINTS[hatchFlow.actionHint] : ''
	);
	let hatchCandidateHintText = $derived(hatchFlow.candidateHint ?? '');

	function providerDescription(provider: ProviderCatalogEntry) {
		if (!provider.implemented) {
			return `Coming soon -- ${provider.tagline}`;
		}
		return provider.tagline;
	}

	function cancelHoverClear() {
		if (clearHoverTimer) {
			clearTimeout(clearHoverTimer);
			clearHoverTimer = undefined;
		}
	}

	function cancelLongPress() {
		if (longPressTimer) {
			clearTimeout(longPressTimer);
			longPressTimer = undefined;
		}
	}

	function cancelSingleTap() {
		if (singleTapTimer) {
			clearTimeout(singleTapTimer);
			singleTapTimer = undefined;
		}
	}

	function markWarmed(providerId: string) {
		markProviderWarmed(providerSelection, providerId);
	}

	function syncWarmedFromStatuses(statuses: ProviderStatusEntry[]) {
		const prefetchedIds = statuses
			.filter((entry) => entry.prefetched_at)
			.map((entry) => entry.id);
		if (prefetchedIds.length === 0) return;
		for (const providerId of prefetchedIds) {
			markProviderWarmed(providerSelection, providerId);
		}
	}

	function providerStatus(entry: ProviderCatalogEntry): ProviderStatusEntry | undefined {
		return statusById[entry.id];
	}

	function isSelected(id: string) {
		return isProviderSelected(providerSelection, id);
	}

	function isWarmed(id: string) {
		return providerSelection.warmedIds.includes(id);
	}

	function hasPrefetchedData(id: string) {
		return isWarmed(id) || Boolean(providerStatuses[id]?.prefetched_at);
	}

	function providerNeedsConfiguration(entry: ProviderCatalogEntry) {
		return !isProviderReady(entry, providerStatus(entry), locationGranted);
	}

	function isProviderConnected(entry: ProviderCatalogEntry) {
		return (
			isSelected(entry.id) &&
			isProviderReady(entry, providerStatus(entry), locationGranted) &&
			isWarmed(entry.id)
		);
	}

	function providerVisualState(entry: ProviderCatalogEntry): ProviderVisualState {
		if (!entry.implemented) return 'disabled';
		if (isProviderConnected(entry)) return 'connected';
		return 'needs-config';
	}

	function providerIcon(entry: ProviderCatalogEntry): PixelIconName {
		return PROVIDER_ICONS[entry.id] ?? 'gear';
	}

	function modalBlocked() {
		return Boolean(onboardingUi?.settingsOpen || providerConfigModalStore.open);
	}

	function candidateReviewActive() {
		return Boolean(hatchFlow.candidate);
	}

	function blockProviderChangeForCandidateReview(): boolean {
		if (!candidateReviewActive()) return false;
		showGameToast(CANDIDATE_PROVIDER_GUARD_TEXT, 'amber');
		return true;
	}

	function showProviderDescription(entry: ProviderCatalogEntry) {
		if (modalBlocked()) return;
		cancelHoverClear();
		if (onboardingUi) {
			onboardingUi.hatchHintVisible = false;
		}
		hatchFlow.actionHint = null;
		hatchFlow.candidateHint = null;
		vibeDeckHintVisible = false;
		hoveredKey = entry.id;
	}

	function clearProviderDescription(entry: ProviderCatalogEntry) {
		cancelHoverClear();
		clearHoverTimer = setTimeout(() => {
			if (hoveredKey === entry.id) {
				hoveredKey = null;
			}
			clearHoverTimer = undefined;
		}, HOVER_CLEAR_MS);
	}

	function showVibeDeckHint() {
		if (modalBlocked()) return;
		cancelHoverClear();
		if (onboardingUi) {
			onboardingUi.hatchHintVisible = false;
		}
		hatchFlow.candidateHint = null;
		hoveredKey = null;
		vibeDeckHintVisible = true;
	}

	function clearVibeDeckHint() {
		cancelHoverClear();
		clearHoverTimer = setTimeout(() => {
			vibeDeckHintVisible = false;
			clearHoverTimer = undefined;
		}, HOVER_CLEAR_MS);
	}

	function openProviderModal(id: string) {
		if (modalBlocked() || blockProviderChangeForCandidateReview()) return;
		configProviderId = id;
		providerConfigModalStore.open = true;
		cancelHoverClear();
		hoveredKey = null;
	}

	function handleProviderPointerDown(entry: ProviderCatalogEntry) {
		if (modalBlocked() || !entry.implemented) return;
		cancelSingleTap();
		longPressTriggered = false;
		cancelLongPress();
		longPressTimer = setTimeout(() => {
			longPressTriggered = true;
			cancelSingleTap();
			openProviderModal(entry.id);
			longPressTimer = undefined;
		}, LONG_PRESS_MS);
	}

	function handleProviderPointerUp(entry: ProviderCatalogEntry) {
		cancelLongPress();
	}

	function disableProvider(providerId: string) {
		if (blockProviderChangeForCandidateReview()) return;
		if (!isSelected(providerId)) return;
		if (providerSelection.selectedIds.length === 1) {
			showGameToast('Keep at least one vibe source connected.', 'amber');
			return;
		}
		removeSelectedProvider(providerSelection, providerId);
	}

	async function handleProviderSingleTap(entry: ProviderCatalogEntry) {
		if (!entry.implemented) {
			showProviderDescription(entry);
			return;
		}
		if (blockProviderChangeForCandidateReview()) return;

		if (providerNeedsConfiguration(entry)) {
			openProviderModal(entry.id);
			return;
		}

		if (isSelected(entry.id)) {
			disableProvider(entry.id);
			return;
		}

		await enableProvider(entry.id);
	}

	function handleProviderClick(entry: ProviderCatalogEntry) {
		if (modalBlocked()) return;
		if (longPressTriggered) {
			longPressTriggered = false;
			return;
		}

		if (singleTapTimer) {
			cancelSingleTap();
			openProviderModal(entry.id);
			return;
		}

		singleTapTimer = setTimeout(() => {
			singleTapTimer = undefined;
			void handleProviderSingleTap(entry);
		}, DOUBLE_TAP_MS);
	}

	function handleProviderContextMenu(entry: ProviderCatalogEntry, event: MouseEvent) {
		event.preventDefault();
		if (modalBlocked()) return;
		cancelSingleTap();
		cancelLongPress();
		longPressTriggered = false;
		openProviderModal(entry.id);
	}

	function providerStatusFetchKeyFor(
		coords: ProviderSelectionState['coordinates']
	): string {
		return coords ? `${coords.latitude},${coords.longitude}` : 'none';
	}

	async function refreshProviderStatuses() {
		const key = providerStatusFetchKeyFor(providerSelection.coordinates);
		if (providerStatusFetchKey === key && providerStatusFetchPromise) {
			return providerStatusFetchPromise;
		}
		providerStatusFetchKey = key;
		providerStatusFetchPromise = (async () => {
			try {
				const statuses = await fetchProviderStatus(providerSelection.coordinates);
				providerStatuses = Object.fromEntries(statuses.map((entry) => [entry.id, entry]));
				syncWarmedFromStatuses(statuses);
			} catch {
				// Status refresh is best-effort during onboarding.
			}
		})();
		return providerStatusFetchPromise;
	}

	async function runPrefetch(providerId: string, forceRefresh = false) {
		if (providerSelection.fetchingIds.includes(providerId)) return;
		setProviderFetching(providerSelection, providerId, true);
		try {
			const result = await prefetchProvider(providerId, {
				latitude: providerSelection.coordinates?.latitude,
				longitude: providerSelection.coordinates?.longitude,
				forceRefresh
			});
			const existing = providerStatuses[providerId];
			providerStatuses = {
				...providerStatuses,
				[providerId]: {
					id: providerId,
					ready: existing?.ready ?? true,
					requirements: existing?.requirements ?? {},
					prefetched_at: result.prefetched_at
				}
			};
			markWarmed(providerId);
		} catch (error) {
			const message = error instanceof Error ? error.message : 'Could not fetch provider data.';
			showGameToast(message, 'brick');
			throw error;
		} finally {
			setProviderFetching(providerSelection, providerId, false);
		}
	}

	async function enableProvider(providerId: string) {
		if (blockProviderChangeForCandidateReview()) return;
		const entry = providers.find((candidate) => candidate.id === providerId);
		if (!entry) return;

		if (!locationGranted && entry.requirements.some((requirement) => requirement.kind === 'geolocation')) {
			requestLocation();
			return;
		}

		if (!isProviderReady(entry, providerStatus(entry), locationGranted)) {
			await refreshProviderStatuses();
			if (!isProviderReady(entry, providerStatus(entry), locationGranted)) {
				showGameToast('Finish vibe source setup before you connect it.', 'amber');
				return;
			}
		}

		try {
			if (!hasPrefetchedData(providerId)) {
				await runPrefetch(providerId);
			} else {
				markWarmed(providerId);
			}
			if (!isProviderSelected(providerSelection, providerId)) {
				addSelectedProvider(providerSelection, providerId);
			}
		} catch {
			return;
		}
	}

	async function handleModalEnable() {
		if (!configProviderId) return;
		await enableProvider(configProviderId);
	}

	function handleModalDisable() {
		if (!configProviderId) return;
		disableProvider(configProviderId);
	}

	async function handleModalRefresh() {
		if (!configProviderId || blockProviderChangeForCandidateReview()) return;
		await runPrefetch(configProviderId, true);
	}

	function applyCoordinates(coords: { latitude: number; longitude: number }) {
		locationGranted = true;
		if (
			providerSelection.coordinates?.latitude === coords.latitude &&
			providerSelection.coordinates?.longitude === coords.longitude
		) {
			return;
		}
		setProviderCoordinates(providerSelection, coords);
		storeTrainerCoordinates(coords);
	}

	function clearCoordinates() {
		locationGranted = false;
		setProviderCoordinates(providerSelection, null);
		clearStoredTrainerCoordinates();
	}

	function requestLocation() {
		if (!browser || !('geolocation' in navigator)) return;
		void readCurrentPosition()
			.then(applyCoordinates)
			.catch(clearCoordinates);
	}

	async function bootstrapLocation() {
		const stored = readStoredTrainerCoordinates();
		if (stored) {
			applyCoordinates(stored);
		}

		const restored = await restoreTrainerCoordinates();
		if (restored) {
			applyCoordinates(restored);
		}
	}

	$effect(() => {
		const providerIds = hatchFlow.candidate?.providers;
		if (!providerIds?.length) return;
		applyCandidateProviderIds(providerSelection, providerIds);
	});

	$effect.pre(() => {
		providerConfigModalStore.entry = activeProvider;
		providerConfigModalStore.status = activeStatus;
		providerConfigModalStore.enabled = configProviderId ? isSelected(configProviderId) : false;
		providerConfigModalStore.canDisable = configProviderId
			? isSelected(configProviderId) && providerSelection.selectedIds.length > 1
			: false;
		providerConfigModalStore.locationGranted = locationGranted;
		providerConfigModalStore.fetching = activeFetching;
	});

	onMount(() => {
		providerConfigModalStore.handlers = {
			onEnable: handleModalEnable,
			onDisable: handleModalDisable,
			onRefresh: handleModalRefresh
		};

		if (!browser) return;

		void (async () => {
			const sessionReady =
				embedded && onboardingUi
					? await bootstrapHatchSceneOnce(onboardingUi, hatchFlow, providerSelection, username)
					: Boolean(await resolveTrainerSession(username));
			if (!sessionReady) {
				catalogError = true;
				showGameToast('Could not start your trainer session.', 'brick');
			}

			try {
				providers = await fetchProviderCatalog();
			} catch {
				catalogError = true;
				showGameToast('Could not load providers.', 'brick');
				return;
			}

			if (sessionReady) {
				await bootstrapLocation();
			}
			locationBootstrapped = true;
		})();
	});

	$effect(() => {
		if (!browser || !locationBootstrapped) return;
		void refreshProviderStatuses();
	});
</script>

{#snippet providersBody()}
	<div class="trainer-configuration" class:trainer-configuration--embedded={embedded}>
		{#if !embedded}
			<div class="trainer-configuration__reference">
				<TrainerReference mirrored />
			</div>
		{/if}

		{#if !embedded}
			<div class="trainer-configuration__greeting">
				<GamePanel tone="status" class="trainer-configuration__greeting-panel">
					<p class="trainer-configuration__greeting-text">How are the vibes {displayName}?</p>
				</GamePanel>
			</div>
		{/if}

		{#if !(embedded && hatchFlow.candidate)}
			<div class="trainer-configuration__providers">
				<ProviderPatchPanel>
					{#each providers as provider (provider.id)}
						<ProviderPatchRow
							label={provider.label}
							icon={providerIcon(provider)}
							state={providerVisualState(provider)}
							fetching={providerSelection.fetchingIds.includes(provider.id)}
							blocked={candidateReviewActive()}
							ariaLabel="{provider.label}: {providerDescription(provider)}"
							onclick={() => handleProviderClick(provider)}
							onpointerdown={() => handleProviderPointerDown(provider)}
							onpointerup={() => handleProviderPointerUp(provider)}
							onpointerleave={() => handleProviderPointerUp(provider)}
							onpointercancel={() => handleProviderPointerUp(provider)}
							onmouseenter={() => showProviderDescription(provider)}
							onmouseleave={() => clearProviderDescription(provider)}
							onfocus={() => showProviderDescription(provider)}
							onblur={() => clearProviderDescription(provider)}
							oncontextmenu={(event) => handleProviderContextMenu(provider, event)}
						/>
					{/each}
				</ProviderPatchPanel>
			</div>
		{/if}

		{#snippet dialogSlot()}
			<div class="trainer-configuration__dialog">
				{#if providerConfigModalStore.open && activeProvider}
					<GamePanel tone="status" class="hud-dialog-slot trainer-configuration__provider-hint">
						<p class="trainer-configuration__provider-hint-text">{providerDescription(activeProvider)}</p>
					</GamePanel>
				{:else if embedded && onboardingUi?.hatchHintVisible}
					<GamePanel tone="status" class="hud-dialog-slot trainer-configuration__hatch-hint">
						<p class="trainer-configuration__provider-hint-text">{HATCH_HINT_TEXT}</p>
					</GamePanel>
				{:else if embedded && (hatchFlow.generating || hatchFlow.busy) && hatchFlow.generatingLine}
					{#key hatchFlow.generatingLine}
						<DialogBox
							text={hatchFlow.generatingLine}
							typewriter={true}
							showCursor={false}
							charDelay={HATCH_TYPEWRITER_CHAR_DELAY}
							class="hud-dialog-slot"
						/>
					{/key}
				{:else if embedded && hatchFlow.actionHint}
					<GamePanel tone="status" class="hud-dialog-slot trainer-configuration__provider-hint">
						<p class="trainer-configuration__provider-hint-text">{hatchActionHintText}</p>
					</GamePanel>
				{:else if embedded && hatchFlow.candidateHint}
					<GamePanel tone="status" class="hud-dialog-slot trainer-configuration__provider-hint">
						<p class="trainer-configuration__provider-hint-text">{hatchCandidateHintText}</p>
					</GamePanel>
				{:else if embedded && hatchFlow.candidate && !hatchFlow.generating && !hatchFlow.busy}
					<DialogBox
						text={candidateAppearedDialog}
						showCursor={showDialogCursor}
						typewriter={false}
						class="hud-dialog-slot"
					/>
				{:else if catalogError}
					<GamePanel tone="status" class="hud-dialog-slot trainer-configuration__provider-hint">
						<p class="trainer-configuration__provider-hint-text">Provider catalog unavailable. Try again soon.</p>
					</GamePanel>
				{:else if hoveredKey}
					<GamePanel tone="status" class="hud-dialog-slot trainer-configuration__provider-hint">
						<p class="trainer-configuration__provider-hint-text">{hoverDescription}</p>
					</GamePanel>
				{:else if vibeDeckHintVisible}
					<GamePanel tone="status" class="hud-dialog-slot trainer-configuration__vibe-deck-hint">
						<p class="trainer-configuration__provider-hint-text">{VIBE_DECK_HINT_TEXT}</p>
					</GamePanel>
				{:else}
					<DialogBox text={dialogText || DIALOG_ANCHOR} showCursor={showDialogCursor} typewriter={typeDialogOnLoad} />
				{/if}
			</div>
		{/snippet}

		{#if embedded}
			<div class="trainer-configuration__hud-bar">
				<div class="trainer-configuration__crew-nav">
					<CrewNavButton
						disabled={modalBlocked()}
						onmouseenter={showVibeDeckHint}
						onmouseleave={clearVibeDeckHint}
						onfocus={showVibeDeckHint}
						onblur={clearVibeDeckHint}
					/>
				</div>
				{@render dialogSlot()}
				<div class="trainer-configuration__hud-bar-spacer" aria-hidden="true"></div>
			</div>
		{:else}
			{@render dialogSlot()}
		{/if}
	</div>
{/snippet}

{#if embedded}
	{@render providersBody()}
{:else}
	<SceneFrame>
		{@render providersBody()}
	</SceneFrame>
{/if}

<style>
	.trainer-configuration {
		position: relative;
		min-height: 100dvh;
	}

	.trainer-configuration--embedded {
		min-height: 100dvh;
		/* Match register: pass pointer events through to the shared reference layer. */
		pointer-events: none;
		--vm-hud-icon-slot-height: calc(var(--vm-hud-dialog-slot-height) * 0.76);
	}

	.trainer-configuration--embedded .trainer-configuration__providers,
	.trainer-configuration--embedded .trainer-configuration__hud-bar {
		pointer-events: auto;
	}

	.trainer-configuration__reference {
		position: absolute;
		left: 30%;
		bottom: clamp(12rem, 23vh, 14.5rem);
		transform: translateX(-50%);
		z-index: 1;
	}

	.trainer-configuration__greeting {
		position: absolute;
		top: clamp(1.25rem, 5vh, 2.5rem);
		left: clamp(1.25rem, 4vw, 2.5rem);
		z-index: 2;
		max-width: calc(100% - 2.5rem);
	}

	:global(.trainer-configuration__greeting-panel) {
		width: var(--vm-hud-name-width);
	}

	.trainer-configuration__greeting-text {
		margin: 0;
		font-size: clamp(0.8125rem, 2.6vw, 1.125rem);
		line-height: 1.6;
		letter-spacing: 0.03em;
		color: inherit;
	}

	.trainer-configuration__providers {
		position: absolute;
		top: var(--vm-bezel-w);
		right: var(--vm-bezel-w);
		z-index: 2;
		width: var(--vm-hud-rail-width);
		max-width: calc(100% - 2 * var(--vm-bezel-w));
		min-width: 0;
	}

	.trainer-configuration__hud-bar {
		position: absolute;
		left: 50%;
		bottom: var(--vm-hud-bottom-inset);
		transform: translateX(-50%);
		z-index: 2;
		width: 100%;
		display: grid;
		grid-template-columns: 1fr var(--vm-hud-dialog-width) 1fr;
		align-items: center;
	}

	.trainer-configuration__dialog {
		justify-self: center;
		width: var(--vm-hud-dialog-width);
		display: flex;
		justify-content: center;
	}

	.trainer-configuration:not(:has(.trainer-configuration__hud-bar)) .trainer-configuration__dialog {
		position: absolute;
		left: 50%;
		bottom: var(--vm-hud-bottom-inset);
		transform: translateX(-50%);
		z-index: 2;
	}

	.trainer-configuration__crew-nav {
		justify-self: center;
		height: var(--vm-hud-icon-slot-height);
		display: flex;
		align-items: center;
	}

	.trainer-configuration__hud-bar-spacer {
		justify-self: center;
		height: var(--vm-hud-icon-slot-height);
		width: var(--vm-hud-icon-slot-height);
	}
</style>
