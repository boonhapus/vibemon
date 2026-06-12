<script lang="ts">
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';

	import TrainerReference from './TrainerReference.svelte';

	const SILHOUETTE_SRC = '/game/sprites/hatchling-silhouette@128.png';
	const DOUBLE_TAP_MS = 750;

	let {
		hovered = $bindable(false),
		hatchable = false,
		spriteSrc = SILHOUETTE_SRC,
		showSilhouette = false,
		generating = false,
		beat = 0,
		revealing = false,
		onhatch
	}: {
		hovered?: boolean;
		hatchable?: boolean;
		spriteSrc?: string;
		showSilhouette?: boolean;
		generating?: boolean;
		beat?: 0 | 1 | 2 | 3;
		revealing?: boolean;
		onhatch?: () => void;
	} = $props();

	let singleTapTimer: ReturnType<typeof setTimeout> | undefined;

	/* Placeholder blob asset is 128×90; generated candidate references are 1:1. */
	let isPlaceholder = $derived(spriteSrc === SILHOUETTE_SRC);
	/* The masked silhouette stays up through generation and dissolves during the
	   crack reveal — by then spriteSrc is this candidate's reference, so the
	   shape the player watches crack open is the creature they get. */
	let masked = $derived(showSilhouette || generating || revealing);
	let activeBeat = $derived(beat > 0 ? beat : generating ? 1 : 0);

	function cancelSingleTap() {
		if (singleTapTimer) {
			clearTimeout(singleTapTimer);
			singleTapTimer = undefined;
		}
	}

	function showHint() {
		if (!hatchable) return;
		hovered = true;
	}

	function hideHint() {
		hovered = false;
	}

	function handleHatchClick() {
		if (!hatchable) return;

		if (singleTapTimer) {
			cancelSingleTap();
			onhatch?.();
			return;
		}

		singleTapTimer = setTimeout(() => {
			singleTapTimer = undefined;
			showHint();
		}, DOUBLE_TAP_MS);
	}
</script>

<div
	class="hatchling-silhouette"
	class:hatchling-silhouette--placeholder={isPlaceholder}
	class:hatchling-silhouette--masked={masked}
	class:hatchling-silhouette--beat-1={activeBeat === 1}
	class:hatchling-silhouette--beat-2={activeBeat === 2}
	class:hatchling-silhouette--beat-3={activeBeat === 3}
	class:hatchling-silhouette--revealing={revealing}
