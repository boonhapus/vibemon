<script lang="ts">
	import { untrack } from 'svelte';
	import { Tween, prefersReducedMotion } from 'svelte/motion';
	import { linear } from 'svelte/easing';

	import TrainerReference from '$lib/domains/trainer/TrainerReference.svelte';
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';

	import { runCrewIntro, type IntroRitual, type IntroStage } from './crewIntro';
	import {
		ROTATE_DURATION_MS,
		STEPS_PER_ADVANCE,
		depthCool,
		depthScale,
		effectiveCrewSlot,
		isSpotlight,
		mirrorForPosition,
		quantizeRotation,
		ringPosition,
		seatTickPositions,
		spotlightFactor,
		spotlightSlot
	} from './crewRingMath';
	import { PARTY_SIZE, type PartySlot, type SwapAnimPair } from './crewSlots';

	const INTRO_SPIN_SLOTS = PARTY_SIZE;

	let {
		slots,
		rotation = 0,
		selectedId = '',
		trainerSpriteSrc = '/game/sprites/trainer@128.png',
		trainerName = '',
		swapMode = false,
		swapBusy = false,
		introReady = false,
		introRitual = 'short',
		swapAnimation = null,
		onSelectSlot,
		onTapEmpty,
		onTapEmptyHatch,
		onSelectSwapTarget,
		onIntroComplete,
		onRotationSettled,
		onSpotlightGreet
	}: {
		slots: PartySlot[];
		rotation?: number;
		selectedId?: string;
		trainerSpriteSrc?: string;
		trainerName?: string;
		swapMode?: boolean;
		swapBusy?: boolean;
		introReady?: boolean;
		introRitual?: IntroRitual;
		swapAnimation?: { pairs: SwapAnimPair[]; progress: number } | null;
		onSelectSlot?: (slot: PartySlot) => void;
		onTapEmpty?: (slot: PartySlot) => void;
		onTapEmptyHatch?: () => void;
		onSelectSwapTarget?: (slotIndex: number) => void;
		onIntroComplete?: () => void;
		onRotationSettled?: (spotlight: PartySlot | undefined) => void;
		onSpotlightGreet?: (slot: PartySlot) => void;
	} = $props();

	const rotationTween = new Tween(0, { duration: ROTATE_DURATION_MS, easing: linear });
	const introSpinTween = new Tween(0, { duration: ROTATE_DURATION_MS * INTRO_SPIN_SLOTS, easing: linear });

	let introStage = $state<IntroStage>('pending');
	let landedSlots = $state<Set<number>>(new Set());
	let greetId = $state<string | null>(null);
	let lastSettledRotation = $state(0);
	let lastSpotlightId = $state<string | null>(null);
	let introAbort: AbortController | null = null;

	let displayRotation = $derived(
		quantizeRotation(rotationTween.current) + introSpinTween.current
	);

	$effect(() => {
		const target = rotation;
		void (async () => {
			await rotationTween.set(target, {
				duration: prefersReducedMotion.current ? 0 : ROTATE_DURATION_MS
			});
			if (introStage !== 'done') return;

			const settled = quantizeRotation(rotationTween.current);
			const ticked = settled !== lastSettledRotation;
			if (ticked) lastSettledRotation = settled;

			const spotlight = spotlightSlot(slots, settled);
			const spotlightChanged = spotlight && spotlight.id !== lastSpotlightId;
			if (spotlightChanged) {
				lastSpotlightId = spotlight.id;
				greetId = spotlight.id;
				onSpotlightGreet?.(spotlight);
				setTimeout(() => {
					if (greetId === spotlight.id) greetId = null;
				}, 520);
			}

			if (ticked) onRotationSettled?.(spotlight);
		})();
	});

	// Only re-run when introReady flips — snapshot slots/ritual so party updates do not abort mid-intro.
	$effect(() => {
		if (!introReady) return;

		introAbort = new AbortController();
		const signal = introAbort.signal;
		const { ritual, filledSlots, reducedMotion } = untrack(() => ({
			ritual: introRitual,
			filledSlots: slots
				.filter((slot) => !slot.empty)
				.map((slot) => slot.crewSlot)
				.sort((left, right) => left - right),
			reducedMotion: prefersReducedMotion.current
		}));

		void runCrewIntro({
			ritual,
			filledSlots,
			prefersReducedMotion: reducedMotion,
			signal,
			onStage: (stage) => {
				introStage = stage;
			},
			onLandSlot: (crewSlot) => {
				landedSlots = new Set([...landedSlots, crewSlot]);
			},
			onSpin: async (slotCount, durationMs) => {
				await introSpinTween.set(slotCount, { duration: durationMs });
				await introSpinTween.set(0, { duration: 0 });
			}
		})
			.catch(() => {})
			.finally(() => {
				introStage = 'done';
				onIntroComplete?.();
			});

		return () => {
			introAbort?.abort();
		};
	});

	let placements = $derived(
		slots.map((slot) => {
			const crewSlot = effectiveCrewSlot(slot, swapAnimation);
			const ringOffsetSmooth = crewSlot - (rotationTween.current + introSpinTween.current);
			const position = ringPosition(crewSlot, displayRotation);
			const spotlight = isSpotlight(ringOffsetSmooth);
			const hopVisible = slot.empty || introStage === 'done' || landedSlots.has(slot.crewSlot);
			return {
				slot,
				x: position.x,
				y: position.y,
				scale: depthScale(ringOffsetSmooth),
				cool: depthCool(ringOffsetSmooth),
				zIndex: 10 + Math.round(spotlightFactor(ringOffsetSmooth) * 8),
				spotlight,
				mirrored: mirrorForPosition(slot, position.cos),
				hopVisible,
				idleDelay: slot.crewSlot * 0.42,
				greeting: greetId === slot.id
			};
		})
	);

	const ticks = seatTickPositions();

	function slotAriaLabel(slot: PartySlot): string {
		if (slot.empty) return `Empty crew slot ${slot.crewSlot + 1}`;
		return `${slot.name}, level ${slot.level}`;
	}

	function handleSlotTap(slot: PartySlot) {
		if (introStage !== 'done' || swapBusy) return;
		if (swapMode) {
			onSelectSwapTarget?.(slot.crewSlot);
			return;
		}
		if (slot.empty) {
			onTapEmpty?.(slot);
			return;
		}
		onSelectSlot?.(slot);
	}

	function handleEmptyHatch(event: MouseEvent) {
		event.stopPropagation();
		onTapEmptyHatch?.();
	}
