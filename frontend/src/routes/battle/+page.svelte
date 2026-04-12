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

	// Type badge colors matching Gen 3 palette
	const TYPE_COLORS: Record<string, string> = {
		Normal: '#9099a1',   Fire: '#e8794a',    Water: '#5585e8',
		Grass: '#5ca85c',    Electric: '#e8c840', Ice: '#6ecece',
		Fighting: '#c93040', Poison: '#aa5599',   Ground: '#d4b55a',
		Flying: '#8899e8',   Psychic: '#e8506a',  Bug: '#a8b820',
		Rock: '#b8a038',     Ghost: '#6060b0',    Dragon: '#7038e8',
		Dark: '#6c5a4c',     Steel: '#9898c0',    Fairy: '#e898e8',
	};

	function levelFromStats(s: VibemonStats): number {
		const bst = s.hp + s.attack + s.defense + s.sp_attack + s.sp_defense + s.speed;
		return Math.max(1, Math.min(100, Math.round((bst / 1530) * 78 + 12)));
	}

	function hpColor(pct: number): string {
		if (pct > 50) return '#39ff14';
		if (pct > 25) return '#ffd600';
		return '#ff3860';
	}

	function expWidth(uid: string): number {
		let h = 0;
		for (let i = 0; i < uid.length; i++) h = (h * 31 + uid.charCodeAt(i)) >>> 0;
		return 35 + (h % 50);
	}
</script>

