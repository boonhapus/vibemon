<script lang="ts">
	import HatchCandidatePanel from '$lib/domains/trainer/HatchCandidatePanel.svelte';
	import { candidateDisplayName, type HatchCandidate } from '$lib/domains/trainer/hatchApi';
	import { evolutionLineHint } from '$lib/domains/trainer/evolutionLineCopy';
	import ProviderPatchPanel from '$lib/domains/trainer/ProviderPatchPanel.svelte';
	import ElementBadge from '$lib/ui/ElementBadge.svelte';
	import SegmentedHpBar from '$lib/ui/SegmentedHpBar.svelte';

	import EvolutionLinePips from '$lib/domains/trainer/EvolutionLinePips.svelte';
	import PowerPips from '$lib/domains/trainer/PowerPips.svelte';

	import { buildCrewStoryEntries } from './crewTimeline';

	type ShowcaseTab = 'stats' | 'moves' | 'sources' | 'story';

	let {
		candidate,
		level,
		currentHp,
		maxHp,
		onDetailHintChange,
		activeTab = $bindable<ShowcaseTab>('stats')
	}: {
		candidate: HatchCandidate;
		level: number;
		currentHp: number;
		maxHp: number;
		onDetailHintChange?: (hint: string | null) => void;
		activeTab?: ShowcaseTab;
	} = $props();

	const HOVER_CLEAR_MS = 250;

	let hatchTab = $state<'stats' | 'moves' | 'sources'>('stats');
	let storyEntries = $derived(buildCrewStoryEntries(candidate));
	let displayName = $derived(candidateDisplayName(candidate));
	let powerPips = $derived(Math.min(Math.max(candidate.power_pips, 1), 3) as 1 | 2 | 3);
	let panelHint = $state<string | null>(null);
	let clearHintTimer: ReturnType<typeof setTimeout> | undefined;

	$effect(() => {
		if (activeTab === 'story') return;
		hatchTab = activeTab;
	});

	function cancelHintClear() {
		if (clearHintTimer) {
			clearTimeout(clearHintTimer);
			clearHintTimer = undefined;
		}
	}

	function selectTab(tab: ShowcaseTab) {
		cancelHintClear();
		activeTab = tab;
		panelHint = null;
		onDetailHintChange?.(null);
	}

	function showHint(text: string) {
		cancelHintClear();
		panelHint = text;
		onDetailHintChange?.(text);
	}

	function clearHint(text: string) {
		cancelHintClear();
		clearHintTimer = setTimeout(() => {
			if (panelHint === text) {
				panelHint = null;
				onDetailHintChange?.(null);
			}
			clearHintTimer = undefined;
		}, HOVER_CLEAR_MS);
	}

	function strengthHint(pips: 1 | 2 | 3): string {
		const context =
			pips === 3
				? 'on the high end for its evolution line'
				: pips === 2
					? 'right around the norm for its evolution line'
					: 'still building toward its line\'s potential';
		return `A measure of its BST relative to its evolution stages -- ${context}.`;
	}

	function runtimeHpHint(): string {
		return `${displayName} has ${currentHp} HP at level ${level}.`;
	}

	function storyHint(title: string, body: string): string {
		return `${title} — ${body}`;
	}
</script>

<ProviderPatchPanel
	title={false}
	fill
	mount="corner-tl"
	ariaLabel="Crew member details"
	class="crew-showcase-panel-shell"