</script>

<div class="crew-formation" class:crew-formation--swap-mode={swapMode}>
	<div class="crew-formation__ground" aria-hidden="true">
		{#each ticks as tick, index (index)}
			<span class="crew-formation__tick" style:--px={tick.x} style:--py={tick.y}></span>
		{/each}
	</div>

	<div class="crew-formation__hub" class:crew-formation__hub--visible={introStage !== 'pending'}>
		<TrainerReference spriteSrc={trainerSpriteSrc} class="crew-formation__trainer" />
		{#if trainerName}
			<span class="crew-formation__nameplate crew-formation__nameplate--trainer" aria-hidden="true">
				{trainerName}
			</span>
		{/if}
	</div>

	{#each placements as placement (placement.slot.id)}
		<div
			class="crew-formation__slot"
			class:crew-formation__slot--hop-in={!placement.slot.empty && placement.hopVisible && introStage === 'assemble'}
			class:crew-formation__slot--hidden={!placement.slot.empty && !placement.hopVisible && introStage !== 'done'}
			class:crew-formation__slot--swap={swapAnimation?.pairs.some((pair) => pair.memberId === placement.slot.id)}
			style:--px={placement.x}
			style:--py={placement.y}
			style:--depth-scale={placement.scale}
			style:--depth-cool="{placement.cool}deg"
			style:--height-factor={placement.slot.heightFactor}
			style:--idle-delay="{placement.idleDelay}s"
			style:z-index={placement.zIndex}
		>
			<FreeFormButton
				class={[
					'crew-formation__slot-button',
					placement.slot.empty && 'crew-formation__slot-button--empty',
					swapMode && 'crew-formation__slot-button--swap-target'
				]
					.filter(Boolean)
					.join(' ')}
				disabled={introStage !== 'done' || swapBusy}
				ariaLabel={slotAriaLabel(placement.slot)}
				onclick={() => handleSlotTap(placement.slot)}
			>
				<span
					class={[
						'crew-formation__platform',
						placement.slot.empty && 'crew-formation__platform--empty',
						!placement.slot.empty &&
							selectedId === placement.slot.id &&
							'crew-formation__platform--active',
						swapMode && 'crew-formation__platform--swap-target'
					]
						.filter(Boolean)
						.join(' ')}
					aria-hidden="true"
				>
					<span class="crew-formation__platform-number">{placement.slot.crewSlot + 1}</span>
				</span>

				{#if !placement.slot.empty}
					<span
						class={[
							'crew-formation__sprite-wrap',
							placement.spotlight && 'crew-formation__sprite-wrap--spotlight',
							!placement.spotlight && 'crew-formation__sprite-wrap--benched',
							placement.greeting && 'crew-formation__sprite-wrap--greet'
						]
							.filter(Boolean)
							.join(' ')}
					>
						<img
							class={[
								'crew-formation__sprite',
								placement.mirrored && 'crew-formation__sprite--mirrored'
							]
								.filter(Boolean)
								.join(' ')}
							src={placement.slot.spriteSrc}
							alt=""
							decoding="async"
						/>
					</span>
					<span
						class={[
							'crew-formation__nameplate',
							placement.spotlight && 'crew-formation__nameplate--spotlight',
							placement.greeting && 'crew-formation__nameplate--greet'
						]
							.filter(Boolean)
							.join(' ')}
						aria-hidden="true"
					>{placement.slot.name}</span>
				{:else if swapMode}
					<span class="crew-formation__empty-hint">Tap to place</span>
				{:else}
					<button type="button" class="crew-formation__hatch-link" onclick={handleEmptyHatch}>
						Hatch
					</button>
				{/if}
			</FreeFormButton>
		</div>
	{/each}
</div>

<style>
	.crew-formation {
		/* Wide, shallow ellipse — stretched left-right to echo the light-green grass
		   bands flanking the meadow. */
		--radius-x: min(42vw, 52rem);
		--radius-y: calc(var(--radius-x) * 0.08);
		--ring-x: 50%;
		/* Anchor low so the formation sits in the near-field grass rather than floating
		   up on the horizon line (which left a large empty foreground apron). */
		--hub-y: 90%;
		--trainer-h: 336px;

		position: relative;
		width: 100%;
		height: 100%;
		min-height: 50dvh;
	}

	.crew-formation__ground {
		position: absolute;
		left: var(--ring-x);
		top: var(--hub-y);
		width: calc(var(--radius-x) * 2 + clamp(5rem, 14vw, 9rem));
		height: calc(var(--radius-y) * 2 + clamp(1.5rem, 4.5vh, 2.5rem));
		transform: translate(-50%, -50%);
		border-radius: 50%;
		pointer-events: none;
		z-index: 1;
		/* Whisper-faint darkened clearing — just enough to seat the formation on the
		   painterly meadow without reading as an obvious ring. */
		background: radial-gradient(
			ellipse 100% 100% at 50% 50%,
			rgb(34 24 16 / 0.1) 0%,
			rgb(34 24 16 / 0.06) 52%,
			rgb(34 24 16 / 0.025) 78%,
			transparent 100%
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
		opacity: 0;
		transition: opacity 320ms steps(8);
	}

	.crew-formation__hub--visible {
		opacity: 1;
	}

	.crew-formation__hub :global(.crew-formation__trainer) {
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

	.crew-formation__slot--hidden {
		opacity: 0;
		pointer-events: none;
	}

	.crew-formation__slot--hop-in {
		animation: crew-hop-in 420ms steps(8) both;
	}

	:global(.crew-formation__slot-button) {
		position: relative;
		padding: 0.25rem;
		overflow: visible;
		flex-shrink: 0;
	}

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
		align-items: flex-end;
		justify-content: center;
		padding-bottom: 0.1rem;
		pointer-events: none;
		z-index: 0;
	}

	.crew-formation__platform--empty {
		opacity: 0.72;
		border: 2px dashed color-mix(in srgb, var(--vm-tobacco) 30%, transparent);
		background: radial-gradient(
			ellipse 100% 100% at 50% 50%,
			color-mix(in srgb, var(--vm-tobacco) 16%, transparent) 0%,
			transparent 72%
		);
	}

	.crew-formation__platform--swap-target {
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--vm-mustard) 55%, transparent);
	}

	.crew-formation__platform-number {
		font-family: var(--vm-font-ui);
		font-size: 1.05rem;
		line-height: 1;
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

	.crew-formation__platform--active .crew-formation__platform-number,
	.crew-formation__platform--empty .crew-formation__platform-number {
		color: var(--vm-mustard);
		opacity: 0.92;
	}

	.crew-formation__sprite-wrap {
		position: relative;
		z-index: 1;
		display: block;
		transform-origin: bottom center;
	}

	.crew-formation__sprite-wrap--spotlight {
		animation: idle-breathe var(--anim-idle-duration) infinite ease-in-out;
		animation-delay: var(--idle-delay, 0s);
	}

	.crew-formation__sprite-wrap--benched {
		opacity: 0.88;
		filter: brightness(0.82) saturate(0.78) hue-rotate(var(--depth-cool, 0deg));
		animation: idle-breathe calc(var(--anim-idle-duration) * 1.08) infinite ease-in-out;
		animation-delay: var(--idle-delay, 0s);
	}

	.crew-formation__sprite-wrap--greet {
		animation: crew-spotlight-greet 520ms steps(8) both;
	}

	.crew-formation__sprite {
		display: block;
		flex-shrink: 0;
		max-width: none;
		height: calc(var(--trainer-h) * var(--height-factor, 0.8));
		width: auto;
		image-rendering: pixelated;
		image-rendering: crisp-edges;
		user-select: none;
		pointer-events: none;
	}

	/* Mirror lives on the img so idle/greet animations on the wrap cannot clobber it. */
	.crew-formation__sprite--mirrored {
		transform: scale(-1, 1);
	}

	.crew-formation__nameplate {
		position: absolute;
		top: calc(100% + 0.55rem);
		left: 50%;
		transform: translateX(-50%);
		max-width: 9rem;
		overflow: hidden;
		/* Breathing room so the clip edge (and the 1px outline) doesn't shave the first
		   glyph's left bearing — letter-spacing pushes it right to the box edge. */
		padding-inline: 0.25rem;
		white-space: nowrap;
		text-overflow: ellipsis;
		font-family: var(--vm-font-ui);
		font-size: 0.625rem;
		line-height: 1.4;
		letter-spacing: 0.07em;
		color: var(--vm-parchment);
		/* Dark pixel-halo so the label reads over the bright meadow — a flat 1px outline
		   plus a soft drop, rather than a single faint shadow. */
		text-shadow:
			0 0 3px rgb(20 12 8 / 0.85),
			1px 0 0 rgb(20 12 8 / 0.7),
			-1px 0 0 rgb(20 12 8 / 0.7),
			0 1px 0 rgb(20 12 8 / 0.7),
			0 -1px 0 rgb(20 12 8 / 0.7);
		pointer-events: none;
		user-select: none;
	}

	.crew-formation__nameplate--spotlight,
	.crew-formation__nameplate--greet {
		font-size: 0.75rem;
		color: var(--vm-mustard);
	}

	.crew-formation__nameplate--trainer {
		font-size: 0.8125rem;
		color: var(--vm-parchment);
		text-transform: uppercase;
		/* Tucked near the feet, with a small gap so it isn't touching them. */
		top: calc(100% - 1.25rem);
	}

	.crew-formation__hatch-link,
	.crew-formation__empty-hint {
		position: relative;
		z-index: 1;
		display: block;
		margin: 0.35rem auto 0;
		padding: 0.15rem 0.45rem;
		border: 0;
		background: transparent;
		font-family: var(--vm-font-ui);
		font-size: 0.625rem;
		line-height: 1.4;
		letter-spacing: 0.08em;
		color: var(--vm-mustard);
		cursor: pointer;
	}

	.crew-formation__empty-hint {
		color: color-mix(in srgb, var(--vm-parchment) 72%, var(--vm-mustard));
		pointer-events: none;
	}

	.crew-formation--swap-mode :global(.crew-formation__slot-button--swap-target) {
		cursor: pointer;
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
