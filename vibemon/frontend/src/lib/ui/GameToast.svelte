<script lang="ts">
	import GamePanel from './GamePanel.svelte';
	import { toastStore } from './toastStore.svelte';

	let visible = $derived(toastStore.message !== null);
	let text = $derived(toastStore.message ?? '');
	let panelClass = $derived(`game-toast__panel game-toast__panel--${toastStore.status}`);
</script>

{#if visible}
	<div class="game-toast" role="alert" aria-live="assertive">
		<div class="game-toast__wipe">
			<GamePanel tone="status" class={panelClass}>
				<p class="game-toast__text">{text}</p>
			</GamePanel>
		</div>
	</div>
{/if}

<style>
	.game-toast {
		position: fixed;
		/* Float inside the screen glass: clear the cabinet bezel plus a sliver of
		   canvas, mirroring the register dialog's relationship to the frame. */
		top: calc(var(--vm-bezel-w, 16px) + clamp(0.75rem, 3vh, 1.5rem));
		right: calc(var(--vm-bezel-w, 16px) + clamp(0.75rem, 3vw, 1.5rem));
		left: auto;
		z-index: 100;
		max-width: 30vw;
		pointer-events: none;
	}

	.game-toast__wipe {
		animation: game-toast-wipe-in var(--anim-toast-duration) steps(var(--anim-transition-steps), end) both;
	}

	:global(.game-toast__panel) {
		width: 100%;
		--panel-status-surface: color-mix(in srgb, var(--panel-status-accent) 20%, var(--vm-panel-command-bg));
	}

	:global(.game-toast__panel--sage) {
		--panel-status-accent: var(--vm-status-sage);
	}

	:global(.game-toast__panel--amber) {
		--panel-status-accent: var(--vm-status-amber);
	}

	:global(.game-toast__panel--brick) {
		--panel-status-accent: var(--vm-status-brick);
	}

	.game-toast__text {
		margin: 0;
		font-size: clamp(0.8125rem, 2.6vw, 1rem);
		line-height: 1.75;
		color: inherit;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	@keyframes game-toast-wipe-in {
		from {
			transform: translateX(calc(100% + clamp(1rem, 4vw, 2rem)));
			clip-path: inset(0 0 0 100%);
		}
		to {
			transform: translateX(0);
			clip-path: inset(0 0 0 0);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.game-toast__wipe {
			animation: game-toast-wipe-in-reduced 180ms ease-out both;
		}

		@keyframes game-toast-wipe-in-reduced {
			from {
				opacity: 0;
			}
			to {
				opacity: 1;
			}
		}
	}
</style>