>
	<div class="crew-showcase-panel">
		<div class="crew-showcase-panel__identity">
			<h2 class="crew-showcase-panel__name">{displayName}</h2>
			<ul class="crew-showcase-panel__types" role="list">
				{#each candidate.elements as element (element)}
					<li>
						<ElementBadge type={element} />
					</li>
				{/each}
			</ul>
		</div>

		<div class="crew-showcase-panel__ledger">
			<button
				type="button"
				class="crew-showcase-panel__ledger-hit"
				aria-label="Evolution line"
				onmouseenter={() =>
					showHint(evolutionLineHint(candidate.evolution_line, displayName, candidate.evo_seed))}
				onmouseleave={() =>
					clearHint(evolutionLineHint(candidate.evolution_line, displayName, candidate.evo_seed))}
				onfocus={() =>
					showHint(evolutionLineHint(candidate.evolution_line, displayName, candidate.evo_seed))}
				onblur={() =>
					clearHint(evolutionLineHint(candidate.evolution_line, displayName, candidate.evo_seed))}
			>
				<span class="crew-showcase-panel__ledger-key">EVO</span>
				<EvolutionLinePips line={candidate.evolution_line} />
			</button>
			<button
				type="button"
				class="crew-showcase-panel__ledger-hit crew-showcase-panel__ledger-hit--str"
				aria-label="Strength"
				onmouseenter={() => showHint(strengthHint(powerPips))}
				onmouseleave={() => clearHint(strengthHint(powerPips))}
				onfocus={() => showHint(strengthHint(powerPips))}
				onblur={() => clearHint(strengthHint(powerPips))}
			>
				<span class="crew-showcase-panel__ledger-key">STR</span>
				<PowerPips compact pips={powerPips} />
			</button>
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

		<div
			class="crew-showcase-panel__body"
			class:crew-showcase-panel__body--stats={activeTab === 'stats'}
		>
			<div
				class="crew-showcase-panel__body-stage"
				class:crew-showcase-panel__body-stage--stats={activeTab === 'stats'}
			>
				{#if activeTab === 'stats'}
					<div
						class="crew-showcase-panel__runtime"
						onmouseenter={() => showHint(runtimeHpHint())}
						onmouseleave={() => clearHint(runtimeHpHint())}
					>
						<span class="crew-showcase-panel__runtime-level">Lv{level}</span>
						<SegmentedHpBar current={currentHp} max={maxHp} />
					</div>
				{/if}

				<div class="crew-showcase-panel__tab-panel">
					{#if activeTab === 'story'}
						<div class="crew-showcase-panel__story" role="tabpanel">
							<ol class="crew-showcase-panel__story-list">
							{#each storyEntries as entry (entry.id)}
								{@const hint = storyHint(entry.title, entry.body)}
								<li
									class="crew-showcase-panel__story-item"
									onmouseenter={() => showHint(hint)}
									onmouseleave={() => clearHint(hint)}
									onfocus={() => showHint(hint)}
									onblur={() => clearHint(hint)}
									tabindex="0"
								>
									<span class="crew-showcase-panel__story-title">{entry.title}</span>
									<p class="crew-showcase-panel__story-body">{entry.body}</p>
								</li>
							{/each}
							</ol>
						</div>
					{:else}
						<HatchCandidatePanel
							{candidate}
							showActions={false}
							embedded
							hideStatKeys={['hp']}
							{onDetailHintChange}
							bind:activeTab={hatchTab}
						/>
					{/if}
				</div>
			</div>
		</div>
	</div>
</ProviderPatchPanel>

<style>
	:global(.crew-showcase-panel-shell.provider-patch-panel) {
		--provider-patch-pad: clamp(12px, 2vw, 18px);
		width: 100%;
		min-width: 0;
		height: 100%;
	}

	.crew-showcase-panel {
		--crew-inset-surface: color-mix(in srgb, var(--vm-tobacco) 10%, var(--vm-panel-command-bg));
		--crew-inset-border: color-mix(in srgb, var(--vm-tobacco) 16%, transparent);
		--hatch-pip-block-w: 0.8rem;
		--hatch-pip-block-h: 0.6rem;
		--hatch-pip-gap: 0.28rem;
		--hatch-readout-pip-gap: 0.55rem;
		--hatch-pip-track-width: calc(3 * var(--hatch-pip-block-w) + 2 * var(--hatch-pip-gap));
		--hatch-stats-grid: minmax(0, 1.38fr) minmax(0, max-content) var(--hatch-pip-track-width);

		display: flex;
		flex-direction: column;
		gap: 0.45rem;
		flex: 1;
		width: 100%;
		min-width: 0;
		min-height: 0;
		height: 100%;
		overflow: hidden;
		color: var(--vm-tobacco-black);
		font-family: var(--vm-font-ui);
	}

	.crew-showcase-panel__identity {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, max-content);
		align-items: center;
		gap: 0.35rem 0.75rem;
		margin-bottom: 0.35rem;
		flex-shrink: 0;
	}

	.crew-showcase-panel__name {
		margin: 0;
		font-size: clamp(0.9375rem, 2.85vw, 1.2rem);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.06em;
		color: var(--vm-tobacco-black);
	}

	.crew-showcase-panel__types {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: flex-end;
		justify-self: end;
		gap: 0.35rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.crew-showcase-panel__ledger {
		display: grid;
		grid-template-columns: var(--hatch-stats-grid);
		align-items: center;
		width: 100%;
		flex-shrink: 0;
	}

	.crew-showcase-panel__ledger-hit:first-child {
		grid-column: 1;
		grid-row: 1;
		justify-self: start;
	}

	.crew-showcase-panel__ledger-hit {
		display: inline-flex;
		align-items: center;
		gap: var(--hatch-readout-pip-gap);
		margin: 0;
		padding: 0;
		border: 0;
		background: transparent;
		color: inherit;
		font: inherit;
		cursor: help;
		-webkit-tap-highlight-color: transparent;
	}

	.crew-showcase-panel__ledger-hit--str {
		grid-column: 1 / -1;
		grid-row: 1;
		display: grid;
		grid-template-columns: var(--hatch-stats-grid);
		align-items: center;
		column-gap: 0.28rem;
	}

	.crew-showcase-panel__ledger-hit--str .crew-showcase-panel__ledger-key {
		grid-column: 2;
		justify-self: end;
		margin-right: var(--hatch-readout-pip-gap);
	}

	.crew-showcase-panel__ledger-hit--str :global(.power-pips) {
		grid-column: 3;
		justify-self: end;
	}

	.crew-showcase-panel__ledger-hit:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: 2px;
	}

	.crew-showcase-panel__ledger-key {
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1;
		letter-spacing: 0.08em;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-brass));
	}

	.crew-showcase-panel__tabs {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 0.2rem;
		padding: 0.18rem;
		border: 2px solid color-mix(in srgb, var(--vm-tobacco) 18%, transparent);
		border-radius: var(--vm-radius-sm);
		background: color-mix(in srgb, var(--vm-tobacco) 8%, var(--vm-panel-command-bg));
		flex-shrink: 0;
	}

	.crew-showcase-panel__tab {
		margin: 0;
		padding: 0.35rem 0.35rem;
		border: 0;
		border-radius: calc(var(--vm-radius-sm) - 2px);
		background: transparent;
		font-family: inherit;
		font-size: clamp(0.625rem, 1.8vw, 0.75rem);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.06em;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-brass));
		cursor: pointer;
		-webkit-tap-highlight-color: transparent;
	}

	.crew-showcase-panel__tab--active {
		background: var(--vm-panel-command-bg);
		color: var(--vm-tobacco-black);
		box-shadow:
			inset 0 0 0 1px color-mix(in srgb, var(--vm-tobacco) 22%, transparent),
			0 1px 0 rgb(42 30 22 / 0.12);
	}

	.crew-showcase-panel__tab:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: 1px;
	}

	.crew-showcase-panel__body {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		min-width: 0;
		overflow: hidden;
	}

	.crew-showcase-panel__body--stats {
		margin-top: 0.15rem;
		padding-top: 0.6rem;
	}

	.crew-showcase-panel__body-stage {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		height: 100%;
	}

	.crew-showcase-panel__body-stage--stats {
		gap: 0.45rem;
	}

	.crew-showcase-panel__runtime {
		display: grid;
		grid-template-columns: minmax(2.85rem, auto) minmax(0, 1fr);
		gap: 0.35rem 0.75rem;
		align-items: center;
		width: 100%;
		padding: 0.45rem 0.5rem;
		border-radius: var(--vm-radius-sm);
		background: var(--crew-inset-surface);
		box-shadow: inset 0 0 0 1px var(--crew-inset-border);
		flex-shrink: 0;
	}

	.crew-showcase-panel__runtime-level {
		justify-self: end;
		min-width: 2.85rem;
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1;
		letter-spacing: 0.08em;
		font-variant-numeric: tabular-nums;
		text-align: right;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-brass));
	}

	.crew-showcase-panel__tab-panel {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	.crew-showcase-panel__tab-panel :global(.hatch-candidate-panel) {
		--hatch-stats-grid: minmax(0, 1.38fr) minmax(0, max-content) var(--hatch-pip-track-width);
		flex: 1;
		min-height: 0;
		height: 100%;
	}

	.crew-showcase-panel__tab-panel :global(.hatch-candidate-panel__body) {
		flex: 1;
		min-height: 0;
	}

	.crew-showcase-panel__tab-panel :global(.hatch-candidate-panel__stats),
	.crew-showcase-panel__tab-panel :global(.hatch-candidate-panel__moves),
	.crew-showcase-panel__tab-panel :global(.hatch-candidate-panel__sources) {
		flex: 1;
		min-height: 0;
	}

	.crew-showcase-panel__tab-panel :global(.hatch-candidate-panel__stats-grid) {
		flex: 1;
		min-height: 0;
	}

	.crew-showcase-panel__story {
		flex: 1;
		min-height: 0;
		overflow-x: hidden;
		overflow-y: auto;
	}

	.crew-showcase-panel__story-list {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		gap: 0.65rem;
	}

	.crew-showcase-panel__story-item {
		display: grid;
		gap: 0.2rem;
		padding: 0.55rem 0.6rem;
		border-radius: var(--vm-radius-sm);
		background: var(--crew-inset-surface);
		box-shadow: inset 0 0 0 1px var(--crew-inset-border);
		cursor: help;
	}

	.crew-showcase-panel__story-item:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: 2px;
	}

	.crew-showcase-panel__story-title {
		font-size: clamp(0.6875rem, 2vw, 0.8125rem);
		line-height: 1.35;
		letter-spacing: 0.06em;
		color: var(--vm-tobacco-black);
	}

	.crew-showcase-panel__story-body {
		margin: 0;
		font-size: clamp(0.625rem, 1.75vw, 0.8125rem);
		line-height: 1.55;
		letter-spacing: 0.03em;
		color: color-mix(in srgb, var(--vm-tobacco) 88%, var(--vm-tobacco-black));
	}
</style>
