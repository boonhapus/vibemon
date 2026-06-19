<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import { sceneSolarPhase } from '$lib/domains/game/gameSolarContext.svelte';
	import { sceneBackgroundSrc } from '$lib/domains/game/sceneBackgrounds';
	import GameButton from '$lib/ui/GameButton.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import { playGameAudio } from '$lib/ui/gameAudioStore.svelte';
	import SceneFrame from '$lib/ui/SceneFrame.svelte';

	import { fetchTitleMonSprites } from './titleMonApi';
	import TitleGrassMon from './TitleGrassMon.svelte';
	import { TITLE_MON_SLOTS, zipTitleMonSprites } from './titleMonSlots';

	type TitleMenuItem = {
		id: string;
		label: string;
		href?: string;
		disabled?: boolean;
	};

	const MENU_ITEMS: readonly TitleMenuItem[] = [
		{ id: 'learn', label: 'Learn More', disabled: true },
		{ id: 'register', label: 'Register', href: '/register' },
		{ id: 'login', label: 'Login', href: '/login' }
	];

	let selectedIndex = $state(0);
	let grassMons = $state<Array<(typeof TITLE_MON_SLOTS)[number] & { spriteSrc: string }>>([]);
	let solarPhase = $derived(sceneSolarPhase());
	let backgroundSrc = $derived(sceneBackgroundSrc('title', solarPhase));
	let logoLit = $derived(solarPhase === 'night' || solarPhase === 'dusk');

	function enabledMenuIndexes(): number[] {
		return MENU_ITEMS.map((item, index) => (item.disabled ? -1 : index)).filter((index) => index >= 0);
	}

	function selectIndex(next: number) {
		if (next === selectedIndex) return;
		selectedIndex = next;
		playGameAudio('menu-nav');
	}

	function moveSelection(delta: number) {
		const enabled = enabledMenuIndexes();
		if (enabled.length === 0) return;
		const current = enabled.indexOf(selectedIndex);
		const base = current >= 0 ? current : 0;
		const next = enabled[(base + delta + enabled.length) % enabled.length]!;
		selectIndex(next);
	}

	function activateSelected() {
		const item = MENU_ITEMS[selectedIndex];
		if (item.disabled || !item.href) return;
		playGameAudio('confirm');
		void goto(item.href);
	}

	function handleMenuKeydown(event: KeyboardEvent) {
		switch (event.key) {
			case 'ArrowUp':
			case 'ArrowLeft':
				event.preventDefault();
				moveSelection(-1);
				break;
			case 'ArrowDown':
			case 'ArrowRight':
				event.preventDefault();
				moveSelection(1);
				break;
			case 'Enter':
			case ' ':
				event.preventDefault();
				activateSelected();
				break;
		}
	}

	onMount(() => {
		const enabled = enabledMenuIndexes();
		if (enabled.length > 0) selectedIndex = enabled[0]!;

		void fetchTitleMonSprites().then((sprites) => {
			grassMons = zipTitleMonSprites(TITLE_MON_SLOTS, sprites);
		});
	});
</script>

<svelte:window onkeydown={handleMenuKeydown} />

<SceneFrame
	backgroundSrc={backgroundSrc}
	backgroundFadeMs={720}
	backgroundAlt="Golden meadow clearing framed by pine trees"
	showSettingsKnob={false}
	class="title-scene-frame"
