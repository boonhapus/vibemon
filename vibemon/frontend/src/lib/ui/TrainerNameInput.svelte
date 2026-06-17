<script lang="ts">
	import { tick } from 'svelte';

	import GamePanel from './GamePanel.svelte';

	const DEFAULT_MAX = 16;

	let {
		username = $bindable(''),
		maxLength = DEFAULT_MAX,
		label = 'YOUR USERNAME?',
		disabled = false,
		autofocus = false,
		onSubmit,
		testId,
		class: className = ''
	}: {
		username?: string;
		maxLength?: number;
		label?: string;
		disabled?: boolean;
		autofocus?: boolean;
		onSubmit?: () => void;
		testId?: string;
		class?: string;
	} = $props();

	let inputEl = $state<HTMLInputElement | null>(null);
	let focused = $state(false);
	let focusFromPointer = $state(false);
	let caretIndex = $state(0);

	let slots = $derived(Array.from({ length: maxLength }, (_, index) => username[index] ?? ''));

	function syncCaret() {
		const el = inputEl;
		if (!el) return;
		caretIndex = Math.min(el.selectionStart ?? 0, maxLength);
	}

	function placeCaretAtEnd() {
		const el = inputEl;
		if (!el) return;
		const pos = el.value.length;
		el.setSelectionRange(pos, pos);
		syncCaret();
	}

	function isFullSelection(el: HTMLInputElement) {
		return el.selectionStart === 0 && el.selectionEnd === el.value.length && el.value.length > 0;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			if (onSubmit) {
				onSubmit();
			} else {
				inputEl?.blur();
			}
			return;
		}

		const el = inputEl;
		if (!el || event.key.length !== 1 || event.ctrlKey || event.metaKey || event.altKey) return;

		if (isFullSelection(el)) {
			placeCaretAtEnd();
		}
	}

	function handlePointerDown() {
		focusFromPointer = true;
	}

	function handleFocus() {
		focused = true;
		if (!focusFromPointer) {
			placeCaretAtEnd();
			requestAnimationFrame(() => {
				placeCaretAtEnd();
				syncCaret();
			});
		} else {
			syncCaret();
		}
		focusFromPointer = false;
	}

	let panelClass = $derived(['trainer-name-input', className].filter(Boolean).join(' '));

	$effect(() => {
		if (!autofocus || disabled || !inputEl) return;
		void tick().then(() => inputEl?.focus());
	});
</script>

<GamePanel tone="command" class={panelClass}>
	<div class="trainer-name-input__shell">
		<p class="trainer-name-input__label">{label}</p>

		<div
			class="trainer-name-input__field"
			class:trainer-name-input__field--focused={focused}
			aria-hidden="true"
		>
			<span class="trainer-name-input__cursor" aria-hidden="true">▶</span>
			<span class="trainer-name-input__slots" aria-hidden="true">
				{#each slots as char, index (index)}
					<span
						class="trainer-name-input__slot"
						class:trainer-name-input__slot--active={focused && caretIndex === index}
					>
						<span class="trainer-name-input__char">{char}</span>
						<span class="trainer-name-input__underscore">_</span>
					</span>
				{/each}
			</span>
		</div>

		<input
			bind:this={inputEl}
			class="trainer-name-input__native"
			data-testid={testId}
			type="text"
			inputmode="text"
			autocomplete="nickname"
			spellcheck="false"
			aria-label="Trainer name"
			maxlength={maxLength}
			{disabled}
			bind:value={username}
			onkeydown={handleKeydown}
			onkeyup={syncCaret}
			onclick={syncCaret}
			onselect={syncCaret}
			oninput={syncCaret}
			onpointerdown={handlePointerDown}
			onfocus={handleFocus}
			onblur={() => (focused = false)}
		/>
	</div>
</GamePanel>

<style>
	:global(.trainer-name-input) {
		width: var(--vm-hud-name-width);
	}

	.trainer-name-input__shell {
		position: relative;
		display: grid;
		gap: clamp(0.5rem, 1.6vw, 0.75rem);
	}

	.trainer-name-input__field,
	.trainer-name-input__native {
		grid-row: 2;
		grid-column: 1;
	}

	.trainer-name-input__label {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: var(--vm-hud-font-name-label);
		line-height: 1.5;
		letter-spacing: 0.04em;
		color: var(--vm-tobacco-black);
	}

	.trainer-name-input__field {
		display: flex;
		align-items: center;
		gap: clamp(0.35rem, 1vw, 0.5rem);
		width: 100%;
		margin: 0;
		padding: 0.15rem 0.1rem 0.15rem 0;
		border: 0;
		background: transparent;
		cursor: text;
		text-align: left;
		pointer-events: none;
	}

	.trainer-name-input__field:has(+ .trainer-name-input__native:disabled) {
		cursor: not-allowed;
		opacity: 0.65;
	}

	.trainer-name-input__field--focused .trainer-name-input__cursor {
		animation: vm-cursor-blink 900ms steps(2, end) infinite;
	}

	.trainer-name-input__cursor {
		flex: 0 0 auto;
		font-family: var(--vm-font-ui);
		font-size: var(--vm-hud-font-name-slot);
		line-height: 1;
		color: var(--vm-tobacco-black);
	}

	.trainer-name-input__slots {
		display: flex;
		flex: 1;
		flex-wrap: nowrap;
		gap: 0;
		min-width: 0;
		justify-content: space-between;
	}

	.trainer-name-input__slot {
		position: relative;
		display: inline-grid;
		place-items: end center;
		flex: 1 1 0;
		min-width: 0;
		height: var(--vm-hud-slot-height);
		font-family: var(--vm-font-ui);
		font-size: var(--vm-hud-font-name-slot);
		line-height: 1;
		color: var(--vm-tobacco-black);
	}

	.trainer-name-input__char {
		position: absolute;
		inset: 0;
		display: grid;
		place-items: end center;
		text-transform: uppercase;
	}

	.trainer-name-input__underscore {
		opacity: 0.85;
	}

	.trainer-name-input__slot:has(.trainer-name-input__char:not(:empty)) .trainer-name-input__underscore {
		opacity: 0;
	}

	.trainer-name-input__slot--active .trainer-name-input__char:not(:empty) {
		color: var(--vm-mustard);
	}

	.trainer-name-input__slot--active:has(.trainer-name-input__char:empty) .trainer-name-input__underscore {
		color: var(--vm-mustard);
		opacity: 1;
	}

	.trainer-name-input__native {
		position: relative;
		z-index: 1;
		--trainer-name-cursor-width: var(--vm-hud-font-name-slot);
		width: 100%;
		min-height: var(--vm-hud-slot-height);
		margin: 0;
		padding: 0.15rem 0.1rem 0.15rem calc(var(--trainer-name-cursor-width) + clamp(0.35rem, 1vw, 0.5rem));
		border: 0;
		background: transparent;
		color: transparent;
		caret-color: transparent;
		font-family: var(--vm-font-ui);
		font-size: var(--vm-hud-font-name-slot);
		line-height: 1;
		cursor: text;
		outline: none;
		letter-spacing: 0;
	}

	.trainer-name-input__native::selection {
		background-color: transparent;
		color: transparent;
	}

	.trainer-name-input__native::-moz-selection {
		background-color: transparent;
		color: transparent;
	}

	.trainer-name-input__native:disabled {
		cursor: not-allowed;
	}

	@media (prefers-reduced-motion: reduce) {
		.trainer-name-input__field--focused .trainer-name-input__cursor {
			animation: none;
		}
	}
</style>
