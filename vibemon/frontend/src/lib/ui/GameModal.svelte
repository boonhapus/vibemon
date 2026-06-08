<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { Attachment } from 'svelte/attachments';

	import GamePanel, { type GamePanelTone } from './GamePanel.svelte';

	export type GameModalPlacement = 'center' | 'top';

	let {
		open = $bindable(false),
		ariaLabel,
		placement = 'center',
		panelClass = '',
		tone = 'status',
		width,
		maxHeight,
		children
	}: {
		open?: boolean;
		ariaLabel: string;
		placement?: GameModalPlacement;
		panelClass?: string;
		tone?: GamePanelTone;
		/** Sets `--game-modal-width` on the dialog panel. */
		width?: string;
		/** Sets `--game-modal-max-height` on the dialog body scroll region. */
		maxHeight?: string;
		children: Snippet;
	} = $props();

	let dialogEl = $state<HTMLDivElement | null>(null);

	let rootClass = $derived(
		['game-modal', `game-modal--${placement}`, open && 'game-modal--open'].filter(Boolean).join(' ')
	);

	let positionerClass = $derived(
		['game-modal__positioner', `game-modal__positioner--${placement}`].join(' ')
	);

	const portalToBody: Attachment = (element) => {
		document.body.appendChild(element);
		return () => {
			element.remove();
		};
	};

	function close() {
		open = false;
	}

	function handleOverlayClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			close();
		}
	}

	$effect(() => {
		if (open && dialogEl) {
			dialogEl.focus();
		}
	});
</script>

<svelte:window
	onkeydown={(event) => {
		if (open && event.key === 'Escape') {
			close();
		}
	}}
/>

{#if open}
	<div {@attach portalToBody} class={rootClass} role="presentation">
		<div
			class="game-modal__scrim"
			role="presentation"
			onclick={handleOverlayClick}
			onkeydown={(event) => {
				if (event.key === 'Escape') {
					close();
				}
			}}
		></div>
		<div class={positionerClass}>
			<GamePanel {tone} class={panelClass}>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<div
					bind:this={dialogEl}
					class="game-modal__panel"
					role="dialog"
					aria-modal="true"
					aria-label={ariaLabel}
					tabindex="-1"
					style:--game-modal-width={width}
					style:--game-modal-max-height={maxHeight}
					onkeydown={(event) => {
						if (event.key === 'Escape') {
							close();
						}
					}}
				>
					<div class="game-modal__body">
						{@render children()}
					</div>
				</div>
			</GamePanel>
		</div>
	</div>
{/if}

<style>
	.game-modal {
		position: fixed;
		inset: 0;
		z-index: 1000;
		isolation: isolate;
		margin: 0;
		border: 0;
		background: transparent;
		cursor: default;
		pointer-events: none;
		overflow: hidden;
	}

	.game-modal__scrim {
		position: absolute;
		inset: 0;
		background: rgb(42 30 22 / 0.42);
		backdrop-filter: grayscale(1);
		-webkit-backdrop-filter: grayscale(1);
		pointer-events: auto;
	}

	.game-modal__positioner {
		position: relative;
		z-index: 1;
		box-sizing: border-box;
		width: 100%;
		height: 100%;
		display: flex;
		justify-content: center;
		padding: clamp(1rem, 4vw, 2rem);
		pointer-events: none;
	}

	.game-modal__positioner--center {
		align-items: center;
	}

	.game-modal__positioner--top {
		align-items: flex-start;
		padding-top: clamp(1rem, 4vh, 1.75rem);
	}

	.game-modal__positioner :global(.game-panel) {
		pointer-events: auto;
		max-width: 100%;
	}

	.game-modal__panel {
		box-sizing: border-box;
		width: var(--game-modal-width, min(100%, 22rem));
		max-width: 100%;
		display: flex;
		flex-direction: column;
		min-height: 0;
		outline: none;
	}

	.game-modal__body {
		box-sizing: border-box;
		max-height: var(--game-modal-max-height, calc(100dvh - 2rem));
		overflow: auto;
		min-height: 0;
	}

	:global(.game-panel__content:has(.game-modal__panel)) {
		padding: 0;
		min-height: 0;
	}
</style>
