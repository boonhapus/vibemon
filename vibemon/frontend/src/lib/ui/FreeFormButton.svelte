<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		onclick,
		onpointerdown,
		onpointerup,
		onpointerleave,
		onpointercancel,
		onmouseenter,
		onmouseleave,
		onfocus,
		onblur,
		oncontextmenu,
		disabled = false,
		ariaLabel,
		class: className = '',
		children
	}: {
		onclick?: (event: MouseEvent) => void;
		onpointerdown?: (event: PointerEvent) => void;
		onpointerup?: (event: PointerEvent) => void;
		onpointerleave?: (event: PointerEvent) => void;
		onpointercancel?: (event: PointerEvent) => void;
		onmouseenter?: (event: MouseEvent) => void;
		onmouseleave?: (event: MouseEvent) => void;
		onfocus?: (event: FocusEvent) => void;
		onblur?: (event: FocusEvent) => void;
		oncontextmenu?: (event: MouseEvent) => void;
		disabled?: boolean;
		ariaLabel: string;
		class?: string;
		children?: Snippet;
	} = $props();

	let rootClass = $derived(['free-form-button', className].filter(Boolean).join(' '));
</script>

<button
	type="button"
	class={rootClass}
	{onclick}
	{onpointerdown}
	{onpointerup}
	{onpointerleave}
	{onpointercancel}
	{onmouseenter}
	{onmouseleave}
	{onfocus}
	{onblur}
	{oncontextmenu}
	{disabled}
	aria-label={ariaLabel}
>
	{#if children}
		{@render children()}
	{/if}
</button>

<style>
	.free-form-button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		margin: 0;
		padding: 0;
		border: 0;
		background: transparent;
		color: inherit;
		font: inherit;
		line-height: inherit;
		cursor: pointer;
		-webkit-tap-highlight-color: transparent;
	}
	.free-form-button:disabled {
		cursor: not-allowed;
		opacity: 0.45;
	}
	.free-form-button:not(:disabled):active {
		transform: translateY(1px);
		opacity: 0.82;
	}
	.free-form-button:focus-visible {
		outline: 2px solid var(--vm-mustard);
		outline-offset: 3px;
	}
</style>
