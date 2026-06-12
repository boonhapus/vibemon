<script lang="ts">
	import ElementBadge from '$lib/ui/ElementBadge.svelte';
	import PixelIcon from '$lib/ui/PixelIcon.svelte';

	import BstRadarChart from './BstRadarChart.svelte';
	import EvolutionLinePips from './EvolutionLinePips.svelte';
	import HatchControls from './HatchControls.svelte';
	import ProviderPatchPanel from './ProviderPatchPanel.svelte';
	import MovePill from './MovePill.svelte';
	import PowerPips from './PowerPips.svelte';
	import StatBar from './StatBar.svelte';
	import { candidateDisplayName, type BaseStats, type HatchCandidate } from './hatchApi';
	import { evolutionLineHint } from './evolutionLineCopy';
	import {
		PROVIDER_CATALOG_ORDER,
		providerDisplayLabel,
		providerIcon
	} from './providerLabels';

	type CandidateTab = 'stats' | 'moves' | 'sources';

	const statLines = [
		{ key: 'hp', label: 'HP' },
		{ key: 'attack', label: 'Attack' },
		{ key: 'defense', label: 'Defense' },
		{ key: 'sp_attack', label: 'Sp. Attack' },
		{ key: 'sp_defense', label: 'Sp. Defense' },
		{ key: 'speed', label: 'Speed' }
	] as const satisfies ReadonlyArray<{ key: keyof BaseStats; label: string }>;

	let {
		candidate,
		actionHint = $bindable<'refresh' | 'adopt' | 'release' | null>(null),
		detailHint = $bindable<string | null>(null),
		releaseDisabled = false,
		busy = false,
		showActions = true,
		onRelease,
		onRefresh,
		onAdopt
	}: {
		candidate: HatchCandidate;
		actionHint?: 'refresh' | 'adopt' | 'release' | null;
		detailHint?: string | null;
		releaseDisabled?: boolean;
		busy?: boolean;
		/** Hide the Release / Refresh / Adopt row for read-only contexts (e.g. crew). */
		showActions?: boolean;
		onRelease?: () => void;
		onRefresh?: () => void;
		onAdopt?: () => void;
	} = $props();

	let activeTab = $state<CandidateTab>('stats');

	let peakStat = $derived(
		Math.max(...statLines.map(({ key }) => candidate.base_stats[key]), 1)
	);

	function statPips(value: number): 1 | 2 | 3 {
		const ratio = value / peakStat;
		if (ratio >= 0.84) return 3;
		if (ratio >= 0.5) return 2;
		return 1;
	}

	function statHint(label: string, value: number): string {
		return `${label} ${value}. Blocks show how this stat compares to ${displayName}'s best.`;
	}

	let displayName = $derived(candidateDisplayName(candidate));
	let powerPips = $derived(Math.min(Math.max(candidate.power_pips, 1), 3) as 1 | 2 | 3);
	let activeProviderIds = $derived(new Set(candidate.providers));

	function strengthHint(pips: 1 | 2 | 3): string {
		const context =
			pips === 3
				? 'on the high end for its evolution line'
				: pips === 2
					? 'right around the norm for its evolution line'
					: 'still building toward its line\'s potential';
		return `A measure of its BST relative to its evolution stages -- ${context}.`;
	}
	function moveHint(move: HatchCandidate['moves'][number]): string {
		const parts: string[] = [];
		const flavor = move.flavor_text?.trim();
		if (flavor) parts.push(flavor);
		if (move.combat_hints?.length) {
			parts.push(...move.combat_hints);
		}
		return parts.join(' ') || 'No lore recorded for this move yet.';
	}

	function radarHint(): string {
		return `${displayName}'s base stats (BST: ${candidate.bst}) — the shape shows where its strength leans.`;
	}

	function sourceHint(providerId: string, active: boolean): string {
		const label = providerDisplayLabel(providerId);
		if (!active) return `${label} was not connected for this hatch.`;
		return `${label} helped shape this hatch.`;
	}

	function showHint(text: string) {
		actionHint = null;
		detailHint = text;
	}

	function clearHint(text: string) {
		if (detailHint === text) {
			detailHint = null;
		}
	}

	function selectTab(tab: CandidateTab) {
		activeTab = tab;
		detailHint = null;
	}
