<script lang="ts">
	import { browser } from '$app/environment';

	const CAMERA_ICON = '/game/icons/camera.png';

	let {
		hovered = $bindable(false),
		disabled = false
	}: {
		hovered?: boolean;
		disabled?: boolean;
	} = $props();

	let buttonEl = $state<HTMLButtonElement | null>(null);
	let fileInput = $state<HTMLInputElement | null>(null);
	let pointerOver = $state(false);
	let pickingFile = $state(false);

	function showHint() {
		hovered = true;
	}

	function syncHintToPointer() {
		if (pickingFile) {
			hovered = true;
			return;
		}
		hovered = buttonEl?.matches(':hover') ?? false;
		pointerOver = hovered;
	}

	function handlePointerLeave() {
		if (pickingFile) return;
		pointerOver = false;
		queueMicrotask(() => {
			if (pickingFile || buttonEl?.matches(':hover')) {
				pointerOver = true;
				return;
			}
			hovered = false;
		});
	}

	function openFilePicker() {
		if (disabled) return;
		pickingFile = true;
		showHint();
		fileInput?.click();
	}

	function dismissPickerHint() {
		if (!pickingFile) return;
		pickingFile = false;
		hovered = false;
	}

	function handlePickerClosed() {
		dismissPickerHint();
	}

	async function handleFileChange(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) {
			dismissPickerHint();
			return;
		}

		const formData = new FormData();
		formData.append('image', file);

		try {
			await fetch('/api/trainers/portrait', { method: 'POST', body: formData });
		} catch {
			// Stub endpoint — no client feedback yet.
		}

		input.value = '';
		pickingFile = false;
		hovered = false;
	}

	$effect(() => {
		if (!browser) return;

		window.addEventListener('focus', handlePickerClosed);
		return () => window.removeEventListener('focus', handlePickerClosed);
	});
</script>

<button
	bind:this={buttonEl}
	type="button"
	class="trainer-portrait-camera"
	{disabled}
	aria-label="Upload Trainer image"
	onclick={openFilePicker}
	onmouseenter={() => {
		pointerOver = true;
		showHint();
	}}
	onmouseleave={handlePointerLeave}
	onfocus={showHint}
	onblur={() => {
		if (!pickingFile) {
			syncHintToPointer();
		}
	}}
>
	<img class="trainer-portrait-camera__icon" src={CAMERA_ICON} alt="" decoding="async" />
</button>

<input
	bind:this={fileInput}
	class="trainer-portrait-camera__input"
	type="file"
	accept="image/*"
	{disabled}
	aria-hidden="true"
	tabindex={-1}
	onchange={handleFileChange}
	oncancel={dismissPickerHint}
/>

<style>
	.trainer-portrait-camera {
		position: absolute;
		top: -5%;
		right: -5%;
		z-index: 2;
		display: grid;
		place-items: center;
		margin: 0;
		padding: 0.2rem;
		border: 0;
		background: transparent;
		cursor: pointer;
		transition: transform 120ms ease;
	}

	.trainer-portrait-camera:hover:not(:disabled),
	.trainer-portrait-camera:focus-visible:not(:disabled) {
		transform: scale(1.06);
	}

	.trainer-portrait-camera:disabled {
		cursor: not-allowed;
		opacity: 0.55;
	}

	.trainer-portrait-camera__icon {
		width: 6rem;
		height: auto;
		image-rendering: pixelated;
		image-rendering: crisp-edges;
		user-select: none;
		pointer-events: none;
		filter: drop-shadow(0 2px 0 rgb(42 30 22 / 0.22));
	}

	.trainer-portrait-camera__input {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	@media (max-width: 480px) {
		.trainer-portrait-camera {
			top: -4%;
			right: -3%;
		}

		.trainer-portrait-camera__icon {
			width: 5.25rem;
		}
	}
</style>
