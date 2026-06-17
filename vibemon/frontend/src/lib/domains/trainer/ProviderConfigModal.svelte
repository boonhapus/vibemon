<script lang="ts">
	import ElementBadge from '$lib/ui/ElementBadge.svelte';
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';
	import GameButton from '$lib/ui/GameButton.svelte';
	import GameModal from '$lib/ui/GameModal.svelte';

	import { providerConfigModalStore } from './providerConfigModalStore.svelte';
	import type { ProviderRequirement, RequirementStatusEntry } from './providerApi';

	let entry = $derived(providerConfigModalStore.entry);
	let status = $derived(providerConfigModalStore.status);
	let enabled = $derived(providerConfigModalStore.enabled);
	let canDisable = $derived(providerConfigModalStore.canDisable);
	let locationGranted = $derived(providerConfigModalStore.locationGranted);
	let fetching = $derived(providerConfigModalStore.fetching);

	let ariaLabel = $derived(entry ? `${entry.label} provider configuration` : 'Provider configuration');

	function requirementStatus(requirement: ProviderRequirement): RequirementStatusEntry | undefined {
		if (requirement.kind === 'geolocation') {
			return {
				status: locationGranted ? 'satisfied' : 'missing'
			};
		}
		return status?.requirements[requirement.id];
	}

	function requirementReady(requirement: ProviderRequirement): boolean {
		return requirementStatus(requirement)?.status === 'satisfied';
	}

	function requirementDisplayStatus(
		requirement: ProviderRequirement
	): RequirementStatusEntry['status'] {
		return requirementStatus(requirement)?.status ?? 'missing';
	}

	let pendingRequirement = $derived.by(() => {
		if (!entry) return null;
		for (const requirement of entry.requirements) {
			if (requirementDisplayStatus(requirement) === 'missing') {
				return requirement;
			}
		}
		return null;
	});

	let ready = $derived.by(() => {
		if (!entry?.implemented) return false;
		return entry.requirements.every((requirement) => requirementReady(requirement));
	});

	let lastFetchedLabel = $derived(formatLastFetched(status?.prefetched_at));

	let showDataPanel = $derived(Boolean(entry && (ready || fetching) && !pendingRequirement));

	function formatLastFetched(iso: string | null | undefined): string | null {
		if (!iso) return null;
		const parsed = new Date(iso);
		if (Number.isNaN(parsed.getTime())) return null;
		const month = parsed.toLocaleString('en-US', { month: 'short' });
		const day = String(parsed.getDate()).padStart(2, '0');
		const time = parsed.toLocaleString(undefined, {
			hour: 'numeric',
			minute: '2-digit'
		});
		return `${month} ${day} ${time}`;
	}

	function requirementStatusLabel(displayStatus: RequirementStatusEntry['status']): string {
		if (displayStatus === 'satisfied') return 'Ready';
		if (displayStatus === 'unavailable') return 'Coming soon';
		return 'Setup';
	}

	let canEnable = $derived(Boolean(entry?.implemented && ready && !enabled && !fetching));
	let canRefresh = $derived(Boolean(entry?.implemented && ready && !fetching));

	function openAuthorize(url: string) {
		window.open(url, '_blank', 'noopener,noreferrer');
	}

	function handleRequirementAction(requirement: ProviderRequirement) {
		if (requirement.kind === 'geolocation' && !locationGranted) {
			providerConfigModalStore.handlers.onEnable?.();
			return;
		}
		if (requirement.kind === 'oauth2_link') {
			const authorizeUrl = status?.requirements[requirement.id]?.authorize_url;
			if (authorizeUrl) openAuthorize(authorizeUrl);
			return;
		}
		if (requirement.kind === 'secret_group') {
			const groupStatus = status?.requirements[requirement.id];
			if (groupStatus?.authorize_url) {
				openAuthorize(groupStatus.authorize_url);
			}
		}
	}

	function handlePrimaryAction() {
		if (enabled) {
			providerConfigModalStore.handlers.onDisable?.();
			return;
		}
		providerConfigModalStore.handlers.onEnable?.();
	}
</script>