</script>

<ProviderPatchPanel title={false} fill ariaLabel="Candidate review" class="hatch-candidate-panel-shell">
	<div class="hatch-candidate-panel">
		<div class="hatch-candidate-panel__header">
			<div class="hatch-candidate-panel__identity">
				<div class="hatch-candidate-panel__title-row">
					<h2 class="hatch-candidate-panel__name">{displayName}</h2>
					<ul class="hatch-candidate-panel__types" role="list">
						{#each candidate.elements as element (element)}
							<li>
								<ElementBadge type={element} />
							</li>
						{/each}
					</ul>
				</div>
			</div>
			<div class="hatch-candidate-panel__ledger">
				<button
					type="button"
					class="hatch-candidate-panel__ledger-hit"
					aria-label="Evolution line"
					onmouseenter={() => showHint(evolutionLineHint(candidate.evolution_line, displayName, candidate.evo_seed))}
					onmouseleave={() => clearHint(evolutionLineHint(candidate.evolution_line, displayName, candidate.evo_seed))}
					onfocus={() => showHint(evolutionLineHint(candidate.evolution_line, displayName, candidate.evo_seed))}
					onblur={() => clearHint(evolutionLineHint(candidate.evolution_line, displayName, candidate.evo_seed))}
				>
					<span class="hatch-candidate-panel__ledger-key">EVO</span>
					<EvolutionLinePips line={candidate.evolution_line} />
				</button>
				<button
					type="button"
					class="hatch-candidate-panel__ledger-hit hatch-candidate-panel__ledger-hit--str"
					aria-label="Strength"
					onmouseenter={() => showHint(strengthHint(powerPips))}
					onmouseleave={() => clearHint(strengthHint(powerPips))}
					onfocus={() => showHint(strengthHint(powerPips))}
					onblur={() => clearHint(strengthHint(powerPips))}
				>
					<span class="hatch-candidate-panel__ledger-key">STR</span>
					<PowerPips compact pips={powerPips} />
				</button>
			</div>
		</div>

		<div class="hatch-candidate-panel__tabs" role="tablist" aria-label="Candidate details">
			<button
				type="button"
				class="hatch-candidate-panel__tab"
				class:hatch-candidate-panel__tab--active={activeTab === 'stats'}
				role="tab"
				aria-selected={activeTab === 'stats'}
				onclick={() => selectTab('stats')}
			>
				Stats
			</button>
			<button
				type="button"
				class="hatch-candidate-panel__tab"
				class:hatch-candidate-panel__tab--active={activeTab === 'moves'}
				role="tab"
				aria-selected={activeTab === 'moves'}
				onclick={() => selectTab('moves')}
			>
				Moves
			</button>
			<button
				type="button"
				class="hatch-candidate-panel__tab"
				class:hatch-candidate-panel__tab--active={activeTab === 'sources'}
				role="tab"
				aria-selected={activeTab === 'sources'}
				onclick={() => selectTab('sources')}
			>
				Sources
			</button>
		</div>

		<div class="hatch-candidate-panel__body">
			{#if activeTab === 'stats'}
				<div class="hatch-candidate-panel__stats" role="tabpanel">
					<button
						type="button"
						class="hatch-candidate-panel__chart"
						aria-label="Base stat radar chart"
						onmouseenter={() => showHint(radarHint())}
						onmouseleave={() => clearHint(radarHint())}
						onfocus={() => showHint(radarHint())}
						onblur={() => clearHint(radarHint())}
					>
						<BstRadarChart stats={candidate.base_stats} size={168} />
					</button>
					<div class="hatch-candidate-panel__stat-list">
						{#each statLines as line (line.key)}
							{@const value = candidate.base_stats[line.key]}
							{@const hint = statHint(line.label, value)}
							<button
								type="button"
								class="hatch-candidate-panel__stat-hit"
								onmouseenter={() => showHint(hint)}
								onmouseleave={() => clearHint(hint)}
								onfocus={() => showHint(hint)}
								onblur={() => clearHint(hint)}
							>
								<StatBar label={line.label} {value} pips={statPips(value)} />
							</button>
						{/each}
					</div>
				</div>
			{:else if activeTab === 'moves'}
				<div class="hatch-candidate-panel__moves" role="tabpanel">
					{#if candidate.moves.length === 0}
						<p class="hatch-candidate-panel__empty">Moves still settling in.</p>
					{:else}
						<div class="hatch-candidate-panel__move-grid">
							{#each candidate.moves as move (move.name)}
								{@const hint = moveHint(move)}
								<button
									type="button"
									class="hatch-candidate-panel__move-hit"
									onmouseenter={() => showHint(hint)}
									onmouseleave={() => clearHint(hint)}
									onfocus={() => showHint(hint)}
									onblur={() => clearHint(hint)}
								>
									<MovePill {move} review />
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{:else}
				<div class="hatch-candidate-panel__sources" role="tabpanel">
					<ul class="hatch-candidate-panel__source-list" role="list">
						{#each PROVIDER_CATALOG_ORDER as providerId, index (providerId)}
							{@const active = activeProviderIds.has(providerId)}
							{@const hint = sourceHint(providerId, active)}
							<li>
								<button
									type="button"
									class="hatch-candidate-panel__source-row"
									class:hatch-candidate-panel__source-row--inactive={!active}
									class:hatch-candidate-panel__source-row--striped={index % 2 === 1}
									onmouseenter={() => showHint(hint)}
									onmouseleave={() => clearHint(hint)}
									onfocus={() => showHint(hint)}
									onblur={() => clearHint(hint)}
								>
									<PixelIcon
										name={providerIcon(providerId)}
										class="hatch-candidate-panel__source-icon"
									/>
									<span class="hatch-candidate-panel__source-label"
										>{providerDisplayLabel(providerId)}</span
									>
									<span class="hatch-candidate-panel__source-lamp" aria-hidden="true"></span>
								</button>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		</div>

		{#if showActions}
			<div class="hatch-candidate-panel__actions">
				<HatchControls
					bind:actionHint
					{releaseDisabled}
					{busy}
					embedded
					{onRelease}
					{onRefresh}
					{onAdopt}
				/>
			</div>
		{/if}
	</div>
</ProviderPatchPanel>

<style>
	:global(.hatch-candidate-panel-shell.provider-patch-panel) {
		--provider-patch-pad: clamp(12px, 2vw, 18px);
		--provider-patch-pad-bottom: 0;
	}

	.hatch-candidate-panel {
		--hatch-pip-block-w: 0.72rem;
		--hatch-pip-block-h: 0.55rem;
		--hatch-pip-gap: 0.28rem;
		--hatch-readout-pip-gap: 0.55rem;
		--hatch-pip-track-width: calc(3 * var(--hatch-pip-block-w) + 2 * var(--hatch-pip-gap));
		--hatch-stats-grid: minmax(0, 1fr) minmax(0, max-content) var(--hatch-pip-track-width);

		display: flex;
		flex-direction: column;
		flex: 1;
		width: 100%;
		min-width: 0;
		min-height: 0;
		height: 100%;
		color: var(--vm-tobacco-black);
		font-family: var(--vm-font-ui);
	}

	.hatch-candidate-panel__header {
		display: grid;
		gap: 0;
		margin-bottom: var(--vm-space-sm);
		flex-shrink: 0;
	}

	.hatch-candidate-panel__identity {
		padding-bottom: 0.55rem;
	}

	.hatch-candidate-panel__title-row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, max-content);
		align-items: center;
		gap: 0.35rem 0.75rem;
	}

	.hatch-candidate-panel__name {
		margin: 0;
		font-size: clamp(0.9375rem, 2.85vw, 1.2rem);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.06em;
		color: var(--vm-tobacco-black);
	}

	.hatch-candidate-panel__types {
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

	.hatch-candidate-panel__ledger {
		display: grid;
		grid-template-columns: var(--hatch-stats-grid);
		align-items: center;
		width: 100%;
		padding-block: 0.55rem 0.2rem;
		border-top: 1px solid color-mix(in srgb, var(--vm-tobacco) 16%, transparent);
	}

	.hatch-candidate-panel__ledger-hit:first-child {
		grid-column: 1;
		grid-row: 1;
		justify-self: start;
	}

	.hatch-candidate-panel__ledger-hit {
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

	.hatch-candidate-panel__ledger-hit--str {
		grid-column: 1 / -1;
		grid-row: 1;
		display: grid;
		grid-template-columns: var(--hatch-stats-grid);
		align-items: center;
		column-gap: 0.28rem;
	}

	.hatch-candidate-panel__ledger-hit--str .hatch-candidate-panel__ledger-key {
		grid-column: 2;
		justify-self: end;
		margin-right: var(--hatch-readout-pip-gap);
	}

	.hatch-candidate-panel__ledger-hit--str :global(.power-pips) {
		grid-column: 3;
		justify-self: end;
	}

	.hatch-candidate-panel__ledger-hit:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: 2px;
	}

	.hatch-candidate-panel__ledger-key {
		font-size: clamp(0.5625rem, 1.6vw, 0.6875rem);
		line-height: 1;
		letter-spacing: 0.08em;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-brass));
	}

	.hatch-candidate-panel__tabs {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.2rem;
		margin-bottom: var(--vm-space-sm);
		padding: 0.18rem;
		border: 2px solid color-mix(in srgb, var(--vm-tobacco) 18%, transparent);
		border-radius: var(--vm-radius-sm);
		background: color-mix(in srgb, var(--vm-tobacco) 8%, var(--vm-panel-command-bg));
		flex-shrink: 0;
	}

	.hatch-candidate-panel__tab {
		margin: 0;
		padding: 0.35rem 0.5rem;
		border: 0;
		border-radius: calc(var(--vm-radius-sm) - 2px);
		background: transparent;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-brass));
		font-family: var(--vm-font-ui);
		font-size: clamp(0.625rem, 1.8vw, 0.75rem);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.06em;
		cursor: pointer;
		-webkit-tap-highlight-color: transparent;
	}

	.hatch-candidate-panel__tab--active {
		background: var(--vm-panel-command-bg);
		color: var(--vm-tobacco-black);
		box-shadow:
			inset 0 0 0 1px color-mix(in srgb, var(--vm-tobacco) 22%, transparent),
			0 1px 0 rgb(42 30 22 / 0.12);
	}

	.hatch-candidate-panel__tab:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: 1px;
	}

	.hatch-candidate-panel__body {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 10rem;
	}

	.hatch-candidate-panel__stats,
	.hatch-candidate-panel__moves,
	.hatch-candidate-panel__sources {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
	}

	.hatch-candidate-panel__stats {
		display: grid;
		grid-template-columns: var(--hatch-stats-grid);
		align-items: center;
		column-gap: clamp(0.65rem, 2vw, 1.1rem);
		flex: 1;
		min-height: 0;
	}

	.hatch-candidate-panel__stat-list {
		display: flex;
		flex-direction: column;
		grid-column: 2 / -1;
		grid-row: 1;
		flex: 1;
		min-height: 0;
		height: 100%;
		min-width: 0;
		gap: 0.58rem;
		padding-block: 0.58rem;
	}

	.hatch-candidate-panel__stat-hit {
		display: flex;
		align-items: center;
		width: 100%;
		flex: 1;
		min-height: 0;
		margin: 0;
		padding: 0;
		border: 0;
		background: transparent;
		color: inherit;
		font: inherit;
		cursor: help;
		-webkit-tap-highlight-color: transparent;
	}

	.hatch-candidate-panel__chart {
		display: flex;
		grid-column: 1;
		grid-row: 1;
		justify-content: center;
		align-items: center;
		align-self: center;
		justify-self: stretch;
		min-width: 0;
		min-height: 0;
		margin: 0;
		padding: 0;
		border: 0;
		background: transparent;
		color: inherit;
		font: inherit;
		cursor: help;
		-webkit-tap-highlight-color: transparent;
	}

	.hatch-candidate-panel__chart :global(.bst-radar) {
		width: clamp(8.5rem, 22vh, 11rem);
		height: auto;
		flex-shrink: 0;
	}

	.hatch-candidate-panel__chart:focus-visible,
	.hatch-candidate-panel__stat-hit:focus-visible,
	.hatch-candidate-panel__move-hit:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: 2px;
	}

	.hatch-candidate-panel__move-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		grid-template-rows: repeat(2, minmax(0, 1fr));
		gap: 0.45rem;
		flex: 1;
		min-height: 0;
	}

	.hatch-candidate-panel__move-hit {
		display: flex;
		width: 100%;
		min-width: 0;
		min-height: 0;
		margin: 0;
		padding: 0;
		border: 0;
		background: transparent;
		color: inherit;
		font: inherit;
		text-align: left;
		cursor: help;
		-webkit-tap-highlight-color: transparent;
	}

	.hatch-candidate-panel__stat-hit :global(.stat-bar) {
		width: 100%;
	}

	.hatch-candidate-panel__move-hit :global(.move-pill) {
		flex: 1;
	}

	.hatch-candidate-panel__source-list {
		display: flex;
		flex-direction: column;
		gap: 0;
		margin: 0;
		padding: 0;
		list-style: none;
		flex: 1;
		min-height: 0;
	}

	.hatch-candidate-panel__source-row {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: 0.4rem;
		width: 100%;
		margin: 0;
		padding: 0.38rem 0.45rem;
		border: 0;
		border-bottom: 1px solid color-mix(in srgb, var(--vm-tobacco) 10%, transparent);
		background: transparent;
		color: inherit;
		font: inherit;
		text-align: left;
		cursor: help;
		-webkit-tap-highlight-color: transparent;
	}

	.hatch-candidate-panel__source-row--striped {
		background: color-mix(in srgb, var(--vm-plum) 7%, var(--vm-panel-command-bg));
	}

	.hatch-candidate-panel__source-row:last-child {
		border-bottom: 0;
	}

	.hatch-candidate-panel__source-row:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: -2px;
	}

	.hatch-candidate-panel__source-row--inactive {
		color: color-mix(in srgb, var(--vm-tobacco) 52%, var(--vm-panel-command-bg));
	}

	.hatch-candidate-panel__source-row--inactive :global(.hatch-candidate-panel__source-icon) {
		color: color-mix(in srgb, var(--vm-tobacco) 38%, var(--vm-panel-command-bg));
	}

	:global(.hatch-candidate-panel__source-icon) {
		width: 14px;
		height: 14px;
		color: color-mix(in srgb, var(--vm-tobacco) 80%, var(--vm-brass));
	}

	.hatch-candidate-panel__source-label {
		font-size: clamp(0.625rem, 1.8vw, 0.75rem);
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.06em;
	}

	.hatch-candidate-panel__source-lamp {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--vm-status-sage);
		box-shadow:
			inset 0 -1px 1px rgb(20 12 8 / 0.35),
			0 0 0 1px color-mix(in srgb, var(--vm-tobacco) 40%, transparent);
	}

	.hatch-candidate-panel__source-row--inactive .hatch-candidate-panel__source-lamp {
		background: color-mix(in srgb, var(--vm-tobacco) 24%, var(--vm-panel-command-bg));
		box-shadow: inset 0 -1px 1px rgb(20 12 8 / 0.25);
	}

	.hatch-candidate-panel__empty {
		margin: auto 0;
		padding: 1rem 0.25rem;
		text-align: center;
		font-size: var(--vm-text-caption);
		line-height: var(--vm-leading-normal);
		color: color-mix(in srgb, var(--vm-tobacco) 68%, var(--vm-brass));
	}

	.hatch-candidate-panel__actions {
		flex-shrink: 0;
		margin-top: auto;
		padding-block: var(--vm-space-sm);
		border-top: 3px solid color-mix(in srgb, var(--vm-tobacco) 16%, transparent);
	}

	.hatch-candidate-panel__actions :global(.hatch-controls) {
		width: 100%;
	}
</style>
