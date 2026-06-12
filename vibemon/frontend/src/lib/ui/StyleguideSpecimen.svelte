<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		title,
		children
	}: {
		title: string;
		children: Snippet;
	} = $props();
</script>

<section class="styleguide-specimen">
	<h3 class="styleguide-specimen__title">{title}</h3>
	<div class="styleguide-specimen__grid">
		<div class="styleguide-specimen__chip styleguide-specimen__chip--parchment">
			<span class="styleguide-specimen__chip-label">Parchment</span>
			<div class="styleguide-specimen__chip-body">
				{@render children()}
			</div>
		</div>
		<div class="styleguide-specimen__chip styleguide-specimen__chip--scene">
			<span class="styleguide-specimen__chip-label">Scene green</span>
			<div class="styleguide-specimen__chip-body">
				{@render children()}
			</div>
		</div>
		<div class="styleguide-specimen__chip styleguide-specimen__chip--tobacco">
			<span class="styleguide-specimen__chip-label">Tobacco bezel</span>
			<div class="styleguide-specimen__chip-body">
				{@render children()}
			</div>
		</div>
	</div>
</section>

<style>
	.styleguide-specimen {
		display: grid;
		gap: var(--vm-space-sm);
	}

	.styleguide-specimen__title {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: 0.75rem;
		line-height: var(--vm-leading-tight);
		letter-spacing: 0.06em;
		color: var(--vm-tobacco);
	}

	.styleguide-specimen__grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--vm-space-md);
	}

	.styleguide-specimen__chip {
		position: relative;
		min-height: 6.5rem;
		padding: var(--vm-space-md);
		border-radius: var(--vm-radius-md);
		border: 2px solid color-mix(in srgb, var(--vm-tobacco) 22%, transparent);
	}

	.styleguide-specimen__chip-label {
		position: absolute;
		top: var(--vm-space-xs);
		left: var(--vm-space-sm);
		font-family: var(--vm-font-ui);
		font-size: 0.5rem;
		line-height: 1;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: color-mix(in srgb, var(--vm-tobacco) 72%, var(--vm-brass));
	}

	.styleguide-specimen__chip-body {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: center;
		gap: var(--vm-space-sm);
		min-height: 5rem;
		padding-top: var(--vm-space-md);
	}

	.styleguide-specimen__chip--parchment {
		background: var(--vm-parchment);
	}

	.styleguide-specimen__chip--scene {
		background:
			linear-gradient(to bottom, #c4a882 0%, #c4a882 52%, #6b7a2a 79%, #6b7a2a 100%);
	}

	.styleguide-specimen__chip--tobacco {
		background: linear-gradient(180deg, #4a3428, #3d2b1f 55%, #2f2117);
		color: var(--vm-parchment);
	}

	.styleguide-specimen__chip--tobacco .styleguide-specimen__chip-label {
		color: color-mix(in srgb, var(--vm-parchment) 72%, var(--vm-brass));
	}

	@media (max-width: 900px) {
		.styleguide-specimen__grid {
			grid-template-columns: 1fr;
		}
	}
</style>