>
	<div class="title-scene">
		<h1 class="title-scene__logo" class:title-scene__logo--lit={logoLit}>Vibemon</h1>

		<div class="title-scene__grass-stage">
			{#each grassMons as mon (mon.id)}
				<TitleGrassMon slot={mon} spriteSrc={mon.spriteSrc} />
			{/each}
		</div>

		<div class="title-scene__menu-wrap">
			<nav class="title-scene__menu" aria-label="Title menu">
				<GamePanel tone="dialog" class="title-scene__menu-panel">
					<ul class="title-scene__menu-list" role="menu">
						{#each MENU_ITEMS as item, index (item.id)}
							<li class="title-scene__menu-item">
								<GameButton
									variant="primary"
									selected={selectedIndex === index}
									disabled={item.disabled}
									class="title-scene__menu-button"
									testId={`title-menu-${item.id}`}
									onclick={() => {
										if (item.disabled) return;
										selectedIndex = index;
										if (item.href) {
											playGameAudio('confirm');
											void goto(item.href);
										}
									}}
									onmouseenter={() => {
										if (!item.disabled) selectedIndex = index;
									}}
									onfocus={() => {
										if (!item.disabled) selectedIndex = index;
									}}
								>
									{item.label}
								</GameButton>
							</li>
						{/each}
					</ul>
				</GamePanel>
			</nav>
		</div>
	</div>
</SceneFrame>

<style>
	:global(.title-scene-frame .scene-frame__overlay) {
		display: block;
	}

	.title-scene {
		position: relative;
		min-height: 100dvh;
		box-sizing: border-box;
	}

	.title-scene__logo {
		position: absolute;
		z-index: 1;
		top: 17%;
		left: 50%;
		margin: 0;
		transform: translate(-50%, -50%);
		font-family: var(--vm-font-title);
		font-size: clamp(3.5rem, 14vw, 7.25rem);
		font-weight: 700;
		line-height: 0.92;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--vm-tobacco);
		text-shadow:
			3px 3px 0 var(--vm-panel-command-bg),
			5px 5px 0 color-mix(in srgb, var(--vm-tobacco) 28%, transparent);
	}

	.title-scene__logo--lit {
		color: var(--vm-parchment);
		text-shadow:
			3px 3px 0 var(--vm-tobacco),
			5px 5px 0 color-mix(in srgb, var(--vm-tobacco-black) 45%, transparent);
	}

	.title-scene__grass-stage {
		/* Bounding box for the tall-grass oval in title--day.png — keep TITLE_GRASS_OVAL in sync. */
		position: absolute;
		z-index: 1;
		left: 50%;
		bottom: clamp(12%, 14vh, 18%);
		width: 92vw;
		height: clamp(14rem, 34vh, 30rem);
		transform: translateX(-50%);
	}

	.title-scene__menu-wrap {
		position: absolute;
		z-index: 2;
		left: 50%;
		bottom: clamp(1.25rem, 5vh, 2.5rem);
		width: min(94vw, 38rem);
		transform: translateX(-50%);
	}

	.title-scene__menu {
		width: 100%;
	}

	:global(.title-scene__menu-panel) {
		width: 100%;
	}

	:global(.title-scene__menu-panel .game-panel__content) {
		padding-block: clamp(0.85rem, 2vh, 1.15rem);
		padding-inline: clamp(1rem, 2.8vw, 1.35rem);
	}

	.title-scene__menu-list {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--vm-space-sm);
		margin: 0;
		padding: 0;
		list-style: none;
		align-items: stretch;
	}

	.title-scene__menu-item {
		margin: 0;
		min-width: 0;
	}

	:global(.title-scene__menu-button) {
		display: block;
		width: 100%;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.8125rem, 2.2vw, 0.9375rem);
		font-weight: 600;
		line-height: 1.35;
		letter-spacing: 0.06em;
	}

	:global(.title-scene__menu-button .game-button__face) {
		width: 100%;
		justify-content: center;
		min-height: 52px;
		padding-block: var(--vm-space-sm);
		padding-inline: var(--vm-space-sm);
		text-align: center;
	}

	:global(.title-scene__menu-button .game-button__label) {
		font-weight: inherit;
	}

	:global(.title-scene__menu-button .game-button__cursor) {
		display: none;
	}

	@media (max-width: 36rem) {
		.title-scene__menu-list {
			grid-template-columns: 1fr;
			gap: var(--vm-space-md);
		}

		:global(.title-scene__menu-button .game-button__face) {
			justify-content: flex-start;
			padding-inline: var(--vm-space-lg);
		}
	}
</style>
