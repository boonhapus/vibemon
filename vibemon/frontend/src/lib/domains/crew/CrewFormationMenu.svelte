<script lang="ts">
	import GamePanel from '$lib/ui/GamePanel.svelte';
	import {
		CREW_FORMATION_COMMANDS,
		CREW_POSITION_SLOTS,
		type CrewCommandId
	} from './crewFormationMenu';

	let {
		mode = 'command',
		selected = 0,
		contextHeld = false,
		swapDisabled = false,
		positionDisabled = false,
		currentSlotIndex = null,
		onSelect,
		onCommand,
		onSwapBlocked,
		onPosition
	}: {
		mode?: 'command' | 'position';
		selected?: number;
		contextHeld?: boolean;
		swapDisabled?: boolean;
		positionDisabled?: boolean;
		currentSlotIndex?: number | null;
		onSelect?: (index: number) => void;
		onCommand?: (command: CrewCommandId) => void;
		onSwapBlocked?: () => void;
		onPosition?: (slotIndex: number) => void;
	} = $props();

	function commandDisabled(id: CrewCommandId): boolean {		return id === 'swap' && swapDisabled;
	}

	function activateCommand(index: number) {
		const command = CREW_FORMATION_COMMANDS[index];
		if (!command) return;
		if (command.id === 'swap' && swapDisabled) {
			onSwapBlocked?.();
			return;
		}
		onSelect?.(index);
		onCommand?.(command.id);
	}

	function activatePosition(slotIndex: number) {
		if (positionDisabled) return;
		onSelect?.(slotIndex);
		onPosition?.(slotIndex);
	}
	function commandLabelParts(command: (typeof CREW_FORMATION_COMMANDS)[number]): {
		hotkey: string | null;
		rest: string;
	} {
		if (!command.hotkey) return { hotkey: null, rest: command.label };
		return { hotkey: command.hotkey, rest: command.label.slice(command.hotkey.length) };
	}
