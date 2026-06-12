<svelte:head>
	<title>Vibemon</title>
</svelte:head>

<main>
	<h1>Vibemon</h1>
	<p>Frontend reset. Build from here.</p>
</main>

<style>
	main {
		display: grid;
		place-content: center;
		min-height: 100vh;
		padding: 2rem;
		text-align: center;
	}

	h1 {
		margin: 0 0 0.5rem;
		font-size: clamp(2rem, 5vw, 3rem);
	}

	p {
		margin: 0;
		opacity: 0.72;
	}
</style>
