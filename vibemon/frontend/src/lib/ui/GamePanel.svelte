<script lang="ts">
	import type { Snippet } from 'svelte';

	/** `dialog` = narration. `command` = input/actions. `status` = HP plates and readouts. */
	export type GamePanelTone = 'dialog' | 'command' | 'status';

	let {
		tone = 'dialog',
		class: className = '',
		children
	}: {
		tone?: GamePanelTone;
		class?: string;
		children: Snippet;
	} = $props();
</script>

<div class={['game-panel', `game-panel--${tone}`, className]}>
	<div class="game-panel__frame">
		<div class="game-panel__inset">
			<div class="game-panel__surface">
				<div class="game-panel__content">
					{@render children()}
				</div>
			</div>
		</div>

		<div class="game-panel__corners game-panel__corners--clamp" aria-hidden="true"></div>
	</div>
</div>

<style>
	.game-panel {
		--panel-wood: var(--vm-tobacco);

		/* Fixed px — HUD chrome is pixel-styled; scales with viewport via font/padding tokens only */
		--panel-wood-w: 1px;
		--panel-hairline: var(--vm-tobacco);
		--panel-hairline-w: 4px;
		--panel-bevel: var(--vm-panel-border-light);
		--panel-bevel-w: 10px;
		--panel-inner-trim: transparent;
		--panel-inner-trim-w: 0px;
		--panel-surface: var(--vm-parchment);
		--panel-clamp-color: var(--vm-brass);

		/* Parallel chamfers — each layer tips corners by its cumulative band width */
		--panel-bevel-inner: 4px;
		--panel-bevel-outer: calc(var(--panel-bevel-inner) + var(--panel-bevel-w));
		--panel-chamfer-inset: calc(var(--panel-bevel-outer) + var(--panel-hairline-w));
		--panel-chamfer-frame: calc(var(--panel-chamfer-inset) + var(--panel-wood-w));
		--panel-clamp-arm: 8px;
		--panel-clamp-stroke: 4px;
		--panel-chrome: calc(var(--panel-wood-w) + var(--panel-hairline-w) + var(--panel-bevel-w));
		--panel-accent-inset: calc(var(--panel-chrome) + var(--panel-inner-trim-w) + 2px);

		display: inline-block;
	}

	.game-panel__frame {
		position: relative;
		display: inline-block;
		box-sizing: border-box;
		min-width: 100%;
		padding: 0;
		border: var(--panel-wood-w) solid var(--panel-wood);
		background: var(--panel-wood);
		overflow: hidden;
		box-shadow:
			0 3px 0 rgb(42 30 22 / 0.22),
			0 5px 14px rgb(42 30 22 / 0.18);
		--panel-chamfer: var(--panel-chamfer-frame);
	}

	.game-panel__inset {
		padding: var(--panel-hairline-w);
		background: var(--panel-hairline);
		--panel-chamfer: var(--panel-chamfer-inset);
	}

	.game-panel__surface {
		padding: var(--panel-bevel-w);
		background: var(--panel-bevel);
		--panel-chamfer: var(--panel-bevel-outer);
	}

	.game-panel__content {
		position: relative;
		padding: var(--vm-hud-surface-pad, var(--vm-space-md));
		min-height: 100%;
		background-color: var(--panel-surface);
		box-shadow: inset 0 0 0 var(--panel-inner-trim-w) var(--panel-inner-trim);
		background-image:
			radial-gradient(circle at 18% 24%, rgb(107 68 35 / 0.07) 1px, transparent 1px),
			radial-gradient(circle at 62% 71%, rgb(107 68 35 / 0.05) 1px, transparent 1px),
			radial-gradient(circle at 84% 38%, rgb(107 68 35 / 0.04) 1px, transparent 1px);
		background-size:
			9px 9px,
			13px 13px,
			17px 17px;
		color: inherit;
		--panel-chamfer: var(--panel-bevel-inner);
	}

	.game-panel__frame,
	.game-panel__inset,
	.game-panel__surface,
	.game-panel__content {
		clip-path: polygon(
			var(--panel-chamfer) 0,
			calc(100% - var(--panel-chamfer)) 0,
			100% var(--panel-chamfer),
			100% calc(100% - var(--panel-chamfer)),
			calc(100% - var(--panel-chamfer)) 100%,
			var(--panel-chamfer) 100%,
			0 calc(100% - var(--panel-chamfer)),
			0 var(--panel-chamfer)
		);
	}

	.game-panel__corners {
		position: absolute;
		inset: var(--panel-accent-inset);
		z-index: 2;
		pointer-events: none;
	}

	/* L-clamps at each corner */
	.game-panel__corners--clamp {
		--c: var(--panel-clamp-color);
		--s: var(--panel-clamp-stroke);
		--a: var(--panel-clamp-arm);
		background:
			linear-gradient(var(--c), var(--c)) 0 0 / var(--s) var(--a) no-repeat,
			linear-gradient(var(--c), var(--c)) 0 0 / var(--a) var(--s) no-repeat,
			linear-gradient(var(--c), var(--c)) 100% 0 / var(--s) var(--a) no-repeat,
			linear-gradient(var(--c), var(--c)) 100% 0 / var(--a) var(--s) no-repeat,
			linear-gradient(var(--c), var(--c)) 0 100% / var(--s) var(--a) no-repeat,
			linear-gradient(var(--c), var(--c)) 0 100% / var(--a) var(--s) no-repeat,
			linear-gradient(var(--c), var(--c)) 100% 100% / var(--s) var(--a) no-repeat,
			linear-gradient(var(--c), var(--c)) 100% 100% / var(--a) var(--s) no-repeat;
	}

	.game-panel--status {
		--panel-bevel-w: 5px;
		/* Consumers (e.g. toasts) set --panel-status-accent on this element for sage/amber/brick. */
		--panel-bevel: var(--panel-status-accent, var(--vm-tobacco));
		--panel-surface: var(--panel-status-surface, var(--vm-panel-command-bg));
		--panel-clamp-color: var(--panel-status-accent, var(--vm-tobacco));
		color: var(--vm-tobacco-black);
	}

	.game-panel--command {
		--panel-bevel: var(--panel-command-accent, var(--vm-burnt-orange));
		--panel-surface: var(--panel-command-surface, var(--vm-panel-command-bg));
		--panel-clamp-color: var(--panel-command-clamp, var(--vm-tobacco));
		color: var(--vm-tobacco-black);
	}

	.game-panel--dialog {
		--panel-bevel: var(--vm-plum);
		--panel-inner-trim: var(--vm-mustard);
		--panel-inner-trim-w: calc(var(--panel-bevel-w) / 3);
		--panel-surface: var(--vm-panel-dialog-bg);
		--panel-clamp-color: var(--vm-brass);
		color: var(--vm-panel-dialog-text);
	}

	/* Status panels that replace DialogBox in the same HUD slot. */
	:global(.game-panel.hud-dialog-slot) {
		width: var(--vm-hud-dialog-width);
	}

	:global(.game-panel.hud-dialog-slot.game-panel--status) {
		--panel-bevel-w: 10px;
	}

	:global(.game-panel.hud-dialog-slot .game-panel__content) {
		box-sizing: border-box;
		height: calc(var(--vm-hud-dialog-content-height) + 2 * var(--vm-hud-surface-pad, var(--vm-space-md)));
		display: flex;
		align-items: flex-start;
		padding-right: calc(var(--vm-hud-font-name-slot) + var(--vm-space-sm));
	}
</style>
