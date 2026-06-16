<script lang="ts">
	import type { CrewMember } from '$lib/domains/trainer/hatchApi';
	import GameButton from '$lib/ui/GameButton.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';

	const PLACEHOLDER_SPRITE = '/game/sprites/hatchling-silhouette@128.png';

	let {
		open = $bindable(false),
		speciesName = '',
		busy = false,
		swapTargets = null,
		releaseTargetId = $bindable<string | null>(null),
		onConfirm
	}: {
		open?: boolean;
		speciesName?: string;
		busy?: boolean;
		swapTargets?: CrewMember[] | null;
		releaseTargetId?: string | null;
		onConfirm?: (nickname: string | null) => void | Promise<void>;
	} = $props();

	let nickname = $state('');
	let needsSwap = $derived(Boolean(swapTargets?.length));
	let canConfirm = $derived(!needsSwap || Boolean(releaseTargetId));
	let selectedMember = $derived(
		swapTargets?.find((member) => member.id === releaseTargetId) ?? null
	);
	let selectedLabel = $derived(selectedMember ? memberLabel(selectedMember) : null);

	$effect(() => {
		if (open) {
			nickname = '';
			if (!needsSwap) releaseTargetId = null;
		}
	});

	function memberLabel(member: CrewMember): string {
		return (member.nickname?.trim() || member.name).toUpperCase();
	}

	function close() {
		open = false;
		releaseTargetId = null;
	}

	function toggleReleaseTarget(memberId: string) {
		releaseTargetId = releaseTargetId === memberId ? null : memberId;
	}

	function handleSkip() {
		if (!canConfirm) return;
		void onConfirm?.(null);
	}

	function handleConfirm() {
		if (!canConfirm) return;
		const trimmed = nickname.trim();
		void onConfirm?.(trimmed || null);
	}
</script>

