<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { generation } from '$lib/stores/generation.svelte';
	import VibemonRenderer from '$lib/components/VibemonRenderer.svelte';
	import type { VibemonStats } from '$lib/types';

	let ready = $state(false);

	onMount(() => {
		if (!generation.payload) {
			void goto('/');
			return;
		}
		ready = true;
	});

	let player = $derived(generation.payload?.player);
	let enemy = $derived(generation.payload?.enemy);

	function levelFromStats(s: VibemonStats): number {
		const bst = s.hp + s.attack + s.defense + s.sp_attack + s.sp_defense + s.speed;
		return Math.max(1, Math.min(100, Math.round((bst / 1530) * 78 + 12)));
	}

	function hpPercent(current: number, max: number): number {
		if (max <= 0) return 0;
		return Math.min(100, Math.max(0, (current / max) * 100));
	}

	function hpFillVar(pct: number): string {
		if (pct > 50) return 'var(--hp-hi)';
		if (pct > 25) return 'var(--hp-mid)';
		return 'var(--hp-lo)';
	}

	function expWidth(uid: string): number {
		let h = 0;
		for (let i = 0; i < uid.length; i++) h = (h * 31 + uid.charCodeAt(i)) >>> 0;
		return 35 + (h % 50);
	}

	function moveSecondary(move: {
		category: string;
		power: number;
		accuracy: number;
	}): string {
		const parts = [move.category];
		if (move.power > 0) parts.push(String(move.power));
		parts.push(`${move.accuracy}%`);
		return parts.join(' · ');
	}
</script>

