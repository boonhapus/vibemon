<script lang="ts">
	import { goto } from '$app/navigation';

	import DialogBox from '$lib/ui/DialogBox.svelte';
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';

	type CrewMember = {
		id: string;
		name: string;
		level: number;
		gender: 'male' | 'female';
		currentHp: number;
		maxHp: number;
		spriteSrc: string;
	};

	const PLACEHOLDER_SPRITE = '/game/sprites/hatchling-silhouette.png';

	const CREW: CrewMember[] = [
		{
			id: 'lead',
			name: 'MOSSPUP',
			level: 5,
			gender: 'male',
			currentHp: 24,
			maxHp: 24,
			spriteSrc: PLACEHOLDER_SPRITE
		},
		{
			id: 'slot-2',
			name: 'FERNKIT',
			level: 4,
			gender: 'female',
			currentHp: 19,
			maxHp: 19,
			spriteSrc: PLACEHOLDER_SPRITE
		},
		{
			id: 'slot-3',
			name: 'BARKLING',
			level: 6,
			gender: 'female',
			currentHp: 28,
			maxHp: 28,
			spriteSrc: PLACEHOLDER_SPRITE
		},
		{
			id: 'slot-4',
			name: 'THISTAIL',
			level: 3,
			gender: 'male',
			currentHp: 16,
			maxHp: 16,
			spriteSrc: PLACEHOLDER_SPRITE
		},
		{
			id: 'slot-5',
			name: 'DUSKPAW',
			level: 7,
			gender: 'female',
			currentHp: 31,
			maxHp: 31,
			spriteSrc: PLACEHOLDER_SPRITE
		},
		{
			id: 'slot-6',
			name: 'GLIMMER',
			level: 5,
			gender: 'female',
			currentHp: 22,
			maxHp: 22,
			spriteSrc: PLACEHOLDER_SPRITE
		}
	];

	let selectedId = $state(CREW[0]?.id ?? '');
	let lead = $derived(CREW[0]);
	let bench = $derived(CREW.slice(1));

	function hpPercent(member: CrewMember) {
		return Math.max(0, Math.min(100, (member.currentHp / member.maxHp) * 100));
	}

	function genderLabel(gender: CrewMember['gender']) {
		return gender === 'male' ? '♂' : '♀';
	}

	function handleCancel() {
		void goto('/hatch');
	}
</script>

<SceneFrame bandedTop="#8a9460" bandedBase="#4f5734" bandedShadow="#2f3622">
	<div class="crew-scene">
		<div class="crew-scene__roster">
			{#if lead}
				<FreeFormButton
					class="crew-scene__lead-button"
					ariaLabel="{lead.name}, level {lead.level}, {lead.currentHp} of {lead.maxHp} HP"
					onclick={() => (selectedId = lead.id)}
				>
					<GamePanel tone="status" class="crew-scene__lead-panel">
						<div class="crew-scene__lead">
							<img class="crew-scene__lead-sprite" src={lead.spriteSrc} alt="" decoding="async" />
							<div class="crew-scene__lead-meta">
								<div class="crew-scene__name-row">
									<span class="crew-scene__name">{lead.name}</span>
									<span class="crew-scene__level">Lv{lead.level}</span>
									<span class="crew-scene__gender">{genderLabel(lead.gender)}</span>
								</div>
								<div class="crew-scene__hp">
									<div class="crew-scene__hp-label">HP</div>
									<div class="crew-scene__hp-track" aria-hidden="true">
										<div class="crew-scene__hp-fill" style:width="{hpPercent(lead)}%"></div>
									</div>
									<div class="crew-scene__hp-values">
										{lead.currentHp} / {lead.maxHp}
									</div>
								</div>
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
							ariaLabel="{member.name}, level {member.level}, {member.currentHp} of {member.maxHp} HP"
							onclick={() => (selectedId = member.id)}
						>
							<GamePanel
								tone="status"
								class={['crew-scene__bench-panel', selectedId === member.id && 'crew-scene__bench-panel--selected']
									.filter(Boolean)
									.join(' ')}
							>
								<div class="crew-scene__bench-row">
									<img class="crew-scene__bench-sprite" src={member.spriteSrc} alt="" decoding="async" />
									<div class="crew-scene__bench-meta">
										<div class="crew-scene__name-row">
											<span class="crew-scene__name">{member.name}</span>
											<span class="crew-scene__level">Lv{member.level}</span>
											<span class="crew-scene__gender">{genderLabel(member.gender)}</span>
										</div>
										<div class="crew-scene__hp crew-scene__hp--compact">
											<div class="crew-scene__hp-track" aria-hidden="true">
												<div class="crew-scene__hp-fill" style:width="{hpPercent(member)}%"></div>
											</div>
											<div class="crew-scene__hp-values">
												{member.currentHp} / {member.maxHp}
											</div>
										</div>
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
				<DialogBox text="Choose a Vibemon." showCursor={false} typewriter={false} />
			</div>

			<FreeFormButton class="crew-scene__cancel-button" ariaLabel="Cancel" onclick={handleCancel}>
				<GamePanel tone="command" class="crew-scene__cancel-panel">
					<span class="crew-scene__cancel-label">Cancel</span>
				</GamePanel>
			</FreeFormButton>
		</div>
	</div>
</SceneFrame>

<style>
	.crew-scene {
		position: relative;
		min-height: 100dvh;
		padding: clamp(1rem, 3vh, 1.75rem) clamp(1rem, 3vw, 1.75rem) clamp(1.25rem, 4vh, 2rem);
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
		filter: brightness(0);
		user-select: none;
		pointer-events: none;
	}

	.crew-scene__lead-meta,
	.crew-scene__bench-meta {
		min-width: 0;
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

	.crew-scene__level,
	.crew-scene__gender,
	.crew-scene__hp-label,
	.crew-scene__hp-values {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.75rem);
		line-height: 1.5;
		letter-spacing: 0.03em;
	}

	.crew-scene__gender {
		color: color-mix(in srgb, var(--vm-burnt-orange) 72%, var(--vm-tobacco));
	}

	.crew-scene__hp {
		display: grid;
		grid-template-columns: auto 1fr;
		grid-template-rows: auto auto;
		gap: 0.35rem 0.55rem;
		align-items: center;
	}

	.crew-scene__hp--compact {
		grid-template-columns: 1fr;
	}

	.crew-scene__hp-label {
		grid-row: span 2;
	}

	.crew-scene__hp-track {
		height: clamp(0.55rem, 1.5vw, 0.75rem);
		border: 2px solid var(--vm-tobacco);
		background: color-mix(in srgb, var(--vm-tobacco) 12%, var(--vm-parchment));
		padding: 1px;
	}

	.crew-scene__hp-fill {
		height: 100%;
		background: var(--vm-status-sage);
	}

	.crew-scene__hp-values {
		text-align: right;
	}

	.crew-scene__hp--compact .crew-scene__hp-values {
		text-align: left;
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

	@media (max-width: 720px) {
		.crew-scene__roster {
			grid-template-columns: 1fr;
		}

		.crew-scene__lead {
			min-height: clamp(7rem, 22vh, 10rem);
		}
	}

	@media (max-width: 480px) {
		.crew-scene__footer {
			grid-template-columns: 1fr;
		}

		:global(.crew-scene__cancel-button) {
			justify-self: end;
		}
	}
</style>
