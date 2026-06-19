<script lang="ts">
	import DialogBox from '$lib/ui/DialogBox.svelte';
	import ElementBadge from '$lib/ui/ElementBadge.svelte';
	import GameButton from '$lib/ui/GameButton.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import CrewFormationMenu from '$lib/domains/crew/CrewFormationMenu.svelte';
	import PixelIcon from '$lib/ui/PixelIcon.svelte';
	import GuideNavButton from '$lib/domains/trainer/GuideNavButton.svelte';
	import StyleguideSpecimen from '$lib/ui/StyleguideSpecimen.svelte';
	import CabinetGuidePanel from '$lib/ui/CabinetGuidePanel.svelte';
	import { ELEMENT_TYPES, elementTypeColor } from '$lib/ui/elementTypes';
</script>

<svelte:head>
	<title>Styleguide · Vibemon</title>
</svelte:head>

<main class="styleguide">
	<h1 class="styleguide__title">Vibemon Styleguide</h1>

	<section class="styleguide__section styleguide__intro">
		<div class="styleguide__intro-col">
			<h2 class="styleguide__heading">Palette</h2>
			<h3 class="styleguide__subheading">Brand</h3>
			<div class="styleguide__swatches">
				{#each [
					{ name: 'Parchment', token: '--vm-parchment', hex: '#f0e7ce' },
					{ name: 'Tobacco', token: '--vm-tobacco', hex: '#3d2b1f' },
					{ name: 'Burnt Orange', token: '--vm-burnt-orange', hex: '#c0542a' },
					{ name: 'Sage Olive', token: '--vm-sage-olive', hex: '#6e7540' },
					{ name: 'Grape Plum', token: '--vm-plum', hex: '#7c4d8a' },
					{ name: 'Soft Mustard', token: '--vm-mustard', hex: '#c9a23f' }
				] as swatch (swatch.token)}
					<div class="styleguide__swatch">
						<span
							class="styleguide__swatch-chip"
							style:background="var({swatch.token})"
							aria-hidden="true"
						></span>
						<span class="styleguide__swatch-label">{swatch.name}</span>
						<span class="styleguide__swatch-hex">{swatch.hex}</span>
					</div>
				{/each}
			</div>
			<h3 class="styleguide__subheading">Status</h3>
			<div class="styleguide__swatches">
				{#each [
					{ name: 'Sage status', token: '--vm-status-sage', hex: '#6b9b5a' },
					{ name: 'Amber status', token: '--vm-status-amber', hex: '#cc7a22' },
					{ name: 'Brick status', token: '--vm-status-brick', hex: '#a03020' }
				] as swatch (swatch.token)}
					<div class="styleguide__swatch">
						<span
							class="styleguide__swatch-chip"
							style:background="var({swatch.token})"
							aria-hidden="true"
						></span>
						<span class="styleguide__swatch-label">{swatch.name}</span>
						<span class="styleguide__swatch-hex">{swatch.hex}</span>
					</div>
				{/each}
			</div>
			<h2 class="styleguide__heading styleguide__heading--spaced">Spacing tokens</h2>
			<div class="styleguide__spacing">
				{#each [
					{ name: 'xs', value: 'var(--vm-space-xs)' },
					{ name: 'sm', value: 'var(--vm-space-sm)' },
					{ name: 'md', value: 'var(--vm-space-md)' },
					{ name: 'lg', value: 'var(--vm-space-lg)' },
					{ name: 'xl', value: 'var(--vm-space-xl)' }
				] as space (space.name)}
					<div class="styleguide__space-row">
						<span class="styleguide__space-label">{space.name}</span>
						<span class="styleguide__space-bar" style:width={space.value}></span>
						<span class="styleguide__space-value">{space.value}</span>
					</div>
				{/each}
			</div>
		</div>
		<div class="styleguide__intro-col">
			<h2 class="styleguide__heading">Element types</h2>
			<div class="styleguide__swatches styleguide__swatches--types">
				{#each ELEMENT_TYPES as type (type)}
					<div class="styleguide__swatch">
						<span
							class="styleguide__swatch-chip"
							style:background={elementTypeColor(type)}
							aria-hidden="true"
						></span>
						<span class="styleguide__swatch-label">{type}</span>
						<span class="styleguide__swatch-hex">{elementTypeColor(type)}</span>
					</div>
				{/each}
			</div>
		</div>
	</section>

	<StyleguideSpecimen title="Buttons — default">
		{#snippet children()}
			<GameButton variant="primary">Press</GameButton>
			<GameButton variant="secondary">Stars</GameButton>
			<GameButton variant="tertiary">Back</GameButton>
		{/snippet}
	</StyleguideSpecimen>

	<StyleguideSpecimen title="Buttons — forced states">
		{#snippet children()}
			<GameButton variant="primary" forceState="hover">Hover</GameButton>
			<GameButton variant="secondary" forceState="active">Active</GameButton>
			<GameButton variant="secondary" selected forceState="focus">Focus</GameButton>
		{/snippet}
	</StyleguideSpecimen>

	<StyleguideSpecimen title="Buttons — disabled">
		{#snippet children()}
			<GameButton variant="primary" disabled>Press</GameButton>
			<GameButton variant="secondary" disabled>Stars</GameButton>
		{/snippet}
	</StyleguideSpecimen>

	<StyleguideSpecimen title="Crew formation menu">
		{#snippet children()}
			<div class="styleguide__crew-menu">
				<CrewFormationMenu mode="command" />
			</div>
			<div class="styleguide__crew-menu styleguide__crew-menu--position">
				<CrewFormationMenu mode="position" currentSlotIndex={0} />
			</div>
		{/snippet}
	</StyleguideSpecimen>

	<StyleguideSpecimen title="Cabinet bezel — guide panel">
		{#snippet children()}
			<div class="styleguide__cabinet-frame">
				<GuideNavButton />
				<span class="styleguide__cabinet-caption">Guide knob · panel closed</span>
			</div>
			<div class="styleguide__cabinet-frame styleguide__cabinet-frame--expanded">
				<CabinetGuidePanel />
				<span class="styleguide__cabinet-caption">Guide panel · rolled down</span>
			</div>
		{/snippet}
	</StyleguideSpecimen>

	<section class="styleguide__section">
		<h2 class="styleguide__heading">Typography</h2>
		<div class="styleguide__type">
			<p class="styleguide__type-title">Vibemon Battle</p>
			<p class="styleguide__type-heading">FESALI · HEADING VOICE</p>
			<p class="styleguide__type-body">
				The body voice carries dialog, hints, and descriptions — friendly, rounded, and easy on
				the eyes at length.
			</p>
			<p class="styleguide__type-caption">BST 280 · caption voice for metadata</p>
		</div>
	</section>

	<StyleguideSpecimen title="Panels">
		{#snippet children()}
			<GamePanel tone="status">
				<p class="styleguide__panel-text">Status</p>
			</GamePanel>
			<GamePanel tone="command">
				<p class="styleguide__panel-text">Command</p>
			</GamePanel>
		{/snippet}
	</StyleguideSpecimen>

	<StyleguideSpecimen title="Dialog">
		{#snippet children()}
			<DialogBox text="The vibes settle... tobacco on parchment." showCursor={true} typewriter={false} />
		{/snippet}
	</StyleguideSpecimen>

	<section class="styleguide__section">
		<h2 class="styleguide__heading">Pixel icons</h2>
		<div class="styleguide__row styleguide__icons">
			<PixelIcon name="refresh" class="styleguide__icon" />
			<PixelIcon name="heart" class="styleguide__icon" />
			<PixelIcon name="wind" class="styleguide__icon" />
			<PixelIcon name="gear" class="styleguide__icon" />
			<PixelIcon name="note" class="styleguide__icon" />
			<PixelIcon name="star" class="styleguide__icon" />
		</div>
	</section>

	<section class="styleguide__section">
		<h2 class="styleguide__heading">Type badges</h2>
		<div class="styleguide__row styleguide__badges">
			{#each ELEMENT_TYPES as type (type)}
				<ElementBadge {type} />
			{/each}
		</div>
	</section>
</main>

<style>
	.styleguide {
		min-height: 100dvh;
		padding: var(--vm-space-xl);
		display: flex;
		flex-direction: column;
		gap: var(--vm-space-lg);
		background: var(--vm-parchment);
	}

	.styleguide__title {
		margin: 0;
		font-family: var(--vm-font-title);
		font-size: 2rem;
		color: var(--vm-tobacco);
	}

	.styleguide__heading {
		margin: 0 0 var(--vm-space-sm);
		font-family: var(--vm-font-ui);
		font-size: 1rem;
		color: var(--vm-tobacco);
	}

	.styleguide__heading--spaced {
		margin-top: var(--vm-space-lg);
	}

	.styleguide__subheading {
		margin: var(--vm-space-sm) 0 var(--vm-space-xs);
		font-family: var(--vm-font-ui);
		font-size: 0.6875rem;
		font-weight: 500;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-brass));
	}

	.styleguide__section {
		display: flex;
		flex-direction: column;
		gap: var(--vm-space-md);
	}

	.styleguide__intro {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.35fr);
		gap: var(--vm-space-xl);
		align-items: start;
	}

	.styleguide__intro-col {
		display: flex;
		flex-direction: column;
		gap: var(--vm-space-xs);
		min-width: 0;
	}

	@media (max-width: 52rem) {
		.styleguide__intro {
			grid-template-columns: 1fr;
		}
	}

	.styleguide__row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--vm-space-md);
	}

	.styleguide__swatches {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(7rem, 1fr));
		gap: var(--vm-space-sm);
	}

	.styleguide__swatches--types {
		grid-template-columns: repeat(auto-fill, minmax(5.5rem, 1fr));
	}

	.styleguide__badges {
		gap: var(--vm-space-sm);
	}

	.styleguide__swatch {
		display: grid;
		gap: 0.2rem;
	}

	.styleguide__swatch-chip {
		display: block;
		height: 2.25rem;
		border: 2px solid color-mix(in srgb, var(--vm-tobacco) 22%, transparent);
		border-radius: var(--vm-radius-sm);
	}

	.styleguide__swatch-label {
		font-family: var(--vm-font-ui);
		font-size: 0.5625rem;
		line-height: 1.2;
		color: var(--vm-tobacco);
	}

	.styleguide__swatch-hex {
		font-family: var(--vm-font-body);
		font-size: 0.625rem;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-brass));
	}

	.styleguide__spacing {
		display: grid;
		gap: var(--vm-space-sm);
	}

	.styleguide__space-row {
		display: grid;
		grid-template-columns: 2rem 1fr auto;
		align-items: center;
		gap: var(--vm-space-sm);
	}

	.styleguide__space-label {
		font-family: var(--vm-font-ui);
		font-size: 0.5625rem;
		color: var(--vm-tobacco);
	}

	.styleguide__space-bar {
		height: 0.55rem;
		background: var(--vm-burnt-orange);
		border-radius: 1px;
	}

	.styleguide__space-value {
		font-family: var(--vm-font-body);
		font-size: 0.625rem;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-brass));
	}

	.styleguide__icons {
		color: var(--vm-tobacco);
	}

	:global(.styleguide__icon) {
		width: 48px;
		height: 48px;
	}

	.styleguide__type {
		display: grid;
		gap: var(--vm-space-xs);
		max-width: 36rem;
		color: var(--vm-tobacco);
	}

	.styleguide__type-title {
		margin: 0;
		font-family: var(--vm-font-title);
		font-size: var(--vm-text-title);
		line-height: var(--vm-leading-tight);
	}

	.styleguide__type-heading {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: var(--vm-text-heading);
		line-height: var(--vm-leading-tight);
	}

	.styleguide__type-body {
		margin: var(--vm-space-sm) 0 0;
		font-family: var(--vm-font-body);
		font-weight: 500;
		font-size: var(--vm-text-body);
		line-height: var(--vm-leading-body);
	}

	.styleguide__type-caption {
		margin: 0;
		font-family: var(--vm-font-body);
		font-weight: 500;
		font-size: var(--vm-text-caption);
		line-height: var(--vm-leading-tight);
		color: color-mix(in srgb, var(--vm-tobacco) 78%, var(--vm-brass));
	}

	.styleguide__panel-text {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: 0.8125rem;
		line-height: 1.6;
	}

	.styleguide__crew-menu {
		width: min(100%, 12rem);
		height: var(--vm-hud-dialog-slot-height);
	}

	.styleguide__crew-menu--position {
		width: min(100%, 14rem);
	}

	.styleguide__cabinet-frame {
		position: relative;
		width: min(100%, 20rem);
		min-height: 5.5rem;
		padding-top: var(--vm-bezel-w);
		border: var(--vm-bezel-w) solid transparent;
		border-top-width: var(--vm-bezel-top-current, var(--vm-bezel-w));
		border-image: linear-gradient(180deg, #4a3428, #3d2b1f 55%, #2f2117) 1;
		background:
			linear-gradient(to bottom, #c4a882 0%, #c4a882 52%, #6b7a2a 79%, #6b7a2a 100%) padding-box;
		box-shadow: inset 0 0 0 2px rgb(42 30 22 / 0.45);
		--vm-bezel-top-current: var(--vm-bezel-w);
	}

	.styleguide__cabinet-frame :global(.guide-nav) {
		position: absolute;
		left: 0.35rem;
		bottom: 0.35rem;
	}

	.styleguide__cabinet-frame--expanded {
		--vm-bezel-top-current: var(--vm-bezel-guide-h);
		border-top-width: var(--vm-bezel-guide-h);
		min-height: calc(5.5rem + var(--vm-bezel-guide-h) - var(--vm-bezel-w));
	}

	.styleguide__cabinet-frame--expanded :global(.cabinet-guide-panel) {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: var(--vm-bezel-guide-h);
	}

	.styleguide__cabinet-frame--expanded :global(.cabinet-guide-panel__surface) {
		transform: translateY(0);
	}

	.styleguide__cabinet-caption {
		position: absolute;
		left: 50%;
		bottom: var(--vm-space-sm);
		transform: translateX(-50%);
		font-family: var(--vm-font-body);
		font-size: 0.625rem;
		color: var(--vm-tobacco);
		opacity: 0.72;
		white-space: nowrap;
	}
</style>
