<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';

	import CrewNavButton from '$lib/domains/crew/CrewNavButton.svelte';
	import SettingsNavButton from '$lib/domains/trainer/SettingsNavButton.svelte';
	import DialogBox from '$lib/ui/DialogBox.svelte';
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
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
	import { ensureTrainerSession } from './trainerApi';
	import TrainerPortrait from './TrainerPortrait.svelte';
	import { displayUsername } from './validateUsername';

	type ProviderVisualState = 'connected' | 'needs-config' | 'disabled';

	const DIALOG_ANCHOR = `Sweet. Connect your vibes and let's get groovin'!`;
	const HATCH_HINT_TEXT = 'Tap to hatch a new Vibemon and adopt them to your crew.';
	const VIBE_DECK_HINT_TEXT = 'Your Vibe Deck — crew index, encounter log, and field capture.';
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

	type OnboardingUiState = {
		portraitHintVisible: boolean;
		hatchHintVisible: boolean;
		settingsOpen: boolean;
	};

	const onboardingUi = getContext<OnboardingUiState | undefined>(ONBOARDING_UI_KEY);

	let providers = $state<ProviderCatalogEntry[]>([]);
	let providerStatuses = $state<Record<string, ProviderStatusEntry>>({});
	let selected = $state<string[]>([]);
	let warmed = $state<string[]>([]);
	let fetching = $state<string[]>([]);
	let hoveredKey = $state<string | null>(null);
	let configProviderId = $state<string | null>(null);
	let vibeDeckHintVisible = $state(false);
	let locationGranted = $state(false);
	let coordinates = $state<{ latitude: number; longitude: number } | null>(null);
	let catalogError = $state(false);

	let clearHoverTimer: ReturnType<typeof setTimeout> | undefined;
	let longPressTimer: ReturnType<typeof setTimeout> | undefined;
	let singleTapTimer: ReturnType<typeof setTimeout> | undefined;
	let longPressTriggered = false;

	let displayName = $derived(displayUsername(username));
	let statusById = $derived(providerStatuses);
	let activeProvider = $derived(
		configProviderId ? (providers.find((entry) => entry.id === configProviderId) ?? null) : null
	);
	let activeStatus = $derived(configProviderId ? statusById[configProviderId] : undefined);
	let activeFetching = $derived(configProviderId ? fetching.includes(configProviderId) : false);
	let hoverDescription = $derived.by(() => {
		const provider = hoveredKey ? providers.find((entry) => entry.id === hoveredKey) : undefined;
		return provider ? providerDescription(provider) : '';
	});

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
		if (!warmed.includes(providerId)) {
			warmed = [...warmed, providerId];
		}
	}

	function syncWarmedFromStatuses(statuses: ProviderStatusEntry[]) {
		const prefetchedIds = statuses
			.filter((entry) => entry.prefetched_at)
			.map((entry) => entry.id);
		if (prefetchedIds.length === 0) return;
		warmed = [...new Set([...warmed, ...prefetchedIds])];
	}

	function providerStatus(entry: ProviderCatalogEntry): ProviderStatusEntry | undefined {
		return statusById[entry.id];
	}

	function isSelected(id: string) {
		return selected.includes(id);
	}

	function isWarmed(id: string) {
		return warmed.includes(id);
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

	function providerPanelClass(entry: ProviderCatalogEntry) {
		const state = providerVisualState(entry);
		const classes = [
			'trainer-configuration__provider-panel',
			`trainer-configuration__provider-panel--${state}`
		];
		if (fetching.includes(entry.id)) {
			classes.push('trainer-configuration__provider-panel--fetching');
		}
		return classes.join(' ');
	}

	function modalBlocked() {
		return Boolean(onboardingUi?.settingsOpen || providerConfigModalStore.open);
	}

	function showProviderDescription(entry: ProviderCatalogEntry) {
		if (modalBlocked()) return;
		cancelHoverClear();
		if (onboardingUi) onboardingUi.hatchHintVisible = false;
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
		if (onboardingUi) onboardingUi.hatchHintVisible = false;
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
		if (modalBlocked()) return;
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
		if (!isSelected(providerId)) return;
		if (selected.length === 1) {
			showGameToast('Keep at least one provider enabled.', 'amber');
			return;
		}
		selected = selected.filter((value) => value !== providerId);
	}

	async function handleProviderSingleTap(entry: ProviderCatalogEntry) {
		if (!entry.implemented) {
			showProviderDescription(entry);
			return;
		}

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

	async function refreshProviderStatuses() {
		try {
			const statuses = await fetchProviderStatus(coordinates);
			providerStatuses = Object.fromEntries(statuses.map((entry) => [entry.id, entry]));
			syncWarmedFromStatuses(statuses);
		} catch {
			// Status refresh is best-effort during onboarding.
		}
	}

	async function runPrefetch(providerId: string, forceRefresh = false) {
		if (fetching.includes(providerId)) return;
		fetching = [...fetching, providerId];
		try {
			const result = await prefetchProvider(providerId, {
				latitude: coordinates?.latitude,
				longitude: coordinates?.longitude,
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
			fetching = fetching.filter((value) => value !== providerId);
		}
	}

	async function enableProvider(providerId: string) {
		const entry = providers.find((candidate) => candidate.id === providerId);
		if (!entry) return;

		if (!locationGranted && entry.requirements.some((requirement) => requirement.kind === 'geolocation')) {
			requestLocation();
			return;
		}

		if (!isProviderReady(entry, providerStatus(entry), locationGranted)) {
			await refreshProviderStatuses();
			if (!isProviderReady(entry, providerStatus(entry), locationGranted)) {
				showGameToast('Finish provider setup before enabling.', 'amber');
				return;
			}
		}

		try {
			if (!hasPrefetchedData(providerId)) {
				await runPrefetch(providerId);
			} else {
				markWarmed(providerId);
			}
			if (!selected.includes(providerId)) {
				selected = [...selected, providerId];
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
		if (!configProviderId) return;
		await runPrefetch(configProviderId, true);
	}

	function requestLocation() {
		if (!browser || !('geolocation' in navigator)) return;
		navigator.geolocation.getCurrentPosition(
			(position) => {
				locationGranted = true;
				coordinates = {
					latitude: position.coords.latitude,
					longitude: position.coords.longitude
				};
			},
			() => {
				locationGranted = false;
				coordinates = null;
			},
			{ enableHighAccuracy: true, timeout: 12_000, maximumAge: 60_000 }
		);
	}

	$effect.pre(() => {
		providerConfigModalStore.entry = activeProvider;
		providerConfigModalStore.status = activeStatus;
		providerConfigModalStore.enabled = configProviderId ? isSelected(configProviderId) : false;
		providerConfigModalStore.canDisable = configProviderId
			? isSelected(configProviderId) && selected.length > 1
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
			const sessionReady = await ensureTrainerSession(username);
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
				await refreshProviderStatuses();
			}
		})();
	});

	$effect(() => {
		if (browser && coordinates) {
			void refreshProviderStatuses();
		}
	});
</script>

{#snippet providersBody()}
	<div class="trainer-configuration" class:trainer-configuration--embedded={embedded}>
		{#if !embedded}
			<div class="trainer-configuration__portrait">
				<TrainerPortrait mirrored />
			</div>
		{/if}

		<div class="trainer-configuration__greeting">
			<GamePanel tone="status" class="trainer-configuration__greeting-panel">
				<p class="trainer-configuration__greeting-text">How are the vibes {displayName}?</p>
			</GamePanel>
		</div>

		<ul class="trainer-configuration__providers" role="list">
			{#each providers as provider (provider.id)}
				<li class="trainer-configuration__provider-item">
					<FreeFormButton
						class="trainer-configuration__provider-button"
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
					>
						<GamePanel tone="command" class={providerPanelClass(provider)}>
							<span class="trainer-configuration__provider-label">{provider.label}</span>
						</GamePanel>
					</FreeFormButton>
				</li>
			{/each}
		</ul>

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
			{#if onboardingUi}
				<div class="trainer-configuration__settings-nav">
					<SettingsNavButton bind:open={onboardingUi.settingsOpen} />
				</div>
			{/if}
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
		/* Match register: pass pointer events through to the shared portrait layer. */
		pointer-events: none;
	}

	.trainer-configuration--embedded .trainer-configuration__greeting,
	.trainer-configuration--embedded .trainer-configuration__providers,
	.trainer-configuration--embedded .trainer-configuration__hud-bar,
	.trainer-configuration--embedded .trainer-configuration__settings-nav {
		pointer-events: auto;
	}

	.trainer-configuration__portrait {
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
		font-family: var(--vm-font-ui);
		font-size: clamp(0.8125rem, 2.8vw, 1.125rem);
		line-height: 1.75;
		letter-spacing: 0.03em;
		color: inherit;
	}

	.trainer-configuration__providers {
		position: absolute;
		top: var(--vm-hud-rail-inset);
		right: var(--vm-hud-rail-inset);
		z-index: 2;
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: clamp(0.45rem, 1.4vw, 0.65rem);
		width: var(--vm-hud-provider-column-width);
	}

	.trainer-configuration__provider-item {
		width: 100%;
	}

	:global(.trainer-configuration__provider-button) {
		width: 100%;
	}

	:global(.trainer-configuration__provider-panel) {
		width: 100%;
		min-width: clamp(7.5rem, 22vw, 11rem);
	}

	:global(.trainer-configuration__provider-panel--connected) {
		--panel-command-accent: var(--vm-status-sage);
		--panel-command-clamp: var(--vm-status-sage);
		--panel-command-surface: color-mix(in srgb, var(--vm-status-sage) 20%, var(--vm-panel-command-bg));
	}

	:global(.trainer-configuration__provider-panel--disabled) {
		opacity: 0.48;
		filter: grayscale(0.45);
		--panel-command-accent: color-mix(in srgb, var(--vm-tobacco) 55%, var(--vm-brass));
		--panel-command-clamp: color-mix(in srgb, var(--vm-tobacco) 55%, var(--vm-brass));
		--panel-command-surface: color-mix(in srgb, var(--vm-tobacco) 8%, var(--vm-panel-command-bg));
	}

	:global(.trainer-configuration__provider-panel--fetching) {
		--panel-command-accent: var(--vm-status-amber);
		--panel-command-clamp: var(--vm-mustard);
		--panel-command-surface: color-mix(in srgb, var(--vm-status-amber) 16%, var(--vm-panel-command-bg));
		animation: trainer-configuration-provider-fetch 900ms steps(2, end) infinite;
	}

	:global(.trainer-configuration__provider-panel--fetching.trainer-configuration__provider-panel--connected) {
		--panel-command-accent: var(--vm-status-amber);
		--panel-command-clamp: var(--vm-mustard);
		--panel-command-surface: color-mix(in srgb, var(--vm-status-amber) 16%, var(--vm-panel-command-bg));
	}

	@keyframes trainer-configuration-provider-fetch {
		0%,
		49% {
			opacity: 1;
		}
		50%,
		100% {
			opacity: 0.68;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		:global(.trainer-configuration__provider-panel--fetching) {
			animation: none;
		}
	}

	.trainer-configuration__provider-label {
		display: block;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.6875rem, 2.2vw, 0.9375rem);
		line-height: 1.5;
		letter-spacing: 0.06em;
		text-align: center;
		color: inherit;
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

	.trainer-configuration__settings-nav {
		position: absolute;
		right: var(--vm-hud-rail-inset);
		bottom: calc(
			var(--vm-hud-bottom-inset) + (var(--vm-hud-dialog-slot-height) - var(--vm-hud-icon-slot-height)) / 2
		);
		z-index: 2;
		width: var(--vm-hud-provider-column-width);
		height: var(--vm-hud-icon-slot-height);
		display: flex;
		justify-content: center;
		align-items: center;
	}

	.trainer-configuration__provider-hint-text {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: var(--vm-hud-font-dialog);
		line-height: var(--vm-hud-dialog-line-height);
		color: inherit;
	}

	@media (max-width: 480px) {
		.trainer-configuration__portrait {
			left: 28%;
			bottom: clamp(10rem, 20vh, 12rem);
		}

		.trainer-configuration__providers,
		.trainer-configuration__settings-nav {
			--vm-hud-provider-column-width: min(46vw, 10.5rem);
		}
	}
</style>
