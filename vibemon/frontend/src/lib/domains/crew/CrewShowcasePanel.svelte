<script lang="ts">
	import HatchCandidatePanel from '$lib/domains/trainer/HatchCandidatePanel.svelte';
	import { candidateDisplayName, type HatchCandidate } from '$lib/domains/trainer/hatchApi';
	import { evolutionLineHint } from '$lib/domains/trainer/evolutionLineCopy';
	import ProviderPatchPanel from '$lib/domains/trainer/ProviderPatchPanel.svelte';
	import ElementBadge from '$lib/ui/ElementBadge.svelte';
	import SegmentedHpBar from '$lib/ui/SegmentedHpBar.svelte';
	import XpProgressBar from '$lib/ui/XpProgressBar.svelte';

	import EvolutionLinePips from '$lib/domains/trainer/EvolutionLinePips.svelte';
	import PowerPips from '$lib/domains/trainer/PowerPips.svelte';

	import { buildCrewStoryEntries } from './crewTimeline';

	type ShowcaseTab = 'stats' | 'moves' | 'sources' | 'story';

	let {
		candidate,
		level,
		currentHp,
		maxHp,
		xp,
		xpToNext,
		xpBarRatio,
		onDetailHintChange,
		activeTab = $bindable<ShowcaseTab>('stats')
	}: {
		candidate: HatchCandidate;
		level: number;
		currentHp: number;
		maxHp: number;
		xp: number;
		xpToNext: number;
		xpBarRatio: number;
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
				? 'sits high'
				: pips === 2
					? 'is about average'
					: 'is still climbing';
		return `Its BST ${context} for its evolution line.`;
	}

	function runtimeHpHint(): string {
		return `${displayName} has ${currentHp} HP at level ${level}.`;
	}

	function runtimeXpHint(): string {
		if (xpToNext <= 0) {
			return `${displayName} is at max level with ${xp} total XP.`;
		}
		return `${displayName} has ${xpToNext} XP to go before level ${level + 1}.`;
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
			<div class="crew-showcase-panel__name-row">
				<h2 class="crew-showcase-panel__name">{displayName}</h2>
				<span class="crew-showcase-panel__level">Lv {level}</span>
			</div>
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
					<div class="crew-showcase-panel__runtime">
						<div
							class="crew-showcase-panel__runtime-row"
							role="button"
							tabindex="0"
							onmouseenter={() => showHint(runtimeHpHint())}
							onmouseleave={() => clearHint(runtimeHpHint())}
						>
							<SegmentedHpBar current={currentHp} max={maxHp} />
						</div>
						<div
							class="crew-showcase-panel__runtime-row crew-showcase-panel__runtime-row--xp"
							role="button"
							tabindex="0"
							onmouseenter={() => showHint(runtimeXpHint())}
							onmouseleave={() => clearHint(runtimeXpHint())}
						>
							<XpProgressBar ratio={xpBarRatio} value={`${Math.round(xpBarRatio * 100)}%`} />
						</div>
					</div>
				{/if}

				<div class="crew-showcase-panel__tab-panel">
					{#if activeTab === 'story'}
						<div class="crew-showcase-panel__story" role="tabpanel">
							<div class="crew-showcase-panel__story-list" role="list">
							{#each storyEntries as entry (entry.id)}
								{@const hint = storyHint(entry.title, entry.body)}
								<div
									class="crew-showcase-panel__story-item"
									role="button"
									tabindex="0"
									onmouseenter={() => showHint(hint)}
									onmouseleave={() => clearHint(hint)}
									onfocus={() => showHint(hint)}
									onblur={() => clearHint(hint)}
								>
									<span class="crew-showcase-panel__story-title">{entry.title}</span>
									<p class="crew-showcase-panel__story-body">{entry.body}</p>
								</div>
							{/each}
							</div>
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
		--provider-patch-pad: clamp(10px, 1.6vh, var(--vm-space-md));
		width: 100%;
		min-width: 0;
		height: 100%;
	}

	:global(.crew-showcase-panel-shell.provider-patch-panel .provider-patch-panel__body) {
		background-color: var(--vm-cabinet-guide-surface);
		background-image: none;
		/* Recessed seat — the plate is set into the cabinet wood, not floating over the scene. */
		box-shadow:
			inset 0 0 0 1px rgb(42 30 22 / 0.08),
			inset 0 3px 8px rgb(42 30 22 / 0.12);
	}

	/* Rails inherit the viewport-anchored cabinet grain from ProviderPatchPanel so
	   the plate's wood lip matches the surrounding bezel (no flat-tobacco patch). */

	.crew-showcase-panel {
		--crew-inset-surface: var(--vm-crew-readout-inset-surface);
		--crew-inset-border: var(--vm-crew-readout-inset-border);
		--crew-subtitle-color: var(--vm-crew-readout-subtitle-color);
		--crew-text-muted: var(--vm-crew-readout-muted-color);
		--crew-readout-fill: var(--vm-crew-readout-fill);
		--hatch-pip-block-w: 0.8rem;
		--hatch-pip-block-h: 0.6rem;
		--hatch-pip-gap: 0.28rem;
		--hatch-readout-pip-gap: 0.55rem;
		--hatch-pip-track-width: calc(3 * var(--hatch-pip-block-w) + 2 * var(--hatch-pip-gap));
		--hatch-stats-grid: minmax(0, 1.38fr) minmax(0, max-content) var(--hatch-pip-track-width);

		display: flex;
		flex-direction: column;
		gap: var(--vm-space-sm);
		flex: 1;
		width: 100%;
		min-width: 0;
		min-height: 0;
		height: 100%;
		overflow: hidden;
		color: var(--vm-tobacco-black);
		font-family: var(--vm-font-body);
	}

	.crew-showcase-panel__identity {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, max-content);
		align-items: end;
		gap: var(--vm-space-xs) var(--vm-space-sm);
		flex-shrink: 0;
	}

	.crew-showcase-panel__name-row {
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
		min-width: 0;
	}

	.crew-showcase-panel__name {
		margin: 0;
		font-family: var(--vm-font-body);
		font-size: var(--vm-crew-readout-name);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.01em;
		font-weight: 600;
		color: var(--vm-tobacco-black);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		min-width: 0;
	}

	/* Level sits with the name as identity (mirrors the battle HUD header). */
	.crew-showcase-panel__level {
		flex-shrink: 0;
		font-family: var(--vm-font-ui);
		font-size: var(--vm-crew-readout-subtitle);
		line-height: 1;
		letter-spacing: 0.05em;
		color: color-mix(in srgb, var(--vm-tobacco) 64%, transparent);
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

	/* Span only the STR key + pips, so the hover hit area is the readout itself
	   (not the whole empty row to the left). */
	.crew-showcase-panel__ledger-hit--str {
		grid-column: 2 / -1;
		grid-row: 1;
		display: inline-flex;
		align-items: center;
		justify-self: end;
		gap: var(--hatch-readout-pip-gap);
	}

	.crew-showcase-panel__ledger-hit :global(.power-pips__block--filled) {
		background: var(--crew-readout-fill);
	}

	.crew-showcase-panel__ledger-hit:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: 2px;
	}

	.crew-showcase-panel__ledger-key {
		font-family: var(--vm-font-ui);
		font-size: var(--vm-crew-readout-subtitle);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		font-weight: 400;
		color: var(--crew-subtitle-color);
	}

	/* Engraved guide selector — printed index tabs on the plate, not a raised button bar. */
	.crew-showcase-panel__tabs {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 0;
		padding: 0;
		border: 0;
		border-bottom: 1px solid color-mix(in srgb, var(--vm-tobacco) 22%, transparent);
		border-radius: 0;
		background: transparent;
		flex-shrink: 0;
	}

	.crew-showcase-panel__tab {
		margin: 0 0 -1px;
		padding: var(--vm-space-sm) var(--vm-space-xs);
		min-height: 2.75rem;
		border: 0;
		border-bottom: 2px solid transparent;
		border-radius: 0;
		background: transparent;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.625rem, 1.55vw, 0.75rem);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.04em;
		text-transform: uppercase;
		font-weight: 400;
		color: var(--crew-text-muted);
		cursor: pointer;
		-webkit-tap-highlight-color: transparent;
	}

	/* Active = ink-darkened label + engraved baseline rule; no raised tile, no size jump. */
	.crew-showcase-panel__tab--active {
		color: var(--vm-tobacco-black);
		border-bottom-color: var(--vm-burnt-orange);
		text-shadow: 0 1px 0 rgb(240 231 206 / 0.4);
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

	/* Printed readout — laid flush on the plate and separated by a hairline rule,
	   rather than a floating inset card (which read as a battle-HUD sub-plate). */
	.crew-showcase-panel__runtime {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		width: 100%;
		padding: 0 0 0.55rem;
		border-bottom: 1px solid color-mix(in srgb, var(--vm-tobacco) 14%, transparent);
		flex-shrink: 0;
	}

	.crew-showcase-panel__runtime-row {
		display: block;
		width: 100%;
		min-width: 0;
	}

	/* HP blocks and the XP track share one label/track/value column system so
	   the two bars are the same width and line up on both edges. */
	.crew-showcase-panel__runtime :global(.segmented-hp),
	.crew-showcase-panel__runtime :global(.xp-progress) {
		grid-template-columns: 1.85rem minmax(0, 1fr) 5.6rem;
		column-gap: 0.5rem;
		align-items: center;
	}

	.crew-showcase-panel__runtime-row :global(.segmented-hp__label) {
		font-size: var(--vm-crew-readout-subtitle);
		color: var(--crew-subtitle-color);
	}

	/* HP "13/13" and XP "42%" use the UI voice (clearer numerals than the body
	   font) and are right-aligned in the shared value column so they line up. */
	.crew-showcase-panel__runtime-row :global(.segmented-hp__values),
	.crew-showcase-panel__runtime-row :global(.xp-progress__value) {
		font-family: var(--vm-font-ui);
		font-size: clamp(0.625rem, 1.6vw, 0.75rem);
		font-weight: 400;
		color: var(--vm-tobacco-black);
		font-variant-numeric: tabular-nums;
		text-align: right;
	}

	.crew-showcase-panel__runtime-row :global(.xp-progress__value) {
		color: var(--crew-subtitle-color);
	}

	.crew-showcase-panel__tab-panel {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	/* Body voice + readout colors now live in the shared HatchCandidatePanel /
	   StatBar / MovePill / BstRadarChart defaults (all driven by the
	   --vm-crew-readout-* tokens), so the standalone hatch panel and this
	   embedded one render identically. Only crew-specific layout and the
	   crew-only chrome (HP/XP, story) stay here. */
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
		gap: var(--vm-space-sm);
	}

	.crew-showcase-panel__story-item {
		display: grid;
		gap: var(--vm-space-xs);
		padding: var(--vm-space-sm);
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
		font-family: var(--vm-font-ui);
		font-size: var(--vm-crew-readout-subtitle);
		font-weight: 400;
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.05em;
		text-transform: uppercase;
		color: var(--crew-subtitle-color);
	}

	/* Story prose in the UI voice (Press Start 2P) — same legible numerals and
	   letters as the dialog box, rather than the softer body font. */
	.crew-showcase-panel__story-body {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.6875rem, 1.7vw, 0.8125rem);
		font-weight: 400;
		line-height: 1.7;
		letter-spacing: 0;
		color: var(--vm-tobacco-black);
	}
</style>
