<script lang="ts">
	import { browser } from '$app/environment';
	import type { Snippet } from 'svelte';
	import { prefersReducedMotion } from 'svelte/motion';

	import GamePanel from './GamePanel.svelte';
	import ElementBadge from './ElementBadge.svelte';

	let {
		text = '',
		showCursor = false,
		typewriter = false,
		charDelay = 42,
		continueDisabled = false,
		onContinue,
		onCursorDown,
		continueTestId,
		emphasis,
		class: className = '',
		children
	}: {
		text?: string;
		showCursor?: boolean;
		typewriter?: boolean;
		charDelay?: number;
		continueDisabled?: boolean;
		onContinue?: () => void;
		/** When set, ▼ click / Down key cycles menu selection instead of continuing. */
		onCursorDown?: () => void;
		continueTestId?: string;
		/** Colors an exact substring within `text` (used for move names in battle dialog). */
		emphasis?: { text: string; color: string; typeBadge?: string };
		class?: string;
		children?: Snippet;
	} = $props();
	let displayedText = $state('');
	let typingDone = $state(false);
	let typingTimer: ReturnType<typeof setInterval> | null = null;
	let revealCursor = $derived(showCursor && typingDone);
	let continueReady = $derived(Boolean(onContinue) && !continueDisabled && revealCursor);
	let cursorDownReady = $derived(Boolean(onCursorDown) && !continueDisabled && revealCursor);
	let panelClass = $derived(['dialog-box', className].filter(Boolean).join(' '));
	let typingText = $derived.by(() => {
		if (!emphasis?.typeBadge) return text;
		const idx = text.indexOf(emphasis.text);
		if (idx === -1) return text;
		return `${text.slice(0, idx)} ${emphasis.text}${text.slice(idx + emphasis.text.length)}`;
	});
	let emphasisParts = $derived.by(() => {
		if (!emphasis) return null;
		const idx = text.indexOf(emphasis.text);
		if (idx === -1) return null;
		const beforeFull = text.slice(0, idx);
		const afterFull = text.slice(idx + emphasis.text.length);
		const len = displayedText.length;

		if (emphasis.typeBadge) {
			const badgeSlotStart = beforeFull.length;
			const moveStart = badgeSlotStart + 1;
			const moveEnd = moveStart + emphasis.text.length;
			// Drop the trailing space before the badge: the badge wrapper's symmetric
			// margin owns the gap on both sides, so "used <badge> Canopy" stays balanced.
			const before = displayedText.slice(0, Math.min(len, badgeSlotStart)).replace(/\s+$/, '');
			const showBadge = len > badgeSlotStart;
			const highlight =
				len > moveStart
					? emphasis.text.slice(0, Math.min(len - moveStart, emphasis.text.length))
					: '';
			const after = len > moveEnd ? afterFull.slice(0, len - moveEnd) : '';
			return {
				before,
				showBadge,
				typeBadge: emphasis.typeBadge,
				highlight,
				after,
				color: emphasis.color
			};
		}

		const before = displayedText.slice(0, Math.min(len, beforeFull.length));
		const moveStart = beforeFull.length;
		const moveEnd = moveStart + emphasis.text.length;
		const highlight =
			len > moveStart ? displayedText.slice(moveStart, Math.min(len, moveEnd)) : '';
		const after = len > moveEnd ? displayedText.slice(moveEnd) : '';
		return {
			before,
			showBadge: false,
			typeBadge: undefined,
			highlight,
			after,
			color: emphasis.color
		};
	});
	function handleContinueClick() {
		if (cursorDownReady) {
			onCursorDown?.();
			return;
		}
		if (continueReady) {
			onContinue?.();
		}
	}
	function handleContinueKeydown(event: KeyboardEvent) {
		if (typewriter && !typingDone && (event.key === 'Enter' || event.key === ' ')) {
			event.preventDefault();
			skipTyping();
			return;
		}
		if (cursorDownReady && event.key === 'ArrowDown') {
			event.preventDefault();
			onCursorDown?.();
			return;
		}
		if (!continueReady) return;
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			onContinue?.();
		}
	}
	export function skipTyping(): boolean {
		if (!typewriter || typingDone) return false;
		if (typingTimer !== null) {
			clearInterval(typingTimer);
			typingTimer = null;
		}
		displayedText = typingText;
		typingDone = true;
		return true;
	}
	$effect(() => {
		const fullText = typingText;
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
		if (typingTimer !== null) {
			clearInterval(typingTimer);
			typingTimer = null;
		}
		typingTimer = setInterval(() => {
			index += 1;
			displayedText = fullText.slice(0, index);
			if (index >= fullText.length) {
				if (typingTimer !== null) clearInterval(typingTimer);
				typingTimer = null;
				typingDone = true;
			}
		}, charDelay);
		return () => {
			if (typingTimer !== null) clearInterval(typingTimer);
			typingTimer = null;
		};
	});
</script>

{#snippet dialogBody()}
	<p class="dialog-box__text" aria-hidden="true">
		{#if emphasisParts}
			{emphasisParts.before}{#if emphasisParts.showBadge && emphasisParts.typeBadge}<span
					class="dialog-box__type-badge-wrap"
					><ElementBadge type={emphasisParts.typeBadge} class="dialog-box__type-badge" /></span
				>{/if}<span class="dialog-box__emphasis" style:color={emphasisParts.color}
				>{emphasisParts.highlight}</span
			>{emphasisParts.after}
		{:else}
			{displayedText}
		{/if}
	</p>

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
			class:dialog-box__content--continue={continueReady || cursorDownReady}
			class:dialog-box__content--with-cursor={showCursor}
			role={continueReady || cursorDownReady ? 'button' : 'status'}
			aria-live={continueReady || cursorDownReady ? undefined : 'polite'}
			aria-label={cursorDownReady ? 'Next option' : continueReady ? 'Continue' : typingText}
			data-testid={continueReady ? continueTestId : undefined}
			tabindex={continueReady || cursorDownReady ? 0 : undefined}
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
		padding-inline: var(--vm-hud-surface-pad, var(--vm-space-md));
	}
	.dialog-box__content {
		position: relative;
		width: 100%;
		box-sizing: border-box;
		height: var(--vm-hud-dialog-content-height);
		display: flex;
		align-items: flex-start;
	}
	.dialog-box__content--with-cursor {
		padding-inline-end: calc(var(--vm-hud-font-name-slot) + var(--vm-space-sm));
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
		font-weight: 400;
		font-size: var(--vm-hud-font-dialog-ui);
		/* Length line-height: two lines exactly fill the fixed dialog block, so the
		   typing effect never reflows the panel. */
		line-height: calc(var(--vm-hud-dialog-content-height) / 2);
		color: inherit;
		white-space: pre-line;
	}
	.dialog-box__emphasis {
		font-weight: inherit;
	}

	.dialog-box__type-badge-wrap {
		display: inline-flex;
		align-items: center;
		/* Span the full line box and center the badge in it, so it sits on the
		   text's optical midline rather than the font's x-height midpoint. */
		height: 1lh;
		vertical-align: top;
		margin-inline: 0.5em;
	}

	:global(.dialog-box__type-badge.element-badge) {
		padding: 0.12rem 0.35rem;
		font-size: 0.52em;
		line-height: 1.2;
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
