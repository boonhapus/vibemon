<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	import { fetchCrew, type CrewMember } from '$lib/domains/trainer/hatchApi';
	import DialogBox from '$lib/ui/DialogBox.svelte';
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';
	import SegmentedHpBar from '$lib/ui/SegmentedHpBar.svelte';

	import { buildParty } from './crewSlots';

	let members = $state<CrewMember[]>([]);
	let loading = $state(true);
	let selectedId = $state('');

	let party = $derived(buildParty(members));
	let lead = $derived(party[0]);
	let bench = $derived(party.slice(1));
	let filledCount = $derived(members.length);

	function handleCancel() {
		void goto('/hatch');
	}

	function handleFormation() {
		void goto('/deck/crew');
	}

	onMount(() => {
		void (async () => {
			try {
				const crew = await fetchCrew();
				members = crew.members;
				selectedId = crew.members[0]?.id ?? '';
			} catch {
				showGameToast('Could not load your crew.', 'brick');
			} finally {
				loading = false;
			}
		})();
	});
</script>

<SceneFrame bandedTop="#8a9460" bandedBase="#4f5734" bandedShadow="#2f3622">
	<div class="crew-scene">
		<div class="crew-scene__roster">
			{#if lead}
				<FreeFormButton
					class="crew-scene__lead-button"
					disabled={lead.empty}
					ariaLabel={lead.empty
						? 'Empty lead slot'
						: `${lead.name}, level ${lead.level}, ${lead.currentHp} of ${lead.maxHp} HP`}
					onclick={() => {
						if (!lead.empty) selectedId = lead.id;
					}}
				>
					<GamePanel tone="status" class={['crew-scene__lead-panel', lead.empty && 'crew-scene__lead-panel--empty'].filter(Boolean).join(' ')}>
						<div class="crew-scene__lead">
							<img
								class={['crew-scene__lead-sprite', lead.empty && 'crew-scene__sprite--empty'].filter(Boolean).join(' ')}
								src={lead.empty ? '/game/sprites/hatchling-silhouette@128.png' : lead.spriteSrc}
								alt=""
								decoding="async"
							/>
							<div class="crew-scene__lead-meta">
								{#if lead.empty}
									<p class="crew-scene__empty-label">Empty</p>
								{:else}
									<div class="crew-scene__name-row">
										<span class="crew-scene__name">{lead.name}</span>
										<span class="crew-scene__level">Lv{lead.level}</span>
									</div>
									<SegmentedHpBar current={lead.currentHp} max={lead.maxHp} />
								{/if}
							</div>
						</div>
					</GamePanel>
				</FreeFormButton>
			{/if}

			<ul class="crew-scene__bench" role="list">
				{#each bench as member (member.id)}
					<li class="crew-scene__bench-item">
						<FreeFormButton
							class="crew-scene__bench-button"
							disabled={member.empty}
							ariaLabel={member.empty
								? 'Empty party slot'
								: `${member.name}, level ${member.level}, ${member.currentHp} of ${member.maxHp} HP`}
							onclick={() => {
								if (!member.empty) selectedId = member.id;
							}}
						>
							<GamePanel
								tone="status"
								class={[
									'crew-scene__bench-panel',
									member.empty && 'crew-scene__bench-panel--empty',
									!member.empty && selectedId === member.id && 'crew-scene__bench-panel--selected'
								]
									.filter(Boolean)
									.join(' ')}
							>
								<div class="crew-scene__bench-row">
									<img
										class={['crew-scene__bench-sprite', member.empty && 'crew-scene__sprite--empty'].filter(Boolean).join(' ')}
										src={member.empty ? '/game/sprites/hatchling-silhouette@128.png' : member.spriteSrc}
										alt=""
										decoding="async"
									/>
									<div class="crew-scene__bench-meta">
										{#if member.empty}
											<p class="crew-scene__empty-label">Empty</p>
										{:else}
											<div class="crew-scene__name-row">
												<span class="crew-scene__name">{member.name}</span>
												<span class="crew-scene__level">Lv{member.level}</span>
											</div>
											<SegmentedHpBar
												compact
												current={member.currentHp}
												max={member.maxHp}
											/>
										{/if}
									</div>
								</div>
							</GamePanel>
						</FreeFormButton>
					</li>
				{/each}
			</ul>
		</div>

		<div class="crew-scene__footer">
			<div class="crew-scene__dialog">
				<DialogBox
					text={loading ? 'Loading your crew...' : filledCount === 0 ? 'No Vibemon adopted yet.' : 'Choose a Vibemon.'}
					showCursor={false}
					typewriter={false}
				/>
			</div>

			<div class="crew-scene__footer-actions">
				<FreeFormButton class="crew-scene__cancel-button" ariaLabel="Open formation view" onclick={handleFormation}>
					<GamePanel tone="command" class="crew-scene__cancel-panel">
						<span class="crew-scene__cancel-label">Formation</span>
					</GamePanel>
				</FreeFormButton>

				<FreeFormButton class="crew-scene__cancel-button" ariaLabel="Cancel" onclick={handleCancel}>
					<GamePanel tone="command" class="crew-scene__cancel-panel">
						<span class="crew-scene__cancel-label">Cancel</span>
					</GamePanel>
				</FreeFormButton>
			</div>
		</div>
	</div>
</SceneFrame>

<style>
	.crew-scene {
		position: relative;
		min-height: 100dvh;
		padding: clamp(1rem, 3vh, 1.75rem)
			max(clamp(1rem, 3vw, 1.75rem), var(--vm-settings-corner-reserve))
			clamp(1.25rem, 4vh, 2rem)
			clamp(1rem, 3vw, 1.75rem);
		display: grid;
		grid-template-rows: minmax(0, 1fr) auto;
		gap: clamp(0.85rem, 2.4vh, 1.35rem);
	}

	.crew-scene__roster {
		display: grid;
		grid-template-columns: minmax(0, 1.12fr) minmax(0, 0.88fr);
		gap: clamp(0.75rem, 2vw, 1rem);
		align-items: stretch;
		min-height: 0;
	}

	:global(.crew-scene__lead-button) {
		width: 100%;
		height: 100%;
	}

	:global(.crew-scene__lead-panel) {
		width: 100%;
		height: 100%;
	}

	:global(.crew-scene__lead-panel--empty),
	:global(.crew-scene__bench-panel--empty) {
		opacity: 0.72;
	}

	.crew-scene__lead {
		display: grid;
		grid-template-columns: minmax(5.5rem, 34%) minmax(0, 1fr);
		gap: clamp(0.65rem, 2vw, 1rem);
		align-items: center;
		min-height: clamp(9rem, 28vh, 13rem);
		padding: clamp(0.35rem, 1vw, 0.55rem);
	}

	.crew-scene__lead-sprite,
	.crew-scene__bench-sprite {
		width: 100%;
		height: auto;
		max-height: 100%;
		object-fit: contain;
		image-rendering: pixelated;
		image-rendering: crisp-edges;
		user-select: none;
		pointer-events: none;
	}

	.crew-scene__sprite--empty {
		filter: brightness(0);
		opacity: 0.35;
	}

	.crew-scene__lead-meta,
	.crew-scene__bench-meta {
		min-width: 0;
	}

	.crew-scene__empty-label {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.75rem);
		line-height: 1.5;
		letter-spacing: 0.05em;
		color: color-mix(in srgb, var(--vm-tobacco) 62%, var(--vm-brass));
	}

	.crew-scene__name-row {
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 0.45rem 0.65rem;
		margin-bottom: clamp(0.45rem, 1.2vh, 0.7rem);
	}

	.crew-scene__name {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.6875rem, 2vw, 0.875rem);
		line-height: 1.5;
		letter-spacing: 0.04em;
	}

	.crew-scene__level {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.75rem);
		line-height: 1.5;
		letter-spacing: 0.03em;
	}

	.crew-scene__bench {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: clamp(0.45rem, 1.2vh, 0.65rem);
		min-height: 0;
	}

	.crew-scene__bench-item,
	:global(.crew-scene__bench-button) {
		width: 100%;
	}

	.crew-scene__bench-row {
		display: grid;
		grid-template-columns: clamp(2.75rem, 10vw, 3.75rem) minmax(0, 1fr);
		gap: clamp(0.45rem, 1.4vw, 0.65rem);
		align-items: center;
		padding: clamp(0.2rem, 0.6vw, 0.35rem);
	}

	.crew-scene__bench-sprite {
		max-height: clamp(2.5rem, 7vw, 3.25rem);
	}

	:global(.crew-scene__bench-panel--selected) {
		outline: 2px solid var(--vm-mustard);
		outline-offset: 2px;
	}

	.crew-scene__footer {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: clamp(0.75rem, 2vw, 1rem);
		align-items: end;
	}

	.crew-scene__dialog {
		display: flex;
		justify-content: flex-start;
	}

	.crew-scene__dialog :global(.dialog-box) {
		width: min(100%, var(--vm-hud-dialog-width));
	}

	.crew-scene__footer-actions {
		display: flex;
		gap: clamp(0.5rem, 1.5vw, 0.75rem);
	}

	:global(.crew-scene__cancel-button) {
		flex-shrink: 0;
	}

	:global(.crew-scene__cancel-panel) {
		min-width: clamp(5.5rem, 18vw, 7.5rem);
	}

	.crew-scene__cancel-label {
		display: block;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.6875rem, 2vw, 0.875rem);
		line-height: 1.5;
		letter-spacing: 0.06em;
		text-align: center;
	}
</style>
