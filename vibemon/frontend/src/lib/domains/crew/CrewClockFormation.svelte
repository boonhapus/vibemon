<script lang="ts">
	import { Tween, prefersReducedMotion } from 'svelte/motion';
	import { linear } from 'svelte/easing';

	import TrainerReference from '$lib/domains/trainer/TrainerReference.svelte';
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';

	import { PARTY_SIZE, type PartySlot } from './crewSlots';

	const ROTATE_DURATION_MS = 450;
	/* DESIGN.md §6.1 — action states advance in discrete jumps, never smooth
	   easing. Eight quantized sub-steps per 60° advance read as a clock tick. */
	const STEPS_PER_ADVANCE = 8;
	const SLOT_ANGLE_DEG = 360 / PARTY_SIZE;
	/* Lead anchor at 5:00 — nearest the camera, trainer at the hub center. */
	const LEAD_ANGLE_DEG = 60;

	let {
		slots,
		rotation = 0,
		selectedId = '',
		trainerSpriteSrc = '/game/sprites/trainer@128.png',
		onSelectSlot,
		onTapEmpty
	}: {
		slots: PartySlot[];
		/** Cumulative rotation in slot units; slot `mod(rotation, 6)` sits at the lead anchor. */
		rotation?: number;
		selectedId?: string;
		trainerSpriteSrc?: string;
		onSelectSlot?: (slot: PartySlot) => void;
		onTapEmpty?: (slot: PartySlot) => void;
	} = $props();

	// Starts at 0 and is synced to the `rotation` prop by the effect below.
	const rotationTween = new Tween(0, { duration: ROTATE_DURATION_MS, easing: linear });

	$effect(() => {
		void rotationTween.set(rotation, {
			duration: prefersReducedMotion.current ? 0 : ROTATE_DURATION_MS
		});
	});

	/* Quantize the tweened rotation so each 60° advance lands in discrete
	   mechanical jumps instead of a smooth spin. */
	let quantizedRotation = $derived(
		Math.round(rotationTween.current * STEPS_PER_ADVANCE) / STEPS_PER_ADVANCE
	);

	const DEPTH_SCALE_MIN = 0.62;
	const DEPTH_SCALE_MAX = 1.78;
	const DEPTH_BLUR_MAX = 1.6;

	/* Depth peaks only at the 5:00 anchor — cos(slot offset) avoids the sin
	   symmetry that made 5:00 and 7:00 equally prominent. */
	function spotlightFactor(ringOffset: number): number {
		return Math.cos(ringOffset * SLOT_ANGLE_DEG * (Math.PI / 180));
	}

	function depthScale(ringOffset: number): number {
		const spotlight = spotlightFactor(ringOffset);
		const t = (spotlight + 1) / 2;
		const curved = t * t * t;
		return DEPTH_SCALE_MIN + curved * (DEPTH_SCALE_MAX - DEPTH_SCALE_MIN);
	}

	function depthBlur(ringOffset: number): number {
		const spotlight = spotlightFactor(ringOffset);
		const t = (spotlight + 1) / 2;
		return DEPTH_BLUR_MAX * (1 - t * t);
	}

	function isSpotlight(ringOffset: number): boolean {
		return spotlightFactor(ringOffset) > 0.92;
	}

	function mirrorForPosition(slot: PartySlot, cos: number): boolean {
		if (slot.empty) return false;
		const native = slot.facing ?? 'LEFT';
		if (native === 'CENTER') return false;
		// Face the trainer at the hub: left half of the ring reads rightward,
		// right half reads leftward. Near the lead/back axis, keep native facing.
		if (cos < -0.2) return native !== 'RIGHT';
		if (cos > 0.2) return native === 'RIGHT';
		return false;
	}

	let placements = $derived(
		slots.map((slot) => {
			const ringOffset = slot.crewSlot - quantizedRotation;
			/* Position snaps on clock ticks; scale/blur follow the live tween so
			   mons grow and shrink smoothly as they travel toward or away from
			   the 5:00 spotlight. */
			const ringOffsetSmooth = slot.crewSlot - rotationTween.current;
			const angle = ((LEAD_ANGLE_DEG + ringOffset * SLOT_ANGLE_DEG) * Math.PI) / 180;
			const cos = Math.cos(angle);
			const sin = Math.sin(angle);
			const spotlight = isSpotlight(ringOffsetSmooth);
			return {
				slot,
				x: cos,
				y: sin,
				scale: depthScale(ringOffsetSmooth),
				blur: depthBlur(ringOffsetSmooth),
				zIndex: 10 + Math.round(spotlightFactor(ringOffsetSmooth) * 8),
				spotlight,
				mirrored: mirrorForPosition(slot, cos)
			};
		})
	);

	const ticks = Array.from({ length: PARTY_SIZE }, (_, index) => {
		const angle = ((LEAD_ANGLE_DEG + index * SLOT_ANGLE_DEG) * Math.PI) / 180;
		return { x: Math.cos(angle), y: Math.sin(angle) };
	});

	function slotAriaLabel(slot: PartySlot): string {
		if (slot.empty) return 'Empty crew slot';
		return `${slot.name}, level ${slot.level}, ${slot.currentHp} of ${slot.maxHp} HP`;
	}

	function handleSlotTap(slot: PartySlot) {
		if (slot.empty) {
			onTapEmpty?.(slot);
			return;
		}
		onSelectSlot?.(slot);
	}
