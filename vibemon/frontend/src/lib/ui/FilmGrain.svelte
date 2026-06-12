<div class="film-grain" aria-hidden="true">
	<div class="film-grain__vignette"></div>
</div>

<style>
	.film-grain {
		position: absolute;
		inset: 0;
		z-index: 10;
		pointer-events: none;
	}

	.film-grain::before {
		content: '';
		position: absolute;
		inset: 0;
		opacity: var(--vm-film-grain-opacity);
		mix-blend-mode: overlay;
		background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3CfeComponentTransfer%3E%3CfeFuncR type='linear' slope='2.5' intercept='-0.75'/%3E%3CfeFuncG type='linear' slope='2.5' intercept='-0.75'/%3E%3CfeFuncB type='linear' slope='2.5' intercept='-0.75'/%3E%3C/feComponentTransfer%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
		background-size: 180px 180px;
	}

	.film-grain__vignette {
		position: absolute;
		inset: 0;
		background: radial-gradient(
			ellipse 92% 88% at 50% 46%,
			transparent 52%,
			rgb(42 30 22 / var(--vm-vignette-strength)) 100%
		);
	}
</style>