{#if ready && player && enemy}
	<div class="battle">

		<!-- ════════════════ FIELD ════════════════ -->
		<section class="field" aria-label="Battle field">

			<!-- Layered background -->
			<div class="field-sky" aria-hidden="true"></div>
			<div class="field-ground" aria-hidden="true">
				<div class="field-grid" aria-hidden="true"></div>
			</div>
			<div class="field-horizon" aria-hidden="true"></div>

			<!-- Enemy HUD — top left -->
			<div class="hud hud--enemy" role="status" aria-label="{enemy.name} status">
				<div class="hud__body">
					<div class="hud__header">
						<span class="hud__name">{enemy.name}</span>
						<span class="hud__lv">Lv<em>{levelFromStats(enemy.stats)}</em></span>
					</div>
					<div class="hud__hprow">
						<span class="hud__hplbl">HP</span>
						<div class="hud__hptrack">
							<div
								class="hud__hpfill"
								style:width="100%"
								style:background-color={hpColor(100)}
							></div>
						</div>
					</div>
				</div>
			</div>

			<!-- Enemy sprite — upper right (faces left, toward player) -->
			<div class="combatant combatant--enemy">
				<div class="sprite sprite--enemy">
					<VibemonRenderer spriteUrl={enemy.sprite_url} />
				</div>
				<div class="plat plat--enemy" aria-hidden="true"></div>
			</div>

			<!-- Player sprite — lower left (faces right, toward enemy) -->
			<div class="combatant combatant--player">
				<div class="sprite sprite--player">
					<!-- flip=true mirrors the sprite so it faces right (toward enemy) -->
					<VibemonRenderer spriteUrl={player.sprite_url} flip={true} />
				</div>
				<div class="plat plat--player" aria-hidden="true"></div>
			</div>

			<!-- Player HUD — bottom right -->
			<div class="hud hud--player" role="status" aria-label="{player.name} status">
				<div class="hud__body">
					<div class="hud__header">
						<span class="hud__name">{player.name}</span>
						<span class="hud__lv">Lv<em>{levelFromStats(player.stats)}</em></span>
					</div>
					<div class="hud__hprow">
						<span class="hud__hplbl">HP</span>
						<div class="hud__hptrack">
							<div
								class="hud__hpfill"
								style:width="100%"
								style:background-color={hpColor(100)}
							></div>
						</div>
					</div>
					<div class="hud__hpnums">
						<span class="hud__hpnum">{player.stats.hp}</span
						><span class="hud__hpsep">/</span
						><span class="hud__hpnum">{player.stats.hp}</span>
					</div>
					<div class="hud__exptrack">
						<div class="hud__expfill" style:width="{expWidth(player.uid)}%"></div>
					</div>
				</div>
			</div>

		</section><!-- /field -->

		<!-- ════════════════ MENU ════════════════ -->
		<section class="menu" aria-label="Battle commands">

			<!-- Left: message box -->
			<div class="menu-msg">
				<p class="menu-msg__text">
					What will <span class="menu-msg__name">{player.name}</span> do?<span
						class="menu-msg__cursor"
						aria-hidden="true"
					></span>
				</p>
			</div>

			<!-- Right: 2×2 move grid -->
			<div class="menu-moves" role="group" aria-label="Moves">
				{#each player.moves as move}
					<button class="move" type="button" disabled>
						<span class="move__name">{move.is_signature ? '★ ' : ''}{move.name}</span>
						<span
							class="move__type"
							style:background={TYPE_COLORS[move.type] ?? TYPE_COLORS['Normal']}
						>{move.type}</span>
					</button>
				{/each}
			</div>

		</section><!-- /menu -->

		{#if player.flavour_text}
			<p class="battle-flavour">{player.flavour_text}</p>
		{/if}
		<p class="battle-back"><a href="/">← Back</a></p>

	</div>
{:else}
	<div class="battle-empty">
		<p class="battle-empty__text">Redirecting…</p>
	</div>
{/if}

<style>
	/* ─── Outer wrapper ─── */
	.battle {
		width: 100%;
		max-width: min(960px, calc(100vw - clamp(12px, 3vw, 40px)));
		margin: 0 auto;
		min-height: 100dvh;
		padding: clamp(8px, 1.5vw, 20px) clamp(8px, 1.5vw, 20px) 2rem;
		box-sizing: border-box;
		background: var(--vb-abyss);
	}

	.battle-empty {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 50dvh;
	}
	.battle-empty__text {
		color: var(--vb-muted);
		font-family: var(--f-px);
		font-size: 9px;
	}

	/* ════════════════════════════════════════════
	   FIELD
	   ════════════════════════════════════════════ */
	.field {
		position: relative;
		width: 100%;
		height: clamp(260px, 48vw, 460px);
		overflow: hidden;
		border-radius: 6px 6px 0 0;
		border: 2px solid var(--vb-border);
		border-bottom: none;
	}

	/* Sky: top 56% */
	.field-sky {
		position: absolute;
		inset: 0 0 44% 0;
		background: linear-gradient(
			to bottom,
			#04020e 0%,
			#080525 30%,
			#0f083c 65%,
			#180e50 100%
		);
	}

	/* Ground: bottom 44% */
	.field-ground {
		position: absolute;
		inset: 56% 0 0 0;
		background: linear-gradient(
			to bottom,
			#0b2016 0%,
			#08160f 45%,
			#040a07 100%
		);
		overflow: hidden;
	}

	/* Perspective grid lines on ground */
	.field-grid {
		position: absolute;
		inset: 0;
		background: repeating-linear-gradient(
			to bottom,
			transparent 0,
			transparent 16px,
			rgba(0, 229, 255, 0.06) 16px,
			rgba(0, 229, 255, 0.06) 17px
		);
		transform: perspective(120px) rotateX(18deg);
		transform-origin: top center;
		mask-image: linear-gradient(to bottom, rgba(0,0,0,0.15) 0%, black 60%);
	}

	/* Horizon glow line */
	.field-horizon {
		position: absolute;
		left: 0;
		right: 0;
		top: 56%;
		height: 1px;
		background: linear-gradient(
			to right,
			transparent 0%,
			rgba(0, 229, 255, 0.25) 15%,
			rgba(0, 229, 255, 0.7) 40%,
			rgba(100, 255, 218, 0.9) 50%,
			rgba(0, 229, 255, 0.7) 60%,
			rgba(0, 229, 255, 0.25) 85%,
			transparent 100%
		);
		z-index: 2;
		box-shadow: 0 0 8px rgba(0, 229, 255, 0.3);
	}

	/* ── HUD boxes ── */
	.hud {
		position: absolute;
		z-index: 4;
		width: min(44%, clamp(160px, 36vw, 260px));
	}

	.hud--enemy {
		top: 5%;
		left: 3%;
	}

	.hud--player {
		bottom: 5%;
		right: 3%;
	}

	.hud__body {
		background: rgba(6, 4, 18, 0.93);
		border-radius: 4px;
		padding: clamp(6px, 1vw, 10px) clamp(8px, 1.2vw, 12px);
		backdrop-filter: blur(6px);
	}

	.hud--enemy .hud__body {
		border: 1.5px solid rgba(0, 229, 255, 0.55);
		box-shadow:
			0 0 0 1px rgba(0, 229, 255, 0.08),
			0 4px 16px rgba(0, 229, 255, 0.1);
	}

	.hud--player .hud__body {
		border: 1.5px solid rgba(224, 64, 251, 0.55);
		box-shadow:
			0 0 0 1px rgba(224, 64, 251, 0.08),
			0 4px 16px rgba(224, 64, 251, 0.1);
	}

	.hud__header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 6px;
		margin-bottom: clamp(4px, 0.7vw, 7px);
	}

	.hud__name {
		font-family: var(--f-px);
		font-size: clamp(6px, 0.38rem + 0.7vw, 10px);
		font-weight: 400;
		color: var(--vb-text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 68%;
		letter-spacing: 0.03em;
	}

	.hud__lv {
		font-family: var(--f-px);
		font-size: clamp(5px, 0.3rem + 0.6vw, 9px);
		color: var(--vb-subtle);
		white-space: nowrap;
		flex-shrink: 0;
	}

	.hud__lv em {
		font-style: normal;
		color: var(--gold);
	}

	.hud__hprow {
		display: flex;
		align-items: center;
		gap: clamp(4px, 0.6vw, 7px);
	}

	.hud__hplbl {
		font-family: var(--f-px);
		font-size: clamp(5px, 0.28rem + 0.5vw, 8px);
		color: var(--vb-muted);
		flex-shrink: 0;
		letter-spacing: 0.05em;
	}

	.hud__hptrack {
		flex: 1;
		height: clamp(6px, 0.9vw, 9px);
		border-radius: 2px;
		background: #0e0b22;
		border: 1px solid rgba(255, 255, 255, 0.07);
		overflow: hidden;
		position: relative;
	}

	/* inner shine on HP track */
	.hud__hptrack::after {
		content: '';
		position: absolute;
		inset: 0 0 50% 0;
		background: rgba(255, 255, 255, 0.1);
		pointer-events: none;
	}

	.hud__hpfill {
		height: 100%;
		border-radius: 1px;
		transition: width 0.55s cubic-bezier(0.4, 0, 0.2, 1);
	}

	/* Player-only: HP numbers + EXP */
	.hud__hpnums {
		display: flex;
		align-items: baseline;
		justify-content: flex-end;
		gap: 2px;
		margin-top: clamp(3px, 0.5vw, 5px);
	}

	.hud__hpnum {
		font-family: var(--f-dt);
		font-size: clamp(11px, 0.7rem + 0.9vw, 17px);
		color: var(--vb-text);
		font-variant-numeric: tabular-nums;
		font-weight: 400;
	}

	.hud__hpsep {
		font-family: var(--f-dt);
		font-size: clamp(9px, 0.55rem + 0.7vw, 14px);
		color: var(--vb-muted);
		margin: 0 1px;
	}

	.hud__exptrack {
		height: 4px;
		border-radius: 2px;
		background: #0a0918;
		border: 1px solid rgba(255, 255, 255, 0.05);
		overflow: hidden;
		margin-top: clamp(3px, 0.5vw, 5px);
	}

	.hud__expfill {
		height: 100%;
		border-radius: 2px;
		background: linear-gradient(90deg, #5c6bc0, var(--teal));
	}

	/* ── Combatant areas ── */
	.combatant {
		position: absolute;
		display: flex;
		flex-direction: column;
		align-items: center;
		z-index: 3;
	}

	/* Enemy: upper-right, feet near horizon */
	.combatant--enemy {
		right: 4%;
		top: 4%;
		bottom: 42%;          /* bottom of this zone = 58% from top ≈ horizon */
		justify-content: flex-end;
	}

	/* Player: lower-left, feet near bottom of field */
	.combatant--player {
		left: 4%;
		bottom: 3%;
	}

	/* ── Sprites ── */
	.sprite {
		display: flex;
		align-items: flex-end;
		justify-content: center;
	}

	.sprite--enemy {
		width: clamp(100px, 17vw, 190px);
		height: clamp(110px, 18vw, 200px);
	}

	.sprite--player {
		width: clamp(120px, 21vw, 230px);
		height: clamp(130px, 23vw, 245px);
	}

	/* ── Battle platforms (Gen 3-style ellipse) ── */
	.plat {
		border-radius: 50%;
		margin-top: clamp(-5px, -0.7vw, -3px);
	}

	.plat--enemy {
		width: clamp(90px, 15vw, 170px);
		height: clamp(14px, 2.2vw, 24px);
		background: radial-gradient(
			ellipse at center,
			rgba(0, 229, 255, 0.28) 0%,
			rgba(0, 229, 255, 0.08) 55%,
			transparent 100%
		);
		border: 1px solid rgba(0, 229, 255, 0.35);
		box-shadow: 0 0 10px rgba(0, 229, 255, 0.12);
	}

	.plat--player {
		width: clamp(120px, 20vw, 215px);
		height: clamp(18px, 2.8vw, 30px);
		background: radial-gradient(
			ellipse at center,
			rgba(224, 64, 251, 0.28) 0%,
			rgba(224, 64, 251, 0.08) 55%,
			transparent 100%
		);
		border: 1px solid rgba(224, 64, 251, 0.35);
		box-shadow: 0 0 10px rgba(224, 64, 251, 0.12);
	}

	/* ════════════════════════════════════════════
	   MENU  (Gen 3: msg LEFT | moves RIGHT)
	   ════════════════════════════════════════════ */
	.menu {
		display: flex;
		border: 2px solid var(--vb-border);
		border-top: 3px solid rgba(0, 229, 255, 0.3);
		border-radius: 0 0 6px 6px;
		overflow: hidden;
		min-height: clamp(90px, 17vh, 148px);
	}

	/* Message box — left 55% */
	.menu-msg {
		flex: 0 0 55%;
		display: flex;
		align-items: center;
		padding: clamp(10px, 1.6vw, 16px) clamp(12px, 2vw, 20px);
		background: var(--vb-void);
		border-right: 2px solid var(--vb-border);
		box-sizing: border-box;
	}

	.menu-msg__text {
		margin: 0;
		font-family: var(--f-px);
		font-size: clamp(7px, 0.38rem + 0.75vw, 11px);
		line-height: 2;
		color: var(--vb-text);
	}

	.menu-msg__name {
		color: var(--teal-hi);
	}

	/* Blinking triangle cursor (Gen 3 style) */
	.menu-msg__cursor {
		display: inline-block;
		width: 0;
		height: 0;
		border-left: 5px solid transparent;
		border-right: 5px solid transparent;
		border-top: 7px solid var(--vb-text);
		vertical-align: middle;
		margin-left: 8px;
		animation: vb-blink 0.9s step-end infinite;
	}

	/* Move grid — right 45% */
	.menu-moves {
		flex: 1;
		display: grid;
		grid-template-columns: 1fr 1fr;
		grid-template-rows: 1fr 1fr;
		gap: 3px;
		padding: 4px;
		background: var(--vb-deep);
	}

	.move {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		justify-content: space-between;
		gap: 4px;
		padding: clamp(7px, 1.2vw, 12px) clamp(8px, 1.4vw, 14px);
		background: var(--vb-void);
		border: 1px solid var(--vb-border);
		border-radius: 3px;
		cursor: not-allowed;
		font: inherit;
		color: inherit;
		text-align: left;
		transition: background 0.1s;
		overflow: hidden;
	}

	.move__name {
		font-family: var(--f-px);
		font-size: clamp(5px, 0.3rem + 0.65vw, 8px);
		color: var(--vb-text);
		line-height: 1.4;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 100%;
	}

	.move__type {
		font-family: var(--f-ui);
		font-size: clamp(8px, 0.45rem + 0.6vw, 11px);
		font-weight: 700;
		padding: 1px 6px 2px;
		border-radius: 2px;
		color: #fff;
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
		letter-spacing: 0.02em;
		white-space: nowrap;
	}

	/* ─── Footer ─── */
	.battle-flavour {
		font-family: var(--f-ui);
		font-size: clamp(0.82rem, 0.36rem + 0.92vw, 1rem);
		color: var(--vb-subtle);
		text-align: center;
		margin: var(--sp-4) var(--sp-2) 0;
		line-height: 1.5;
	}

	.battle-back {
		text-align: center;
		margin: var(--sp-3) 0 0;
	}

	/* ─── Responsive ─── */
	@media (max-width: 520px) {
		.battle {
			max-width: 100%;
			padding: 6px 6px 2rem;
		}

		.field {
			height: clamp(220px, 66vw, 340px);
		}

		.hud {
			width: min(46%, clamp(130px, 42vw, 220px));
		}

		.menu {
			flex-direction: column;
			min-height: auto;
		}

		.menu-msg {
			flex: none;
			border-right: none;
			border-bottom: 2px solid var(--vb-border);
			min-height: 52px;
		}

		.menu-moves {
			min-height: 96px;
		}
	}
</style>