</script>
<GamePanel tone="command" class="crew-formation-menu">
	{#if mode === 'command'}
		<div
			class="crew-formation-menu__grid crew-formation-menu__grid--command"			role="menu"
			aria-label="Crew formation commands"
		>
			{#each CREW_FORMATION_COMMANDS as command, index (command.id)}
				{@const disabled = commandDisabled(command.id)}
				{@const labelParts = commandLabelParts(command)}
				<button
					type="button"
					class={[
						'crew-formation-menu__cell',
						selected === index && 'crew-formation-menu__cell--selected',
						selected === index && contextHeld && 'crew-formation-menu__cell--deck-read',
						disabled && 'crew-formation-menu__cell--disabled'
					]
						.filter(Boolean)
						.join(' ')}
					aria-disabled={disabled || undefined}
					aria-current={selected === index ? 'true' : undefined}
					onclick={() => activateCommand(index)}
				>
					<span class="crew-formation-menu__content">
						{#if selected === index}
							<span class="crew-formation-menu__cursor" aria-hidden="true">▶</span>
						{/if}
						<span class="crew-formation-menu__label">
							{#if labelParts.hotkey}
								<span class="crew-formation-menu__hotkey">{labelParts.hotkey}</span>{labelParts.rest}
							{:else}
								{labelParts.rest}
							{/if}
						</span>
					</span>
				</button>
			{/each}
		</div>
	{:else}
		<div
			class="crew-formation-menu__grid crew-formation-menu__grid--position"			role="menu"
			aria-label="Crew position"
		>
			{#each CREW_POSITION_SLOTS as slot, slotIndex (slot.label)}
				<button
					type="button"
					class={[
						'crew-formation-menu__cell',
						selected === slotIndex && 'crew-formation-menu__cell--selected',
						selected === slotIndex && contextHeld && 'crew-formation-menu__cell--deck-read',
						currentSlotIndex === slotIndex && 'crew-formation-menu__cell--current',
						positionDisabled && 'crew-formation-menu__cell--disabled'
					]
						.filter(Boolean)
						.join(' ')}
					disabled={positionDisabled}
					aria-label={slotIndex === 0 ? 'Set as lead' : `Move to position ${slot.label}`}
					aria-current={selected === slotIndex ? 'true' : undefined}
					onclick={() => activatePosition(slotIndex)}
				>
					<span class="crew-formation-menu__content">
						{#if selected === slotIndex}
							<span class="crew-formation-menu__cursor" aria-hidden="true">▶</span>
						{/if}
						<span class="crew-formation-menu__label crew-formation-menu__label--hotkey-first">{slot.label}</span>
					</span>
				</button>
			{/each}
		</div>
	{/if}
</GamePanel>

<style>
	:global(.crew-formation-menu.game-panel) {
		display: flex;
		flex-direction: column;
		width: 100%;
		height: 100%;
		min-height: 0;
		box-shadow: none;
	}

	:global(.crew-formation-menu .game-panel__frame) {
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		box-shadow: none;
	}

	:global(.crew-formation-menu .game-panel__content) {
		box-sizing: border-box;
		flex: 1 1 auto;
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		padding: clamp(0.35rem, 1vw, 0.55rem);
	}

	.crew-formation-menu__grid {
		display: grid;
		width: 100%;
		height: 100%;
	}

	.crew-formation-menu__grid--command {
		grid-template-columns: repeat(2, minmax(0, 1fr));
		grid-template-rows: repeat(2, minmax(0, 1fr));
	}

	.crew-formation-menu__grid--position {
		grid-template-columns: repeat(3, minmax(0, 1fr));
		grid-template-rows: repeat(2, minmax(0, 1fr));
	}

	.crew-formation-menu__cell {
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

	.crew-formation-menu__content {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.15rem;
		max-width: 100%;
		line-height: 1;
	}

	.crew-formation-menu__grid--position .crew-formation-menu__cell {
		overflow: visible;
		padding-inline: 0.1rem;
	}

	.crew-formation-menu__grid--command .crew-formation-menu__cell:nth-child(odd) {
		border-right: 1px dotted color-mix(in srgb, var(--vm-tobacco) 45%, transparent);
	}

	.crew-formation-menu__grid--command .crew-formation-menu__cell:nth-child(-n + 2) {
		border-bottom: 1px dotted color-mix(in srgb, var(--vm-tobacco) 45%, transparent);
	}

	.crew-formation-menu__grid--position .crew-formation-menu__cell:nth-child(3n + 1),
	.crew-formation-menu__grid--position .crew-formation-menu__cell:nth-child(3n + 2) {
		border-right: 1px dotted color-mix(in srgb, var(--vm-tobacco) 45%, transparent);
	}

	.crew-formation-menu__grid--position .crew-formation-menu__cell:nth-child(-n + 3) {
		border-bottom: 1px dotted color-mix(in srgb, var(--vm-tobacco) 45%, transparent);
	}

	.crew-formation-menu__cell--selected {
		color: var(--vm-burnt-orange);
	}

	.crew-formation-menu__cell--deck-read {
		animation: crew-menu-read-reveal calc(var(--anim-ui-reveal-steps) * 16ms)
			steps(var(--anim-ui-reveal-steps));
	}

	@keyframes crew-menu-read-reveal {
		from {
			opacity: 0.25;
		}
		to {
			opacity: 1;
		}
	}

	.crew-formation-menu__cell--current {
		background-color: color-mix(in srgb, var(--vm-mustard) 18%, transparent);
	}

	.crew-formation-menu__cell:focus,
	.crew-formation-menu__cell:focus-visible {
		outline: none;
	}
	.crew-formation-menu__cell--disabled {
		opacity: 0.42;
		cursor: not-allowed;
	}

	.crew-formation-menu__cursor {
		display: block;
		flex: 0 0 auto;
		color: var(--vm-mustard);
		font-size: 0.75em;
		line-height: 1;
		text-box-trim: trim-both;
		text-box-edge: cap alphabetic;
	}

	.crew-formation-menu__label {
		display: block;
		line-height: 1;
		text-align: center;
		white-space: nowrap;
	}

	.crew-formation-menu__label--hotkey-first::first-letter {
		color: var(--vm-burnt-orange);
	}

	.crew-formation-menu__cell--selected .crew-formation-menu__label--hotkey-first::first-letter {
		color: inherit;
	}

	.crew-formation-menu__hotkey {
		color: var(--vm-burnt-orange);
	}

	.crew-formation-menu__cell--selected .crew-formation-menu__hotkey {
		color: inherit;
	}
</style>
