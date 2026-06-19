<script lang="ts">
	import { tick } from 'svelte';

	import GamePanel from '$lib/ui/GamePanel.svelte';
	import { showGameToast } from '$lib/ui/toastStore.svelte';

	import { BATTLE_COMMANDS, type CommandId } from './commandMenu';

	let {
		selected = 0,
		onSelect,
		onConfirm
	}: {
		selected?: number;
		onSelect?: (index: number) => void;
		onConfirm?: (command: CommandId) => void;
	} = $props();

	let gridEl = $state<HTMLDivElement | undefined>();

	function activate(index: number) {
		const command = BATTLE_COMMANDS[index];
		if (!command) return;
		if (command.disabled) {
			if (command.disabledToast) showGameToast(command.disabledToast, 'amber');
			return;
		}
		onSelect?.(index);
		onConfirm?.(command.id);
	}

	function focusSelectedCell(index: number) {
		void tick().then(() => {
			gridEl?.querySelectorAll<HTMLButtonElement>('.command-menu__cell')[index]?.focus({
				preventScroll: true
			});
		});
	}

	$effect(() => {
		focusSelectedCell(selected);
	});
</script>

<GamePanel tone="command" class="command-menu">
	<div bind:this={gridEl} class="command-menu__grid" role="menu" aria-label="Battle commands">
		{#each BATTLE_COMMANDS as command, index (command.id)}
			<button
				type="button"
				class={[
					'command-menu__cell',
					selected === index && 'command-menu__cell--selected',
					command.disabled && 'command-menu__cell--disabled'
				]
					.filter(Boolean)
					.join(' ')}
				disabled={false}
				aria-disabled={command.disabled || undefined}
				aria-current={selected === index ? 'true' : undefined}
				onclick={() => activate(index)}
			>
				<span class="command-menu__content">
					{#if selected === index}
						<span class="command-menu__cursor" aria-hidden="true">▶</span>
					{/if}
					<span class="command-menu__label">{command.label}</span>
				</span>
			</button>
		{/each}
	</div>
</GamePanel>

<style>
	:global(.command-menu.game-panel) {
		display: flex;
		flex-direction: column;
		width: 100%;
		height: 100%;
		min-height: 0;
	}

	:global(.command-menu .game-panel__frame) {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}

	:global(.command-menu .game-panel__content) {
		box-sizing: border-box;
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		padding: clamp(0.35rem, 1vw, 0.55rem);
	}

	.command-menu__grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		grid-template-rows: repeat(2, minmax(0, 1fr));
		width: 100%;
		height: 100%;
	}

	.command-menu__cell {
		display: grid;
		place-items: center;
		width: 100%;
		height: 100%;
		min-width: 0;
		min-height: 0;
		margin: 0;
		padding: 0;
		border: 0;
		background: transparent;
		color: var(--vm-tobacco-black);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.6875rem, 2vw, 0.875rem);
		line-height: 1;
		letter-spacing: 0.06em;
		cursor: pointer;
	}

	.command-menu__content {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.25rem;
		line-height: 1;
	}

	.command-menu__cell:nth-child(odd) {
		border-right: 1px dotted color-mix(in srgb, var(--vm-tobacco) 45%, transparent);
	}

	.command-menu__cell:nth-child(-n + 2) {
		border-bottom: 1px dotted color-mix(in srgb, var(--vm-tobacco) 45%, transparent);
	}

	.command-menu__cell--selected {
		color: var(--vm-burnt-orange);
	}

	.command-menu__cell:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: -2px;
	}

	.command-menu__cell--disabled {
		opacity: 0.42;
		cursor: not-allowed;
	}

	.command-menu__cursor {
		display: block;
		flex: 0 0 auto;
		color: var(--vm-mustard);
		font-size: 0.75em;
		line-height: 1;
		text-box-trim: trim-both;
		text-box-edge: cap alphabetic;
	}

	.command-menu__label {
		display: block;
		line-height: 1;
		text-align: center;
		text-box-trim: trim-both;
		text-box-edge: cap alphabetic;
	}
</style>