{#if ready && player && enemy}
	<div class="vb">
		<section class="vb-scene" aria-label="Battle field">
			<div class="vb-scene__backdrop" aria-hidden="true"></div>
			<div class="vb-scene__stars" aria-hidden="true"></div>
			<div class="vb-scene__grid" aria-hidden="true"></div>

			<div class="vb-scene__grid-layout">
				<header class="vb-foe-hud">
					<p class="vb-side-tag vb-side-tag--foe">Foe</p>
					<div class="vb-card vb-card--foe">
						<div class="vb-card__row">
							<span class="vb-name">{enemy.name}</span>
							<span class="vb-lv">
								<span class="vb-lv__lbl">Lv.</span><span class="vb-lv__num">{levelFromStats(enemy.stats)}</span>
							</span>
						</div>
						<div class="vb-hp">
							<div class="vb-hp__top">
								<span class="vb-hp__lbl">HP</span>
							</div>
							<div class="vb-hp__track">
								<div
									class="vb-hp__fill"
									style:width="{hpPercent(enemy.stats.hp, enemy.stats.hp)}%"
									style:background={hpFillVar(hpPercent(enemy.stats.hp, enemy.stats.hp))}
								></div>
								<div class="vb-hp__shine" aria-hidden="true"></div>
							</div>
						</div>
					</div>
				</header>

				<div class="vb-foe-sprite">
					<div class="vb-mon vb-mon--foe">
						<VibemonRenderer spriteUrl={enemy.sprite_url} role="enemy" />
					</div>
					<div class="vb-plat vb-plat--foe" aria-hidden="true"></div>
				</div>

				<div class="vb-plyr-sprite">
					<div class="vb-mon vb-mon--plyr">
						<VibemonRenderer spriteUrl={player.sprite_url} role="player" />
					</div>
					<div class="vb-plat vb-plat--plyr" aria-hidden="true"></div>
				</div>

				<footer class="vb-plyr-hud">
					<p class="vb-side-tag vb-side-tag--plyr">You</p>
					<div class="vb-card vb-card--plyr">
						<div class="vb-card__row">
							<span class="vb-name">{player.name}</span>
							<span class="vb-lv">
								<span class="vb-lv__lbl">Lv.</span><span class="vb-lv__num">{levelFromStats(player.stats)}</span>
							</span>
						</div>
						<div class="vb-hp">
							<div class="vb-hp__top">
								<span class="vb-hp__lbl">HP</span>
								<span class="vb-hp__nums"
									>{player.stats.hp}<span class="vb-hp__sep"> / </span>{player.stats.hp}</span
								>
							</div>
							<div class="vb-hp__track">
								<div
									class="vb-hp__fill"
									style:width="{hpPercent(player.stats.hp, player.stats.hp)}%"
									style:background={hpFillVar(hpPercent(player.stats.hp, player.stats.hp))}
								></div>
								<div class="vb-hp__shine" aria-hidden="true"></div>
							</div>
							<div class="vb-exp" style:width="{expWidth(player.uid)}%"></div>
						</div>
					</div>
				</footer>
			</div>
		</section>

		<section class="vb-panel" aria-label="Battle commands">
			<div class="vb-msg">
				<p class="vb-msg__text">
					What will {player.name} do?<span class="vb-msg__cursor" aria-hidden="true"></span>
				</p>
			</div>
			<div class="vb-moves">
				{#each player.moves as move}
					<button class="vb-move" type="button" disabled>
						<span class="vb-move__name">{move.is_signature ? '★ ' : ''}{move.name}</span>
						<span class="vb-move__meta">{moveSecondary(move)}</span>
					</button>
				{/each}
			</div>
		</section>

		{#if player.flavour_text}
			<p class="vb-flavour">{player.flavour_text}</p>
		{/if}
		<p class="vb-back"><a href="/">← Back</a></p>
	</div>
{:else}
	<div class="vb vb--empty">
		<p class="vb-muted">Redirecting…</p>
	</div>
{/if}

<style>
	.vb {
		width: 100%;
		max-width: min(960px, calc(100vw - clamp(16px, 4vw, 48px)));
		margin: 0 auto;
		min-height: 100dvh;
		padding: clamp(var(--sp-2), 2vw, var(--sp-6)) clamp(var(--sp-2), 2vw, var(--sp-6)) var(--sp-8);
		background: var(--vb-abyss);
		box-sizing: border-box;
	}

	.vb--empty {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 50dvh;
	}

	.vb-muted {
		color: var(--vb-muted);
		font-family: var(--f-ui);
	}

	/* —— Scene shell —— */
	.vb-scene {
		position: relative;
		height: clamp(280px, 52vh, 560px);
		min-height: 280px;
		border-radius: var(--r-xl) var(--r-xl) 0 0;
		overflow: hidden;
	}

	.vb-scene__backdrop {
		position: absolute;
		inset: 0;
		background: linear-gradient(
			180deg,
			#06030d 0%,
			#1a0933 18%,
			#4a1261 42%,
			#8b1a5c 58%,
			#c42b60 72%,
			#e8553a 88%,
			#f5874a 100%
		);
	}

	.vb-scene__stars {
		position: absolute;
		inset: 0;
		pointer-events: none;
		opacity: 0.75;
		background-image:
			radial-gradient(1px 1px at 15% 20%, rgba(255, 255, 255, 0.65), transparent),
			radial-gradient(1px 1px at 55% 12%, rgba(255, 255, 255, 0.45), transparent),
			radial-gradient(1.5px 1.5px at 82% 28%, rgba(255, 255, 255, 0.55), transparent),
			radial-gradient(1px 1px at 40% 35%, rgba(255, 255, 255, 0.35), transparent),
			radial-gradient(1px 1px at 70% 8%, rgba(255, 255, 255, 0.5), transparent),
			radial-gradient(1px 1px at 8% 40%, rgba(255, 255, 255, 0.4), transparent),
			radial-gradient(1px 1px at 92% 45%, rgba(255, 255, 255, 0.3), transparent),
			radial-gradient(1px 1px at 25% 15%, rgba(255, 255, 255, 0.5), transparent);
	}

	.vb-scene__grid {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: 52%;
		pointer-events: none;
		opacity: 0.45;
		background: repeating-linear-gradient(
			to bottom,
			transparent 0,
			transparent clamp(14px, 2.2vw, 22px),
			rgba(0, 229, 255, 0.14) clamp(14px, 2.2vw, 22px),
			rgba(0, 229, 255, 0.14) calc(clamp(14px, 2.2vw, 22px) + 1px)
		);
		mask-image: linear-gradient(to bottom, transparent 0%, rgba(0, 0, 0, 0.35) 35%, black 100%);
	}

	/*
	 * Gen 3–style field (matches design doc §3.1):
	 * row1: [ foe HUD ] [ foe sprite ]
	 * row2: (breathing room / horizon)
	 * row3: [ ally sprite ] [ ally HUD ]
	 */
	.vb-scene__grid-layout {
		position: relative;
		z-index: 2;
		display: grid;
		height: 100%;
		width: 100%;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		grid-template-rows: minmax(108px, 30%) 1fr minmax(124px, 36%);
		padding: clamp(8px, 1.5vw, 14px);
		box-sizing: border-box;
		gap: 0;
	}

	.vb-foe-hud {
		grid-column: 1;
		grid-row: 1;
		align-self: start;
		justify-self: start;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 6px;
		min-width: 0;
		max-width: 100%;
	}

	.vb-foe-sprite {
		grid-column: 2;
		grid-row: 1;
		align-self: end;
		justify-self: end;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: flex-end;
		min-width: 0;
	}

	.vb-plyr-sprite {
		grid-column: 1;
		grid-row: 3;
		align-self: end;
		justify-self: start;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: flex-end;
		min-width: 0;
	}

	.vb-plyr-hud {
		grid-column: 2;
		grid-row: 3;
		align-self: end;
		justify-self: end;
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 6px;
		min-width: 0;
		max-width: 100%;
	}

	.vb-side-tag {
		margin: 0;
		font-family: var(--f-px);
		font-size: clamp(5px, 0.2rem + 0.55vw, 7px);
		font-weight: 400;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--vb-muted);
	}

	.vb-side-tag--foe {
		color: rgba(0, 229, 255, 0.55);
	}

	.vb-side-tag--plyr {
		color: rgba(224, 64, 251, 0.55);
		text-align: right;
		width: 100%;
	}

	.vb-card {
		width: min(100%, clamp(190px, 42vw, 320px));
		padding: clamp(8px, 1.4vw, 12px) clamp(10px, 1.8vw, 14px);
		border-radius: var(--r-lg);
		background: rgba(6, 4, 15, 0.88);
		border: 1px solid var(--vb-border);
		box-sizing: border-box;
	}

	.vb-card--foe {
		border-color: rgba(0, 229, 255, 0.45);
	}

	.vb-card--plyr {
		border-color: rgba(224, 64, 251, 0.45);
	}

	.vb-card__row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--sp-2);
		margin-bottom: var(--sp-2);
	}

	.vb-name {
		font-family: var(--f-px);
		font-size: clamp(8px, 0.32rem + 0.95vw, 13px);
		font-weight: 400;
		color: var(--vb-text);
		line-height: 1.5;
		text-align: left;
		word-break: break-word;
	}

	.vb-lv {
		font-family: var(--f-dt);
		font-size: clamp(11px, 0.45rem + 1vw, 16px);
		font-weight: 400;
		white-space: nowrap;
		flex-shrink: 0;
	}

	.vb-lv__lbl {
		color: var(--vb-subtle);
	}

	.vb-lv__num {
		color: var(--gold);
	}

	.vb-hp__top {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--sp-2);
		margin-bottom: 4px;
	}

	.vb-hp__lbl {
		font-family: var(--f-px);
		font-size: clamp(5px, 0.22rem + 0.7vw, 9px);
		color: var(--vb-muted);
	}

	.vb-hp__nums {
		font-family: var(--f-ui);
		font-size: clamp(12px, 0.5rem + 1.2vw, 20px);
		font-weight: 700;
		color: var(--vb-text);
		font-variant-numeric: tabular-nums;
	}

	.vb-hp__sep {
		font-weight: 600;
		color: var(--vb-subtle);
	}

	.vb-hp__track {
		position: relative;
		height: clamp(7px, 1vw, 10px);
		border-radius: var(--r-sm);
		background: var(--vb-void);
		border: 1px solid rgba(255, 255, 255, 0.06);
		overflow: hidden;
	}

	.vb-hp__fill {
		height: 100%;
		border-radius: 1px;
		transition:
			width 0.6s cubic-bezier(0.4, 0, 0.2, 1),
			background 0.3s;
	}

	.vb-hp__shine {
		position: absolute;
		left: 0;
		top: 0;
		right: 0;
		height: 40%;
		border-radius: 2px 2px 0 0;
		background: rgba(255, 255, 255, 0.2);
		pointer-events: none;
	}

	.vb-exp {
		height: clamp(3px, 0.5vw, 5px);
		margin-top: 6px;
		border-radius: 2px;
		background: linear-gradient(90deg, #5c6bc0, var(--teal));
		max-width: 100%;
	}

	.vb-mon {
		width: clamp(140px, 24vw, 240px);
		height: clamp(150px, 28vw, 260px);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.vb-mon :global(.vibemon-wrapper) {
		transform-origin: center bottom;
	}

	.vb-plat {
		border-radius: 50%;
		filter: blur(0.5px);
		margin-top: clamp(-6px, -0.5vw, -3px);
	}

	.vb-plat--foe {
		width: clamp(150px, 26vw, 240px);
		height: clamp(20px, 3.2vw, 32px);
		background: rgba(0, 229, 255, 0.2);
		border-top: 1px solid rgba(0, 229, 255, 0.5);
	}

	.vb-plat--plyr {
		width: clamp(160px, 28vw, 260px);
		height: clamp(22px, 3.6vw, 36px);
		background: rgba(224, 64, 251, 0.2);
		border-top: 1px solid rgba(224, 64, 251, 0.5);
	}

	.vb-panel {
		background: var(--vb-deep);
		border: 2px solid var(--vb-border);
		border-top: none;
		border-radius: 0 0 var(--r-xl) var(--r-xl);
		overflow: hidden;
	}

	.vb-msg {
		padding: clamp(10px, 1.6vw, 14px) clamp(14px, 2.2vw, 20px);
		min-height: clamp(40px, 6.5vh, 56px);
		border-bottom: 1px solid var(--vb-border);
		display: flex;
		align-items: center;
		box-sizing: border-box;
	}

	.vb-msg__text {
		margin: 0;
		font-family: var(--f-px);
		font-size: clamp(7px, 0.35rem + 0.85vw, 11px);
		line-height: 1.85;
		color: var(--vb-text);
	}

	.vb-msg__cursor {
		display: inline-block;
		width: clamp(6px, 0.9vw, 9px);
		height: clamp(6px, 0.9vw, 9px);
		background: var(--vb-text);
		margin-left: 8px;
		vertical-align: middle;
		animation: vb-blink 1s step-end infinite;
	}

	.vb-moves {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: clamp(2px, 0.5vw, 5px);
		padding: clamp(3px, 0.7vw, 6px);
	}

	.vb-move {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: clamp(3px, 0.6vw, 6px);
		padding: clamp(10px, 1.6vw, 16px) clamp(12px, 2vw, 18px);
		text-align: left;
		border-radius: clamp(6px, 1vw, 10px);
		background: var(--vb-surface);
		border: 1px solid var(--vb-border);
		min-height: clamp(52px, 9vh, 88px);
		font: inherit;
		color: inherit;
		cursor: not-allowed;
		transition:
			background 0.12s,
			border-color 0.12s,
			box-shadow 0.12s;
	}

	.vb-move__name {
		font-family: var(--f-px);
		font-size: clamp(7px, 0.32rem + 0.85vw, 11px);
		font-weight: 400;
		color: var(--vb-text);
		line-height: 1.35;
	}

	.vb-move__meta {
		font-family: var(--f-dt);
		font-size: clamp(10px, 0.42rem + 1vw, 14px);
		font-weight: 400;
		color: var(--vb-muted);
		text-transform: lowercase;
	}

	.vb-flavour {
		font-family: var(--f-ui);
		font-size: clamp(0.85rem, 0.38rem + 0.95vw, 1.02rem);
		color: var(--vb-subtle);
		text-align: center;
		margin: var(--sp-4) var(--sp-2) 0;
		line-height: 1.45;
	}

	.vb-back {
		text-align: center;
		margin: var(--sp-3) 0 0;
	}

	@media (max-width: 560px) {
		.vb {
			max-width: 100%;
			padding: var(--sp-2);
		}

		.vb-scene {
			height: clamp(220px, 44vh, 400px);
			min-height: 220px;
		}

		.vb-scene__grid-layout {
			grid-template-rows: minmax(96px, 28%) 1fr minmax(112px, 40%);
			padding: 6px;
		}

		.vb-mon {
			width: clamp(110px, 38vw, 200px);
			height: clamp(118px, 42vw, 210px);
		}

		.vb-plat--foe {
			width: clamp(120px, 40vw, 200px);
		}

		.vb-plat--plyr {
			width: clamp(130px, 42vw, 220px);
		}

		.vb-card {
			width: min(100%, min(92vw, 260px));
		}
	}
</style>
