<script lang="ts">
	import HatchCandidatePanel from '$lib/domains/trainer/HatchCandidatePanel.svelte';
	import type { HatchCandidate } from '$lib/domains/trainer/hatchApi';
	import SegmentedHpBar from '$lib/ui/SegmentedHpBar.svelte';

	import { buildCrewStoryEntries } from './crewTimeline';

	type ShowcaseTab = 'stats' | 'moves' | 'sources' | 'story';

	let {
		candidate,
		level,
		currentHp,
		maxHp,
		detailHint = $bindable<string | null>(null),
		activeTab = $bindable<ShowcaseTab>('stats')
	}: {
		candidate: HatchCandidate;
		level: number;
		currentHp: number;
		maxHp: number;
		detailHint?: string | null;
		activeTab?: ShowcaseTab;
	} = $props();

	let hatchTab = $state<'stats' | 'moves' | 'sources'>('stats');
	let storyEntries = $derived(buildCrewStoryEntries(candidate));

	$effect(() => {
		if (activeTab === 'story') return;
		hatchTab = activeTab;
	});

	function selectTab(tab: ShowcaseTab) {
		activeTab = tab;
		detailHint = null;
	}
</script>

<div class="crew-showcase-panel">
	<div class="crew-showcase-panel__header">
		<span class="crew-showcase-panel__level">Lv{level}</span>
		<SegmentedHpBar current={currentHp} max={maxHp} />
	</div>

	<div class="crew-showcase-panel__tabs" role="tablist" aria-label="Crew member details">
		<button
			type="button"
			class="crew-showcase-panel__tab"
			class:crew-showcase-panel__tab--active={activeTab === 'stats'}
			role="tab"
			aria-selected={activeTab === 'stats'}
			onclick={() => selectTab('stats')}
		>
			Stats
		</button>
		<button
			type="button"
			class="crew-showcase-panel__tab"
			class:crew-showcase-panel__tab--active={activeTab === 'moves'}
			role="tab"
			aria-selected={activeTab === 'moves'}
			onclick={() => selectTab('moves')}
		>
			Moves
		</button>
		<button
			type="button"
			class="crew-showcase-panel__tab"
			class:crew-showcase-panel__tab--active={activeTab === 'sources'}
			role="tab"
			aria-selected={activeTab === 'sources'}
			onclick={() => selectTab('sources')}
		>
			Sources
		</button>
		<button
			type="button"
			class="crew-showcase-panel__tab"
			class:crew-showcase-panel__tab--active={activeTab === 'story'}
			role="tab"
			aria-selected={activeTab === 'story'}
			onclick={() => selectTab('story')}
		>
			Story
		</button>
	</div>

	{#if activeTab === 'story'}
		<div class="crew-showcase-panel__story" role="tabpanel">
			<ol class="crew-showcase-panel__story-list">
				{#each storyEntries as entry (entry.id)}
					<li class="crew-showcase-panel__story-item">
						<span class="crew-showcase-panel__story-title">{entry.title}</span>
						<p class="crew-showcase-panel__story-body">{entry.body}</p>
					</li>
				{/each}
			</ol>
		</div>
	{:else}
		<div class="crew-showcase-panel__detail">
			<HatchCandidatePanel
				{candidate}
				showActions={false}
				bind:detailHint
				bind:activeTab={hatchTab}
			/>
		</div>
	{/if}
</div>

<style>
	.crew-showcase-panel {
		display: flex;
		flex-direction: column;
		gap: clamp(0.4rem, 1.2vh, 0.65rem);
		width: 100%;
		min-width: 0;
	}

	.crew-showcase-panel__header {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: 0.35rem 0.65rem;
		align-items: center;
		padding-bottom: 0.35rem;
		border-bottom: 1px solid color-mix(in srgb, var(--vm-tobacco) 16%, transparent);
	}

	.crew-showcase-panel__level {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.75rem);
		line-height: 1.5;
		letter-spacing: 0.05em;
		color: color-mix(in srgb, var(--vm-plum) 42%, var(--vm-brass));
	}

	.crew-showcase-panel__tabs {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}

	.crew-showcase-panel__tab {
		padding: 0.35rem 0.55rem;
		border: 0;
		background: transparent;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5rem, 1.45vw, 0.625rem);
		line-height: 1.4;
		letter-spacing: 0.06em;
		color: color-mix(in srgb, var(--vm-tobacco) 62%, var(--vm-brass));
		cursor: pointer;
	}

	.crew-showcase-panel__tab--active {
		color: var(--vm-tobacco-black);
		box-shadow: inset 0 -2px 0 var(--vm-mustard);
	}

	.crew-showcase-panel__detail :global(.hatch-candidate-panel__tabs) {
		display: none;
	}

	.crew-showcase-panel__story-list {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		gap: 0.75rem;
	}

	.crew-showcase-panel__story-item {
		display: grid;
		gap: 0.15rem;
		padding-bottom: 0.65rem;
		border-bottom: 1px dashed color-mix(in srgb, var(--vm-tobacco) 24%, transparent);
	}

	.crew-showcase-panel__story-item:last-child {
		padding-bottom: 0;
		border-bottom: 0;
	}

	.crew-showcase-panel__story-title {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.6875rem, 2vw, 0.8125rem);
		line-height: 1.35;
		letter-spacing: 0.05em;
		color: var(--vm-tobacco-black);
	}

	.crew-showcase-panel__story-body {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.6vw, 0.75rem);
		line-height: 1.5;
		letter-spacing: 0.03em;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-brass));
	}
</style>