>
	<div class="hatchling-silhouette__reveal-shell">
		<TrainerReference {spriteSrc} class="hatchling-silhouette__reference" />
		{#if masked}
			<div
				class="hatchling-silhouette__sprite-bounds hatchling-silhouette__mask"
				style:--mask-url={`url("${spriteSrc}")`}
				aria-hidden="true"
			>
				<span class="hatchling-silhouette__mask-motion">
					<span class="hatchling-silhouette__mask-halo hatchling-silhouette__mask-halo--a"></span>
					<span class="hatchling-silhouette__mask-halo hatchling-silhouette__mask-halo--b"></span>
					<span class="hatchling-silhouette__mask-body"></span>
					<span class="hatchling-silhouette__mask-flash"></span>
				</span>
			</div>
		{/if}
		{#if hatchable}
			<FreeFormButton
				class="hatchling-silhouette__sprite-bounds hatchling-silhouette__hit"
				ariaLabel="Hatch a new Vibemon from your selected vibes"
				onclick={handleHatchClick}
				onmouseenter={showHint}
				onmouseleave={hideHint}
				onfocus={showHint}
				onblur={hideHint}
			/>
		{/if}
	</div>
</div>

<style>
	.hatchling-silhouette {
		position: relative;
		--hatchling-sprite-h: clamp(10.5rem, 25vh, 18rem);
		/* Candidate references are square; the placeholder blob is 128×90. */
		--hatchling-sprite-w: var(--hatchling-sprite-h);
		/* Match TrainerReference — mask/hit read this on the root, not the nested reference. */
		--platform-h: clamp(2rem, 4.5vw, 3rem);
	}

	.hatchling-silhouette--placeholder {
		--hatchling-sprite-w: calc(var(--hatchling-sprite-h) * 128 / 90);
		--sprite-foot-nudge-y: 3%;
	}

	.hatchling-silhouette:not(.hatchling-silhouette--placeholder) {
		--sprite-foot-nudge-y: calc((1 - var(--hatchling-baseline-y, 0.92)) * 100%);
		--sprite-foot-nudge-x: calc((0.5 - var(--hatchling-anchor-x, 0.5)) * 100%);
	}

	/* Sprite-bounds (mask/hit) are siblings of TrainerReference — read foot nudge from root.
	   TrainerReference must receive the same values explicitly; inherited custom props do not
	   reliably reach its scoped transform rules from the parent component boundary. */
	.hatchling-silhouette--placeholder :global(.hatchling-silhouette__reference) {
		--sprite-foot-nudge-y: 3%;
	}

	.hatchling-silhouette:not(.hatchling-silhouette--placeholder) :global(.hatchling-silhouette__reference) {
		--sprite-foot-nudge-y: calc((1 - var(--hatchling-baseline-y, 0.92)) * 100%);
		--sprite-foot-nudge-x: calc((0.5 - var(--hatchling-anchor-x, 0.5)) * 100%);
	}

	.hatchling-silhouette__reveal-shell {
		position: relative;
		transform-origin: center bottom;
	}

	.hatchling-silhouette :global(.hatchling-silhouette__reference) {
		--sprite-h: var(--hatchling-sprite-h);
		--sprite-w: var(--hatchling-sprite-w);
		--platform-w: calc(var(--sprite-h) * 0.82 * 1.5);
	}

	.hatchling-silhouette :global(.hatchling-silhouette__reference .trainer-reference__sprite) {
		width: var(--sprite-w);
		object-fit: contain;
		object-position: bottom center;
	}

	/* The sprite hides behind the warm-dark mask until the reveal dissolves it. */
	.hatchling-silhouette--masked:not(.hatchling-silhouette--revealing)
		:global(.hatchling-silhouette__reference .trainer-reference__sprite) {
		visibility: hidden;
	}

	/* ---- masked silhouette (DESIGN.md §2.1: warm dark, never pure black) ---- */

	/* Shared sprite canvas — mask and hit target must match TrainerReference foot placement.
	   :global so the class forwarded onto FreeFormButton's inner <button> still matches. */
	:global(.hatchling-silhouette__sprite-bounds) {
		position: absolute;
		bottom: calc(var(--platform-h) * 0.26);
		left: 50%;
		box-sizing: border-box;
		width: var(--hatchling-sprite-w);
		height: var(--hatchling-sprite-h);
		transform: translateX(calc(-50% + var(--sprite-foot-nudge-x, 0%)))
			translateY(calc(-2% + var(--sprite-foot-nudge-y, 0%)));
	}

	.hatchling-silhouette:has(:global(.hatchling-silhouette__hit)) {
		pointer-events: auto;
	}

	.hatchling-silhouette:has(:global(.hatchling-silhouette__hit)) :global(.hatchling-silhouette__reference) {
		pointer-events: none;
	}

	.hatchling-silhouette__mask {
		z-index: 1;
		pointer-events: none;
	}

	.hatchling-silhouette__mask-motion {
		position: absolute;
		inset: 0;
	}

	.hatchling-silhouette__mask-halo,
	.hatchling-silhouette__mask-body,
	.hatchling-silhouette__mask-flash {
		position: absolute;
		inset: 0;
		-webkit-mask-image: var(--mask-url);
		mask-image: var(--mask-url);
		-webkit-mask-repeat: no-repeat;
		mask-repeat: no-repeat;
		-webkit-mask-position: bottom center;
		mask-position: bottom center;
		-webkit-mask-size: contain;
		mask-size: contain;
	}

	/* Pixel halo: two offset copies soften the cutout edge without blur. */
	.hatchling-silhouette__mask-halo {
		background: var(--vm-tobacco);
		opacity: 0.28;
	}

	.hatchling-silhouette__mask-halo--a {
		transform: translate(-2px, -1px);
	}

	.hatchling-silhouette__mask-halo--b {
		transform: translate(2px, 1px);
	}

	/* Warm dark mass: dusk indigo crown into tobacco base, with a slow dither drift. */
	.hatchling-silhouette__mask-body {
		background-color: var(--vm-tobacco);
		background-image:
			radial-gradient(circle at 30% 25%, rgb(240 231 206 / 0.07) 1px, transparent 1px),
			linear-gradient(180deg, var(--vm-dusk-indigo) 0%, var(--vm-tobacco) 72%, var(--vm-tobacco-black) 100%);
		background-size:
			6px 6px,
			100% 100%;
		animation: hatchling-mask-drift 6s steps(8, end) infinite;
	}

	/* 2-frame white-flash layer, fired only during the crack reveal. */
	.hatchling-silhouette__mask-flash {
		background: var(--vm-parchment);
		opacity: 0;
	}

	@keyframes hatchling-mask-drift {
		from {
			background-position:
				0 0,
				0 0;
		}
		to {
			background-position:
				6px 6px,
				0 0;
		}
	}

	/* ---- 3-beat suspense (DESIGN.md §6.1: steps() on action states) ---- */

	/* Beat 1 — settle: ambient breathe; ease-in-out is allowed for slow loops. */
	.hatchling-silhouette--beat-1 .hatchling-silhouette__mask-motion {
		animation: hatchling-settle 3s ease-in-out infinite;
	}

	/* Beat 2 — stir: sharp shudder burst, then a dead pause. Silence sells it. */
	.hatchling-silhouette--beat-2 .hatchling-silhouette__mask-motion {
		animation: hatchling-stir 2.2s steps(4, end) infinite;
	}

	/* Beat 3 — crack build: faster, harder, no rest. */
	.hatchling-silhouette--beat-3 .hatchling-silhouette__mask-motion {
		animation: hatchling-crack-build 0.7s steps(4, end) infinite;
	}

	@keyframes hatchling-settle {
		0%,
		100% {
			transform: translateY(0) scale(1, 1);
		}
		50% {
			transform: translateY(-2px) scale(1.02, 0.98);
		}
	}

	@keyframes hatchling-stir {
		0%,
		24%,
		100% {
			transform: translate(0, 0) rotate(0deg);
		}
		6% {
			transform: translate(-3px, 0) rotate(-0.8deg);
		}
		12% {
			transform: translate(3px, -1px) rotate(0.8deg);
		}
		18% {
			transform: translate(-2px, 0) rotate(-0.4deg);
		}
	}

	@keyframes hatchling-crack-build {
		0%,
		100% {
			transform: translate(0, 0) rotate(0deg);
		}
		25% {
			transform: translate(-4px, -1px) rotate(-1.4deg);
		}
		50% {
			transform: translate(4px, 1px) rotate(1.4deg);
		}
		75% {
			transform: translate(-3px, 0) rotate(-0.9deg);
		}
	}

	/* Aura escalates with the beats. */
	.hatchling-silhouette--beat-1::after,
	.hatchling-silhouette--beat-2::after,
	.hatchling-silhouette--beat-3::after {
		content: '';
		position: absolute;
		inset: 8% 12% 18%;
		border-radius: 48% 48% 42% 42%;
		background: radial-gradient(
			ellipse at 50% 62%,
			color-mix(in srgb, var(--vm-mustard) 28%, transparent) 0%,
			transparent 72%
		);
		animation: hatchling-aura 2.6s ease-in-out infinite;
		pointer-events: none;
	}

	.hatchling-silhouette--beat-2::after {
		animation-duration: 1.8s;
	}

	.hatchling-silhouette--beat-3::after {
		background: radial-gradient(
			ellipse at 50% 62%,
			color-mix(in srgb, var(--vm-mustard) 44%, transparent) 0%,
			transparent 78%
		);
		animation-duration: 0.9s;
	}

	.hatchling-silhouette--beat-2
		:global(.hatchling-silhouette__reference .trainer-reference__platform),
	.hatchling-silhouette--beat-3
		:global(.hatchling-silhouette__reference .trainer-reference__platform) {
		animation: hatchling-platform-glow 2.4s ease-in-out infinite;
	}

	@keyframes hatchling-platform-glow {
		0%,
		100% {
			filter: brightness(1);
		}
		50% {
			filter: brightness(1.08);
		}
	}

	@keyframes hatchling-aura {
		0%,
		100% {
			opacity: 0.28;
			transform: scale(0.98);
		}
		50% {
			opacity: 0.58;
			transform: scale(1.02);
		}
	}

	/* ---- crack reveal: flash snaps twice, the dark mass dissolves in steps ---- */

	.hatchling-silhouette--revealing .hatchling-silhouette__mask {
		animation: hatchling-mask-out 720ms steps(6, end) forwards;
	}

	.hatchling-silhouette--revealing .hatchling-silhouette__mask-flash {
		animation: hatchling-flash 320ms steps(2, jump-none) 2;
	}

	.hatchling-silhouette--revealing .hatchling-silhouette__reveal-shell {
		animation: hatchling-reveal-pop 720ms steps(6, end) both;
	}

	@keyframes hatchling-mask-out {
		0%,
		45% {
			opacity: 1;
		}
		100% {
			opacity: 0;
		}
	}

	@keyframes hatchling-flash {
		0% {
			opacity: 0;
		}
		50% {
			opacity: 0.85;
		}
		100% {
			opacity: 0;
		}
	}

	@keyframes hatchling-reveal-pop {
		0% {
			transform: scale(0.94, 1.02);
		}
		45% {
			transform: scale(1.05, 0.96);
		}
		100% {
			transform: scale(1, 1);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.hatchling-silhouette--beat-1 .hatchling-silhouette__mask-motion,
		.hatchling-silhouette--beat-2 .hatchling-silhouette__mask-motion,
		.hatchling-silhouette--beat-3 .hatchling-silhouette__mask-motion,
		.hatchling-silhouette--beat-1::after,
		.hatchling-silhouette--beat-2::after,
		.hatchling-silhouette--beat-3::after,
		.hatchling-silhouette--beat-2
			:global(.hatchling-silhouette__reference .trainer-reference__platform),
		.hatchling-silhouette--beat-3
			:global(.hatchling-silhouette__reference .trainer-reference__platform),
		.hatchling-silhouette--revealing .hatchling-silhouette__mask,
		.hatchling-silhouette--revealing .hatchling-silhouette__mask-flash,
		.hatchling-silhouette--revealing .hatchling-silhouette__reveal-shell,
		.hatchling-silhouette__mask-body {
			animation: none;
		}

		.hatchling-silhouette--revealing .hatchling-silhouette__mask {
			opacity: 0;
		}
	}

	:global(.hatchling-silhouette__hit) {
		display: block;
		z-index: 2;
		margin: 0;
		padding: 0;
		border: 0;
		cursor: pointer;
		pointer-events: auto;
		transition: transform 120ms ease;
	}

	:global(.hatchling-silhouette__hit:hover),
	:global(.hatchling-silhouette__hit:focus-visible) {
		transform: translateX(calc(-50% + var(--sprite-foot-nudge-x, 0%)))
			translateY(calc(-2% + var(--sprite-foot-nudge-y, 0%)))
			scale(1.03);
	}

	:global(.hatchling-silhouette__hit:not(:disabled):active) {
		transform: translateX(calc(-50% + var(--sprite-foot-nudge-x, 0%)))
			translateY(calc(-2% + var(--sprite-foot-nudge-y, 0%) + 1px));
		opacity: 0.82;
	}
</style>
