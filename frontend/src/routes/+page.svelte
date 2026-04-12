<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { generation } from '$lib/stores/generation.svelte';
	import { ApiError, postGenerate } from '$lib/api/generate';
	import { filterMajorCities, type MajorCity } from '$lib/data/majorCities';

	let submitting = $state(false);
	let errMsg = $state('');
	let cityQuery = $state('');
	let lat = $state<number | null>(null);
	let lon = $state<number | null>(null);
	let locationLabel = $state<string | null>(null);
	let gpsAttempted = $state(false);
	let suggestionsOpen = $state(false);

	const suggestions = $derived(filterMajorCities(cityQuery, 12));
	const hasCoords = $derived(lat !== null && lon !== null);

	/** Open-Meteo `admin1` is state/province/oblast/etc. — omit when absent. */
	function formatGeocodedLabel(r: {
		name: string;
		country: string;
		admin1?: string;
	}): string {
		const region = (r.admin1 ?? '').trim();
		if (region) return `${r.name}, ${region}, ${r.country}`;
		return `${r.name}, ${r.country}`;
	}

	function selectCity(c: MajorCity) {
		lat = c.lat;
		lon = c.lon;
		cityQuery = c.label;
		locationLabel = c.label;
		suggestionsOpen = false;
		errMsg = '';
	}

	function clearLocation() {
		lat = null;
		lon = null;
		locationLabel = null;
	}

	onMount(() => {
		if (typeof navigator === 'undefined' || !navigator.geolocation) {
			gpsAttempted = true;
			return;
		}
		navigator.geolocation.getCurrentPosition(
			(p) => {
				lat = p.coords.latitude;
				lon = p.coords.longitude;
				locationLabel = 'Device location';
				cityQuery = '';
				gpsAttempted = true;
			},
			() => {
				gpsAttempted = true;
			},
			{ enableHighAccuracy: false, timeout: 10000, maximumAge: 60_000 }
		);
	});

	async function geocodeFreeText() {
		if (!cityQuery.trim()) {
			errMsg = 'Enter a city or pick from suggestions';
			return;
		}
		submitting = true;
		errMsg = '';
		try {
			const url = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cityQuery.trim())}&count=1`;
			const r = await fetch(url);
			const j = (await r.json()) as {
				results?: {
					name: string;
					country: string;
					admin1?: string;
					latitude: number;
					longitude: number;
				}[];
			};
			const first = j.results?.[0];
			if (!first) {
				errMsg = 'City not found — try suggestions or spelling';
				return;
			}
			lat = first.latitude;
			lon = first.longitude;
			locationLabel = formatGeocodedLabel(first);
			cityQuery = locationLabel;
			suggestionsOpen = false;
		} catch {
			errMsg = 'Geocoding failed';
		} finally {
			submitting = false;
		}
	}

	async function doGenerate() {
		if (lat === null || lon === null) {
			errMsg = 'Choose location first';
			return;
		}

		submitting = true;
		errMsg = '';

		try {
			const res = await postGenerate({
				user_id: `web-${crypto.randomUUID()}`,
				latitude: lat,
				longitude: lon,
				auth_tokens: {}
			});
			generation.payload = res;
			await goto('/battle');
		} catch (e) {
			if (e instanceof ApiError && e.status === 422) {
				errMsg = 'Location required';
				return;
			}
			if (e instanceof ApiError) {
				errMsg = `Request failed (${e.status})`;
			} else {
				errMsg = 'Network error';
			}
		} finally {
			submitting = false;
		}
	}
</script>

<div class="layout">
	<h1>Vibemon</h1>
	<p class="muted">Pick your location to generate a creature. More data sources later.</p>

	<div class="auth-section">
		<h2>Data sources</h2>

		<div class="source-block source-block--primary">
			<div class="source-head">
				<span class="source-rank">1</span>
				<div>
					<h3 class="source-title">Location <span class="req">Required</span></h3>
					<p class="source-desc">
						Major cities autocomplete. Look up uses City, Region, Country when available (e.g. US
						states). GPS optional.
					</p>
				</div>
			</div>

			<div class="combo-wrap">
				<input
					type="text"
					class="city-input"
					placeholder="e.g. Austin, Texas, United States"
					autocomplete="off"
					bind:value={cityQuery}
					onfocus={() => {
						suggestionsOpen = true;
					}}
					oninput={() => {
						suggestionsOpen = true;
					}}
					aria-label="City and country"
					aria-autocomplete="list"
					aria-controls={suggestionsOpen && suggestions.length > 0 ? 'city-suggestions' : undefined}
				/>
				{#if suggestionsOpen && suggestions.length > 0}
					<ul id="city-suggestions" class="suggestions" role="listbox">
						{#each suggestions as c (c.label)}
							<li role="presentation">
								<button
									type="button"
									class="suggestion-btn"
									onmousedown={(e) => e.preventDefault()}
									onclick={() => selectCity(c)}
								>
									{c.label}
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			<div class="row-actions">
				<button type="button" class="btn-secondary" onclick={geocodeFreeText} disabled={submitting}>
					Look up name
				</button>
				{#if hasCoords}
					<button type="button" class="btn-ghost" onclick={clearLocation}>Clear</button>
				{/if}
			</div>

			{#if hasCoords}
				<p class="coords-line">
					<span class="ok">✓</span>
					{locationLabel ?? 'Coordinates set'} · lat {lat!.toFixed(4)}, lon {lon!.toFixed(4)}
				</p>
			{:else if !gpsAttempted}
				<p class="muted small">Trying device location…</p>
			{/if}
		</div>

		<div class="source-block source-block--disabled">
			<div class="source-head">
				<span class="source-rank muted-rank">2</span>
				<div>
					<h3 class="source-title">Spotify</h3>
					<p class="source-desc">Listening data for stats and flavour.</p>
				</div>
			</div>
			<button type="button" class="btn-disabled" disabled>Coming soon</button>
		</div>

		<div class="source-block source-block--disabled">
			<div class="source-head">
				<span class="source-rank muted-rank">3</span>
				<div>
					<h3 class="source-title">GitHub</h3>
					<p class="source-desc">Code activity patterns.</p>
				</div>
			</div>
			<button type="button" class="btn-disabled" disabled>Coming soon</button>
		</div>
	</div>

	{#if submitting}
		<p class="muted">Working…</p>
		<div class="spinner" aria-hidden="true"></div>
	{/if}

	{#if hasCoords && !submitting}
		<p>
			<button type="button" onclick={doGenerate} disabled={submitting}>Generate</button>
		</p>
	{/if}

	{#if errMsg}
		<p class="error">{errMsg}</p>
	{/if}
</div>

<style>
	.auth-section {
		margin: var(--sp-6) 0;
		padding: var(--sp-4) var(--sp-5);
		border: 1px solid var(--vb-border);
		border-radius: var(--r-lg);
		background: var(--vb-surface);
		text-align: left;
	}
	.auth-section h2 {
		margin: 0 0 var(--sp-4);
		font-family: var(--f-dt);
		font-size: 11px;
		font-weight: 400;
		color: var(--vb-muted);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.source-block {
		padding: var(--sp-4) 0;
		border-bottom: 1px solid var(--vb-border);
	}
	.source-block:last-child {
		border-bottom: none;
		padding-bottom: 0;
	}
	.source-block--primary {
		padding-top: 0;
	}
	.source-head {
		display: flex;
		gap: var(--sp-3);
		margin-bottom: var(--sp-3);
		align-items: flex-start;
	}
	.source-rank {
		flex-shrink: 0;
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 50%;
		background: var(--teal);
		color: var(--vb-abyss);
		font-family: var(--f-ui);
		font-size: 0.75rem;
		font-weight: 700;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.muted-rank {
		background: var(--vb-void);
		color: var(--vb-muted);
		border: 1px solid var(--vb-border);
	}
	.source-title {
		margin: 0;
		font-family: var(--f-ui);
		font-size: 1rem;
		font-weight: 600;
		color: var(--vb-text);
	}
	.req {
		font-size: 0.7rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--hp-hi);
		margin-left: var(--sp-2);
		vertical-align: middle;
	}
	.source-desc {
		margin: var(--sp-1) 0 0;
		font-family: var(--f-ui);
		font-size: 0.85rem;
		color: var(--vb-muted);
		line-height: 1.4;
	}
	.combo-wrap {
		position: relative;
		max-width: 28rem;
	}
	.city-input {
		width: 100%;
		box-sizing: border-box;
		padding: 0.55rem 0.75rem;
		border-radius: var(--r-md);
		border: 1px solid var(--vb-border);
		background: var(--vb-void);
		color: var(--vb-text);
		font-family: var(--f-ui);
		font-size: 1rem;
	}
	.suggestions {
		position: absolute;
		left: 0;
		right: 0;
		top: 100%;
		margin: 4px 0 0;
		padding: 0;
		list-style: none;
		z-index: 10;
		max-height: 14rem;
		overflow-y: auto;
		border-radius: var(--r-md);
		border: 1px solid var(--vb-border);
		background: var(--vb-deep);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
	}
	.suggestion-btn {
		display: block;
		width: 100%;
		text-align: left;
		padding: 0.5rem 0.75rem;
		border: none;
		background: transparent;
		color: var(--vb-text);
		font-family: var(--f-ui);
		font-size: 0.9rem;
		cursor: pointer;
	}
	.suggestion-btn:hover {
		background: var(--vb-raised);
	}
	.row-actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
		margin-top: var(--sp-3);
	}
	.btn-secondary {
		padding: 0.35rem 0.85rem;
		font-size: 0.85rem;
	}
	.btn-ghost {
		padding: 0.35rem 0.85rem;
		font-size: 0.85rem;
		background: transparent;
		border: 1px solid var(--vb-border);
		color: var(--vb-muted);
	}
	.coords-line {
		margin: var(--sp-3) 0 0;
		font-family: var(--f-ui);
		font-size: 0.85rem;
		color: var(--vb-subtle);
	}
	.ok {
		color: var(--hp-hi);
		margin-right: var(--sp-1);
	}
	.small {
		font-size: 0.85rem;
		margin-top: var(--sp-2);
	}
	.source-block--disabled {
		opacity: 0.72;
	}
	.btn-disabled {
		opacity: 0.55;
		cursor: not-allowed;
		padding: 0.4rem 1rem;
		font-size: 0.85rem;
	}
</style>