</script>

<div class="crew-formation">
	<div class="crew-formation__ground" aria-hidden="true">
		{#each ticks as tick, index (index)}
			<span
				class="crew-formation__tick"
				style:--px={tick.x}
				style:--py={tick.y}
			></span>
		{/each}
	</div>

	<div class="crew-formation__hub">
		<TrainerReference spriteSrc={trainerSpriteSrc} class="crew-formation__trainer" />
	</div>

	{#each placements as placement (placement.slot.id)}
		<div
			class="crew-formation__slot"
			style:--px={placement.x}
			style:--py={placement.y}
			style:--depth-scale={placement.scale}
			style:--height-factor={placement.slot.heightFactor}
			style:--depth-blur="{placement.blur}px"
			style:z-index={placement.zIndex}
		>
			<FreeFormButton
				class={[
					'crew-formation__slot-button',
					placement.slot.empty && 'crew-formation__slot-button--empty'
				]
					.filter(Boolean)
					.join(' ')}
				ariaLabel={slotAriaLabel(placement.slot)}
				onclick={() => handleSlotTap(placement.slot)}
			>
				<span
					class={[
						'crew-formation__platform',
						!placement.slot.empty &&
							selectedId === placement.slot.id &&
							'crew-formation__platform--active'
					]
						.filter(Boolean)
						.join(' ')}
					aria-hidden="true"
				>
					<span class="crew-formation__platform-number">{placement.slot.crewSlot + 1}</span>
				</span>
				<img
					class={[
						'crew-formation__sprite',
						placement.slot.empty && 'crew-formation__sprite--empty',
						placement.mirrored && 'crew-formation__sprite--mirrored',
						placement.spotlight && 'crew-formation__sprite--spotlight',
						!placement.spotlight && !placement.slot.empty && 'crew-formation__sprite--benched'
					]
						.filter(Boolean)
						.join(' ')}
					src={placement.slot.spriteSrc}
					alt=""
					decoding="async"
				/>
				{#if !placement.slot.empty}
					<span
						class={[
							'crew-formation__nameplate',
							placement.spotlight && 'crew-formation__nameplate--spotlight'
						]
							.filter(Boolean)
							.join(' ')}
						aria-hidden="true"
					>{placement.slot.name}</span>
				{/if}
			</FreeFormButton>
		</div>
	{/each}
</div>

<style>
	.crew-formation {
		/* The ring sits close to the camera: wide enough that the back arc may
		   slip behind the stats panel — the active front mon is what matters. */
		--radius-x: min(36vw, 46rem);
		/* Ground-level camera: keep the ellipse nearly flat on the floor;
		   depth reads through scale and blur, not vertical lift. */
		--radius-y: calc(var(--radius-x) * 0.1);
		/* Horizontal anchor of the ring; the scene overrides this to share space
		   with the stats column. */
		--ring-x: 50%;
		--hub-y: 78%;
		/* All sprite heights derive from the trainer so species sizes stay honest.
		   2x the native 128px grid: the whole formation sits close to the camera. */
		--trainer-h: 256px;

		position: relative;
		width: 100%;
		height: 100%;
		min-height: 50dvh;
	}

	/* Elliptical clock-face ground plane centered on the trainer hub. */
	.crew-formation__ground {
		position: absolute;
		left: var(--ring-x);
		top: var(--hub-y);
		width: calc(var(--radius-x) * 2 + clamp(5rem, 14vw, 9rem));
		height: calc(var(--radius-y) * 2 + clamp(1.5rem, 4.5vh, 2.5rem));
		transform: translate(-50%, -50%);
		border-radius: 50%;
		pointer-events: none;
		z-index: 0;
		background: radial-gradient(
			ellipse 100% 100% at 50% 50%,
			color-mix(in srgb, #a3ad75 90%, white) 0%,
			#8a9460 34%,
			color-mix(in srgb, #8a9460 62%, #2f3622) 66%,
			color-mix(in srgb, #2f3622 58%, #8a9460) 100%
		);
		-webkit-mask-image: radial-gradient(
			ellipse 82% 78% at 50% 52%,
			rgb(0 0 0 / 1) 0%,
			rgb(0 0 0 / 0.96) 42%,
			rgb(0 0 0 / 0.8) 58%,
			rgb(0 0 0 / 0.5) 72%,
			rgb(0 0 0 / 0.2) 84%,
			rgb(0 0 0 / 0.05) 94%,
			transparent 100%
		);
		mask-image: radial-gradient(
			ellipse 82% 78% at 50% 52%,
			rgb(0 0 0 / 1) 0%,
			rgb(0 0 0 / 0.96) 42%,
			rgb(0 0 0 / 0.8) 58%,
			rgb(0 0 0 / 0.5) 72%,
			rgb(0 0 0 / 0.2) 84%,
			rgb(0 0 0 / 0.05) 94%,
			transparent 100%
		);
	}

	/* Faint tick marks at the six fixed seat anchors. */
	.crew-formation__tick {
		position: absolute;
		left: 50%;
		top: 50%;
		width: clamp(0.35rem, 1vw, 0.55rem);
		height: clamp(0.2rem, 0.55vw, 0.3rem);
		border-radius: 50%;
		background: color-mix(in srgb, var(--vm-tobacco) 55%, transparent);
		transform: translate(
			calc(-50% + var(--px) * var(--radius-x)),
			calc(-50% + var(--py) * var(--radius-y))
		);
	}

	.crew-formation__hub {
		position: absolute;
		left: var(--ring-x);
		top: var(--hub-y);
		transform: translate(-50%, -96%);
		z-index: 10;
		pointer-events: none;
	}

	/* Shrink the trainer reference for hub scale and hide its own platform —
	   the clock-face ground takes its place. Quantized to the 128px sprite
	   grid (DESIGN.md §5.2). */
	.crew-formation__hub :global(.crew-formation__trainer) {
		/* One source pixel = one CSS pixel: the hub trainer renders at native
		   size so mon heights can be read against a stable yardstick. */
		--sprite-h: var(--trainer-h);
		--platform-strength: 0;
	}

	.crew-formation__slot {
		position: absolute;
		left: var(--ring-x);
		top: var(--hub-y);
		transform: translate(
			calc(-50% + var(--px) * var(--radius-x)),
			calc(-92% + var(--py) * var(--radius-y))
		) scale(var(--depth-scale));
		transform-origin: center bottom;
	}

	:global(.crew-formation__slot-button) {
		position: relative;
		padding: 0.25rem;
		overflow: visible;
		flex-shrink: 0;
	}

	/* Seat platform under each mon with a faded slot number. */
	.crew-formation__platform {
		position: absolute;
		left: 50%;
		bottom: calc(-0.2 * var(--platform-h));
		--platform-w: max(7.5rem, 120%);
		--platform-h: 2.3rem;
		width: var(--platform-w);
		height: var(--platform-h);
		transform: translateX(-50%);
		border-radius: 50%;
		background: radial-gradient(
			ellipse 100% 100% at 50% 50%,
			color-mix(in srgb, var(--vm-tobacco) 38%, transparent) 0%,
			color-mix(in srgb, var(--vm-tobacco) 26%, transparent) 55%,
			transparent 78%
		);
		display: flex;
		/* Number rides the front lip of the disc so the mon doesn't cover it. */
		align-items: flex-end;
		justify-content: center;
		padding-bottom: 0.1rem;
		pointer-events: none;
		z-index: 0;
	}

	.crew-formation__platform-number {
		font-family: var(--vm-font-ui);
		font-size: 1.05rem;
		line-height: 1;
		letter-spacing: 0;
		color: var(--vm-parchment);
		opacity: 0.55;
		user-select: none;
	}

	.crew-formation__platform--active {
		background: radial-gradient(
			ellipse 100% 100% at 50% 50%,
			color-mix(in srgb, var(--vm-mustard) 78%, transparent) 0%,
			color-mix(in srgb, var(--vm-mustard) 52%, transparent) 42%,
			color-mix(in srgb, var(--vm-mustard) 28%, transparent) 68%,
			transparent 88%
		);
	}

	.crew-formation__platform--active .crew-formation__platform-number {
		color: var(--vm-mustard);
		opacity: 0.92;
	}

	.crew-formation__nameplate {
		position: absolute;
		top: calc(100% + 0.55rem);
		left: 50%;
		transform: translateX(-50%);
		max-width: 9rem;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
		font-family: var(--vm-font-ui);
		font-size: 0.625rem;
		line-height: 1.4;
		letter-spacing: 0.07em;
		color: var(--vm-parchment);
		text-shadow: 0 1px 0 rgb(20 12 8 / 0.55);
		pointer-events: none;
		user-select: none;
	}

	.crew-formation__sprite {
		position: relative;
		z-index: 1;
		display: block;
		flex-shrink: 0;
		max-width: none;
		/* Honest species height relative to the trainer; depth handles closeness. */
		height: calc(var(--trainer-h) * var(--height-factor, 0.8));
		width: auto;
		image-rendering: pixelated;
		image-rendering: crisp-edges;
		user-select: none;
		pointer-events: none;
		filter: blur(var(--depth-blur, 0px));
	}

	.crew-formation__sprite--spotlight {
		filter: blur(0);
	}

	.crew-formation__sprite--benched {
		opacity: 0.72;
		filter: blur(var(--depth-blur, 0px)) brightness(0.82) saturate(0.78);
	}

	.crew-formation__nameplate--spotlight {
		font-size: 0.75rem;
		color: var(--vm-mustard);
	}

	/* Facing changes are mirror-only — pixel sprites never rotate (DESIGN.md §5.1). */
	.crew-formation__sprite--mirrored {
		transform: scale(-1, 1);
	}

	.crew-formation__sprite--empty {
		filter: blur(var(--depth-blur, 0px)) brightness(0);
		opacity: 0.35;
	}

	@media (max-width: 900px) {
		.crew-formation {
			--trainer-h: 128px;
		}
	}

	@media (max-width: 480px) {
		.crew-formation {
			--radius-x: min(42vw, 11rem);
			--trainer-h: 96px;
		}
	}
</style>