{#if entry}
	<GameModal
		bind:open={providerConfigModalStore.open}
		ariaLabel={ariaLabel}
		placement="center"
		panelClass="provider-config-modal__panel"
		width="min(calc(100vw - 2rem), max(35vw, 18rem))"
		maxHeight="calc(100dvh - 2rem)"
	>
		<div class="provider-config-modal">
			<div class="provider-config-modal__header">
				<h2 class="provider-config-modal__title">{entry.label}</h2>
				{#if entry.lore.length > 0}
					<hr class="provider-config-modal__divider" />
				{/if}
			</div>

			<div class="provider-config-modal__learn">
				{#each entry.lore as paragraph, index (index)}
					<p class="provider-config-modal__lore">{paragraph}</p>
				{/each}

				{#if entry.elements.length > 0}
					<div class="provider-config-modal__learn-block">
						<h3 class="provider-config-modal__section-title">Contributes</h3>
						<div class="provider-config-modal__types" role="list">
							{#each entry.elements as element (element.type)}
								<ElementBadge type={element.type} />
							{/each}
						</div>
					</div>
				{/if}
			</div>

			{#if entry.implemented}
				<div class="provider-config-modal__controls">
					<ul class="provider-config-modal__cards" role="list">
							{#each entry.requirements as requirement (requirement.id)}
							{@const displayStatus = requirementDisplayStatus(requirement)}
							{#if displayStatus === 'missing'}
								<li class="provider-config-modal__card-item" role="none">
									<FreeFormButton
										class="provider-config-modal__card provider-config-modal__card--pending provider-config-modal__card--action"
										ariaLabel="Configure {requirement.label}"
										testId={requirement.kind === 'geolocation' ? 'provider-config-location' : undefined}
										onclick={() => handleRequirementAction(requirement)}
									>
										<div class="provider-config-modal__card-main">
											<span class="provider-config-modal__card-label">{requirement.label}</span>
											<span class="provider-config-modal__card-description"
												>{requirement.description}</span
											>
										</div>
										<div class="provider-config-modal__card-aside">
											<span
												class="provider-config-modal__status-chip provider-config-modal__status-chip--pending"
											>
												{requirementStatusLabel(displayStatus)}
											</span>
										</div>
									</FreeFormButton>
								</li>
							{:else}
								<li
									class="provider-config-modal__card"
									class:provider-config-modal__card--ready={displayStatus === 'satisfied'}
								>
									<div class="provider-config-modal__card-main">
										<span class="provider-config-modal__card-label">{requirement.label}</span>
										<span class="provider-config-modal__card-description"
											>{requirement.description}</span
										>
									</div>
									<div class="provider-config-modal__card-aside">
										<span
											class="provider-config-modal__status-chip"
											class:provider-config-modal__status-chip--ready={displayStatus ===
												'satisfied'}
											class:provider-config-modal__status-chip--unavailable={displayStatus ===
												'unavailable'}
										>
											{requirementStatusLabel(displayStatus)}
										</span>
									</div>
								</li>
							{/if}
						{/each}

						{#if showDataPanel}
							<li
								class="provider-config-modal__card provider-config-modal__card--data"
								aria-live={fetching ? 'polite' : undefined}
							>
								<div class="provider-config-modal__card-main provider-config-modal__card-main--hatch-data">
									<span class="provider-config-modal__card-label">Hatch data</span>
									<span class="provider-config-modal__card-description">
										{#if !fetching && lastFetchedLabel}
											Last fetched {lastFetchedLabel}
										{/if}
									</span>
								</div>
								<div class="provider-config-modal__card-aside">
									<span
										class="provider-config-modal__status-chip"
										class:provider-config-modal__status-chip--fetching={fetching}
										class:provider-config-modal__status-chip--ready={!fetching}
									>
										{fetching ? 'Fetching' : 'Ready'}
									</span>
								</div>
							</li>
						{/if}
					</ul>

					<div class="provider-config-modal__actions">
						<div class="provider-config-modal__action-row">
							<GameButton
								variant={enabled ? 'secondary' : 'primary'}
								class="provider-config-modal__action-button provider-config-modal__action-button--primary"
								ariaLabel={enabled ? 'Disable provider' : 'Enable provider'}
								testId="provider-config-enable"
								disabled={enabled ? !canDisable || fetching : !canEnable}
								onclick={handlePrimaryAction}
							>
								{enabled ? 'Disable' : 'Enable'}
							</GameButton>
							<GameButton
								variant="secondary"
								class="provider-config-modal__action-button"
								ariaLabel="Force refresh provider data"
								disabled={!canRefresh}
								onclick={() => providerConfigModalStore.handlers.onRefresh?.()}
							>
								Refresh
							</GameButton>
						</div>
					</div>
				</div>
			{:else}
				<p class="provider-config-modal__coming-soon">This provider is coming soon.</p>
			{/if}
		</div>
	</GameModal>
{/if}

<style>
	:global(.provider-config-modal__panel .game-modal__panel) {
		display: flex;
		flex-direction: column;
		max-height: var(--game-modal-max-height, calc(100dvh - 2rem));
	}

	:global(.provider-config-modal__panel .game-modal__body) {
		display: flex;
		flex-direction: column;
		flex: 1 1 auto;
		min-height: 0;
		overflow: hidden;
		max-height: none;
		padding: clamp(0.7rem, 2vw, 0.95rem);
	}

	.provider-config-modal {
		display: flex;
		flex-direction: column;
		min-height: 0;
		flex: 1 1 auto;
	}

	.provider-config-modal__header {
		flex-shrink: 0;
	}

	.provider-config-modal__title {
		margin: 0;
		font-family: var(--vm-font-title);
		font-size: clamp(1.125rem, 3.6vw, 1.5rem);
		font-weight: 700;
		line-height: 1.2;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		text-align: left;
		color: inherit;
		opacity: 1;
	}

	.provider-config-modal__learn {
		flex: 1 1 auto;
		min-height: 0;
		overflow: auto;
		padding-bottom: clamp(0.4rem, 1vh, 0.6rem);
	}

	.provider-config-modal__learn-block {
		margin-top: var(--vm-space-md);
	}

	.provider-config-modal__section-title {
		margin: 0 0 0.5rem;
		padding-bottom: 0.35rem;
		border-bottom: 2px solid color-mix(in srgb, var(--vm-plum) 28%, transparent);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1.4;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: inherit;
		opacity: 0.9;
	}

	.provider-config-modal__lore {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1.65;
		color: color-mix(in srgb, currentColor 65%, transparent);
	}

	.provider-config-modal__lore:first-child {
		margin-top: var(--vm-space-md);
		color: var(--vm-plum);
	}

	.provider-config-modal__divider {
		margin: var(--vm-space-xs) 0 0;
		border: 0;
		border-top: 2px solid color-mix(in srgb, var(--vm-tobacco) 32%, transparent);
	}

	.provider-config-modal__lore + .provider-config-modal__lore {
		margin-top: var(--vm-space-sm);
	}

	.provider-config-modal__types {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}

	.provider-config-modal__controls {
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		gap: clamp(0.45rem, 1.1vh, 0.6rem);
		padding-top: clamp(0.45rem, 1.1vh, 0.6rem);
	}

	.provider-config-modal__cards {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.provider-config-modal__card-item {
		width: 100%;
		list-style: none;
	}

	.provider-config-modal__card {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 0.65rem 1rem;
		align-items: stretch;
		width: 100%;
		box-sizing: border-box;
		padding: clamp(0.6rem, 1.4vh, 0.75rem) clamp(0.65rem, 1.6vw, 0.85rem);
		border: 2px solid color-mix(in srgb, var(--vm-tobacco) 22%, transparent);
		background: var(--vm-parchment);
		text-align: left;
		box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.45);
	}

	:global(button.free-form-button.provider-config-modal__card--action) {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 0.65rem 1rem;
		align-items: stretch;
		justify-content: stretch;
		width: 100%;
		box-sizing: border-box;
		margin: 0;
		padding: clamp(0.6rem, 1.4vh, 0.75rem) clamp(0.65rem, 1.6vw, 0.85rem);
		border: 2px solid color-mix(in srgb, var(--vm-tobacco) 22%, transparent);
		background: var(--vm-parchment);
		color: inherit;
		font: inherit;
		line-height: inherit;
		text-align: left;
		box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.45);
		cursor: pointer;
	}

	:global(button.free-form-button.provider-config-modal__card--action:not(:disabled):hover),
	:global(button.free-form-button.provider-config-modal__card--action:not(:disabled):focus-visible) {
		animation: none;
		opacity: 1;
		border-color: color-mix(in srgb, var(--vm-status-amber) 55%, transparent);
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--vm-status-amber) 38%, transparent);
	}

	:global(
		button.free-form-button.provider-config-modal__card--action.provider-config-modal__card--pending
	) {
		border-color: color-mix(in srgb, var(--vm-status-amber) 40%, transparent);
		animation: provider-config-pending-glow 900ms steps(2, end) infinite;
	}

	.provider-config-modal__card--data {
		border-color: color-mix(in srgb, var(--vm-tobacco) 18%, transparent);
	}

	.provider-config-modal__card-main {
		display: grid;
		gap: 0.2rem;
		min-width: 0;
	}

	.provider-config-modal__card-main--hatch-data {
		grid-template-rows: auto auto;
		min-height: calc(
			clamp(0.5625rem, 1.6vw, 0.6875rem) * 1.45 + clamp(0.5rem, 1.4vw, 0.625rem) * 1.55 + 0.2rem
		);
	}

	.provider-config-modal__card-aside {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		justify-content: center;
		min-height: 100%;
		flex-shrink: 0;
	}

	.provider-config-modal__card-label {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1.45;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: inherit;
	}

	.provider-config-modal__card-description {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5rem, 1.4vw, 0.625rem);
		line-height: 1.55;
		color: inherit;
		opacity: 0.82;
		min-height: 1.55em;
	}

	.provider-config-modal__status-chip {
		display: inline-block;
		padding: 0.22rem 0.45rem;
		border: 2px solid color-mix(in srgb, var(--vm-tobacco) 22%, transparent);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5rem, 1.4vw, 0.5625rem);
		line-height: 1.35;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		white-space: nowrap;
		color: inherit;
	}

	.provider-config-modal__status-chip--ready {
		border-color: color-mix(in srgb, var(--vm-status-sage) 45%, transparent);
		background: color-mix(in srgb, var(--vm-status-sage) 12%, transparent);
		color: var(--vm-status-sage);
	}

	.provider-config-modal__status-chip--pending {
		border-color: color-mix(in srgb, var(--vm-status-amber) 45%, transparent);
		background: color-mix(in srgb, var(--vm-status-amber) 10%, transparent);
		color: var(--vm-status-amber);
	}

	.provider-config-modal__status-chip--fetching {
		border-color: color-mix(in srgb, var(--vm-status-amber) 45%, transparent);
		background: color-mix(in srgb, var(--vm-status-amber) 10%, transparent);
		color: var(--vm-status-amber);
		animation: provider-config-fetch-pulse 900ms steps(2, end) infinite;
	}

	.provider-config-modal__status-chip--unavailable {
		opacity: 0.72;
	}

	.provider-config-modal__actions {
		display: flex;
		flex-direction: column;
	}

	.provider-config-modal__action-row {
		display: flex;
		gap: clamp(0.45rem, 1.2vw, 0.65rem);
	}

	.provider-config-modal__action-row :global(.provider-config-modal__action-button) {
		flex: 1 1 0;
		min-width: 0;
		font-size: clamp(0.6875rem, 2vw, 0.875rem);
	}

	.provider-config-modal__action-row :global(.provider-config-modal__action-button--primary) {
		flex: 1.35 1 0;
	}

	.provider-config-modal__coming-soon {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.6875rem, 2vw, 0.8125rem);
		line-height: 1.5;
		text-align: center;
		color: inherit;
		opacity: 0.88;
	}

	@keyframes provider-config-fetch-pulse {
		0%,
		49% {
			opacity: 1;
		}
		50%,
		100% {
			opacity: 0.55;
		}
	}

	@keyframes provider-config-pending-glow {
		0%,
		49% {
			opacity: 1;
			box-shadow: 0 0 0 0 color-mix(in srgb, var(--vm-status-amber) 0%, transparent);
		}
		50%,
		100% {
			opacity: 0.82;
			box-shadow: 0 0 0 2px color-mix(in srgb, var(--vm-status-amber) 38%, transparent);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		:global(
			button.free-form-button.provider-config-modal__card--action.provider-config-modal__card--pending
		),
		.provider-config-modal__status-chip--fetching {
			animation: none;
		}
	}
</style>
