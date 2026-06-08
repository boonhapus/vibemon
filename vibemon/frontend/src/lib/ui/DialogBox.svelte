<script lang="ts">
	import { browser } from '$app/environment';
	import type { Snippet } from 'svelte';
	import { prefersReducedMotion } from 'svelte/motion';

	import GamePanel from './GamePanel.svelte';

	let {
		text = '',
		showCursor = false,
		typewriter = false,
		charDelay = 42,
		continueDisabled = false,
		onContinue,
		class: className = '',
		children
	}: {
		text?: string;
		showCursor?: boolean;
		typewriter?: boolean;
		charDelay?: number;
		continueDisabled?: boolean;
		onContinue?: () => void;
		class?: string;
		children?: Snippet;
	} = $props();
	let displayedText = $state('');
	let typingDone = $state(false);
	let revealCursor = $derived(showCursor && typingDone);
	let continueReady = $derived(Boolean(onContinue) && !continueDisabled && revealCursor);
	let panelClass = $derived(['dialog-box', className].filter(Boolean).join(' '));
	function handleContinueClick() {
		if (continueReady) {
			onContinue?.();
		}
	}
	function handleContinueKeydown(event: KeyboardEvent) {
		if (!continueReady) return;
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			onContinue?.();
		}
	}
	$effect(() => {
		const fullText = text;
		if (!typewriter) {
			displayedText = fullText;
			typingDone = true;
			return;
		}
		if (!browser) {
			displayedText = fullText;
			typingDone = true;
			return;
		}
		if (prefersReducedMotion.current) {
			displayedText = fullText;
			typingDone = true;
			return;
		}
		displayedText = '';
		typingDone = false;
		let index = 0;
		const timer = window.setInterval(() => {
			index += 1;
			displayedText = fullText.slice(0, index);
			if (index >= fullText.length) {
				window.clearInterval(timer);
				typingDone = true;
			}
		}, charDelay);
		return () => window.clearInterval(timer);
	});
</script>

{#snippet dialogBody()}
	<p class="dialog-box__text" aria-hidden="true">{displayedText}</p>

	{#if revealCursor}
		<span class="dialog-box__cursor" aria-hidden="true">▼</span>
	{/if}
{/snippet}

<GamePanel tone="dialog" class={panelClass}>
	{#if children}
		<div class="dialog-box__content" role="status" aria-live="polite" aria-label={text}>
			{@render children()}
		</div>
	{:else}
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->

		<div
			class="dialog-box__content"
			class:dialog-box__content--continue={continueReady}
			role={continueReady ? 'button' : 'status'}
			aria-live={continueReady ? undefined : 'polite'}
			aria-label={continueReady ? 'Continue' : text}
			tabindex={continueReady ? 0 : undefined}
			onclick={handleContinueClick}
			onkeydown={handleContinueKeydown}
		>
			{@render dialogBody()}
		</div>
	{/if}
</GamePanel>

<style>
	:global(.dialog-box) {
		width: var(--vm-hud-dialog-width);
	}
	:global(.dialog-box .game-panel__content) {
		background-image: none;
		padding-left: calc(var(--vm-hud-surface-pad, var(--vm-space-md)) + 10px);
	}
	.dialog-box__content {
		position: relative;
		width: 100%;
		box-sizing: border-box;
		height: var(--vm-hud-dialog-content-height);
		display: flex;
		align-items: flex-start;
		padding-right: calc(var(--vm-hud-font-name-slot) + var(--vm-space-sm));
	}
	.dialog-box__content--continue {
		cursor: pointer;
	}
	.dialog-box__content--continue:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: 3px;
	}
	.dialog-box__content--continue:active {
		opacity: 0.92;
	}
	.dialog-box__text {
		margin: 0;
		flex: 1;
		min-width: 0;
		font-family: var(--vm-font-ui);
		font-size: var(--vm-hud-font-dialog);
		line-height: var(--vm-hud-dialog-line-height);
		color: inherit;
	}
	:global(.dialog-box__cursor) {
		position: absolute;
		right: var(--vm-space-md);
		bottom: var(--vm-space-sm);
		font-family: var(--vm-font-ui);
		font-size: var(--vm-hud-font-name-slot);
		line-height: 1;
		color: inherit;
		animation: vm-cursor-blink 900ms steps(2, end) infinite;
		pointer-events: none;
	}
	@media (prefers-reduced-motion: reduce) {
		:global(.dialog-box__cursor) {
			animation: none;
		}
	}
</style>