{#if open}
	<div class="adopt-crew-modal" role="presentation">
		<button type="button" class="adopt-crew-modal__backdrop" aria-label="Close" onclick={close}></button>
		<GamePanel
			tone="status"
			class={['adopt-crew-modal__panel', needsSwap && 'adopt-crew-modal__panel--swap']
				.filter(Boolean)
				.join(' ')}
		>
			<div class="adopt-crew-modal__content">
				{#if needsSwap && swapTargets}
					<div class="adopt-crew-modal__intro">
						<h2 class="adopt-crew-modal__title">Swap for {speciesName}</h2>
						<ul class="adopt-crew-modal__roster" role="list" aria-label="Choose a crew member to release">
							{#each swapTargets as member (member.id)}
								<li>
									<button
										type="button"
										class={[
											'adopt-crew-modal__member',
											releaseTargetId === member.id && 'adopt-crew-modal__member--selected'
										]
											.filter(Boolean)
											.join(' ')}
										aria-pressed={releaseTargetId === member.id}
										aria-label={releaseTargetId === member.id
											? `Deselect ${memberLabel(member)}`
											: `Release ${memberLabel(member)} to the Wild`}
										disabled={busy}
										onclick={() => toggleReleaseTarget(member.id)}
									>
										<img
											class="adopt-crew-modal__sprite"
											src={member.sprite_url ?? PLACEHOLDER_SPRITE}
											alt=""
											decoding="async"
										/>
										<span class="adopt-crew-modal__member-name">{memberLabel(member)}</span>
										<span class="adopt-crew-modal__member-level">Lv{member.level}</span>
									</button>
								</li>
							{/each}
						</ul>
						{#if selectedLabel}
							<p
								class="adopt-crew-modal__release-note adopt-crew-modal__release-note--selected"
								aria-live="polite"
							>
								Releasing {selectedLabel}.
							</p>
						{:else}
							<p class="adopt-crew-modal__release-note adopt-crew-modal__release-note--hint">
								Tap a Vibemon to release.
							</p>
						{/if}
					</div>
				{:else}
					<p class="adopt-crew-modal__prompt">
						Want to give <strong class="adopt-crew-modal__species">{speciesName}</strong> a nickname before
						they join the crew?
					</p>
				{/if}

				<input
					class="adopt-crew-modal__input"
					type="text"
					maxlength="18"
					bind:value={nickname}
					placeholder="Nickname (optional)"
					aria-label="Nickname (optional)"
					disabled={busy || !canConfirm}
				/>

				<div class="adopt-crew-modal__actions">
					<GameButton
						variant="secondary"
						class="adopt-crew-modal__action"
						ariaLabel="Skip nickname"
						disabled={busy || !canConfirm}
						onclick={handleSkip}
					>
						Skip
					</GameButton>
					<GameButton
						variant="primary"
						class="adopt-crew-modal__action"
						ariaLabel={needsSwap ? 'Swap selected Vibemon for the new hatchling' : 'Confirm adoption'}
						disabled={busy || !canConfirm}
						onclick={handleConfirm}
					>
						{needsSwap ? 'Swap' : 'Adopt'}
					</GameButton>
				</div>
			</div>
		</GamePanel>
	</div>
{/if}

<style>
	.adopt-crew-modal {
		position: fixed;
		inset: 0;
		z-index: 30;
		display: grid;
		place-items: center;
		padding: clamp(0.75rem, 3vw, 1.5rem);
		pointer-events: auto;
	}

	.adopt-crew-modal__backdrop {
		position: absolute;
		inset: 0;
		border: 0;
		background: rgb(26 18 36 / 0.56);
		cursor: pointer;
	}

	:global(.adopt-crew-modal__panel) {
		position: relative;
		z-index: 1;
		width: min(100%, 36rem);
		max-height: min(92dvh, 44rem);
		overflow: auto;
	}

	:global(.adopt-crew-modal__panel--swap) {
		width: min(100%, 42rem);
	}

	:global(.adopt-crew-modal__panel .game-panel__content) {
		padding: clamp(1rem, 2.8vw, 1.35rem);
	}

	.adopt-crew-modal__content {
		display: flex;
		flex-direction: column;
		gap: clamp(1rem, 2.8vw, 1.25rem);
	}

	.adopt-crew-modal__intro {
		display: flex;
		flex-direction: column;
		gap: var(--vm-space-md);
	}

	.adopt-crew-modal__title {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.8125rem, 2.4vw, 1.0625rem);
		line-height: 1.45;
		letter-spacing: 0.05em;
		color: var(--vm-tobacco-black);
		text-align: center;
	}

	.adopt-crew-modal__prompt {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.6875rem, 2vw, 0.875rem);
		line-height: 1.65;
		letter-spacing: 0.04em;
		color: var(--vm-tobacco-black);
	}

	.adopt-crew-modal__species {
		font-weight: inherit;
		color: var(--vm-plum);
	}

	.adopt-crew-modal__roster {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: clamp(0.55rem, 1.8vw, 0.85rem);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.adopt-crew-modal__member {
		display: grid;
		grid-template-rows: auto auto auto;
		justify-items: center;
		gap: 0.35rem;
		width: 100%;
		min-height: clamp(7.5rem, 22vw, 9.5rem);
		padding: clamp(0.55rem, 1.8vw, 0.85rem) clamp(0.4rem, 1.2vw, 0.65rem);
		border: 2px solid color-mix(in srgb, var(--vm-tobacco) 24%, transparent);
		background: color-mix(in srgb, var(--vm-parchment) 88%, var(--vm-panel-command-bg));
		color: var(--vm-tobacco);
		font-family: var(--vm-font-ui);
		cursor: pointer;
		-webkit-tap-highlight-color: transparent;
	}

	.adopt-crew-modal__member--selected {
		border-color: var(--vm-mustard);
		background: color-mix(in srgb, var(--vm-mustard) 18%, var(--vm-parchment));
		box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--vm-mustard) 40%, transparent);
	}

	.adopt-crew-modal__member:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.adopt-crew-modal__sprite {
		width: clamp(3.75rem, 14vw, 5.5rem);
		height: clamp(3.75rem, 14vw, 5.5rem);
		object-fit: contain;
		image-rendering: pixelated;
		image-rendering: crisp-edges;
		pointer-events: none;
		user-select: none;
	}

	.adopt-crew-modal__member-name {
		font-size: clamp(0.625rem, 1.9vw, 0.8125rem);
		line-height: 1.35;
		letter-spacing: 0.04em;
		text-align: center;
	}

	.adopt-crew-modal__member-level {
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1.35;
		letter-spacing: 0.03em;
		opacity: 0.82;
	}

	.adopt-crew-modal__release-note {
		margin: 0;
		padding: 0.55rem 0.65rem;
		border: 1px solid color-mix(in srgb, var(--vm-tobacco) 18%, transparent);
		background: color-mix(in srgb, var(--vm-tobacco) 6%, var(--vm-parchment));
		font-family: var(--vm-font-ui);
		font-size: clamp(0.625rem, 1.8vw, 0.75rem);
		line-height: 1.55;
		letter-spacing: 0.03em;
	}

	.adopt-crew-modal__release-note--hint,
	.adopt-crew-modal__release-note--selected {
		text-align: center;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.adopt-crew-modal__release-note--hint {
		font-style: italic;
		opacity: 0.88;
	}

	.adopt-crew-modal__input {
		width: 100%;
		box-sizing: border-box;
		margin: 0;
		padding: 0.65rem 0.75rem;
		border: 2px solid var(--vm-tobacco);
		background: var(--vm-parchment);
		color: var(--vm-tobacco);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.625rem, 1.9vw, 0.8125rem);
		line-height: 1.5;
	}

	.adopt-crew-modal__actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.65rem;
	}

	.adopt-crew-modal__actions :global(.adopt-crew-modal__action) {
		min-width: clamp(5rem, 18vw, 7rem);
		font-size: clamp(0.625rem, 1.9vw, 0.8125rem);
	}

	@media (max-width: 520px) {
		.adopt-crew-modal__roster {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
</style>
