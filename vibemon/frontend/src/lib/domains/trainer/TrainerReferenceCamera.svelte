<script lang="ts">
	import { browser } from '$app/environment';

	import { showGameToast } from '$lib/ui/toastStore.svelte';

	import { uploadTrainerReference } from './trainerApi';

	import { gearSpritePath } from '$lib/domains/game/gearSpritePaths';

	const CAMERA_SPRITE = gearSpritePath('camera', 'left');

	let {
		hovered = $bindable(false),
		disabled = false,
		deferUpload = false,
		uploadReference,
		onReferenceUrl,
		onFileSelected
	}: {
		hovered?: boolean;
		disabled?: boolean;
		/** Hold the likeness locally until a trainer session exists. */
		deferUpload?: boolean;
		/** Custom upload path (e.g. register session before GenAI reference generation). */
		uploadReference?: (file: File) => Promise<string | null>;
		onReferenceUrl?: (referenceUrl: string) => void;
		onFileSelected?: (file: File, previewUrl: string) => void;
	} = $props();

	let buttonEl = $state<HTMLButtonElement | null>(null);
	let fileInput = $state<HTMLInputElement | null>(null);
	let pointerOver = $state(false);
	let pickingFile = $state(false);
	let uploading = $state(false);

	function showHint() {
		hovered = true;
	}

	function syncHintToPointer() {
		if (pickingFile || uploading) {
			hovered = true;
			return;
		}
		hovered = buttonEl?.matches(':hover') ?? false;
		pointerOver = hovered;
	}

	function handlePointerLeave() {
		if (pickingFile || uploading) return;
		pointerOver = false;
		queueMicrotask(() => {
			if (pickingFile || uploading || buttonEl?.matches(':hover')) {
				pointerOver = true;
				return;
			}
			hovered = false;
		});
	}

	function openFilePicker() {
		if (disabled || uploading) return;
		pickingFile = true;
		showHint();
		fileInput?.click();
	}

	function dismissPickerHint() {
		if (!pickingFile) return;
		pickingFile = false;
		if (!uploading) {
			hovered = false;
		}
	}

	function handlePickerClosed() {
		dismissPickerHint();
	}

	async function uploadImmediately(file: File) {
		uploading = true;
		showHint();

		try {
			if (uploadReference) {
				const referenceUrl = await uploadReference(file);
				if (referenceUrl) {
					onReferenceUrl?.(referenceUrl);
				}
				return;
			}

			const result = await uploadTrainerReference(file);
			if (result.status === 'ok' && result.session.reference_url) {
				onReferenceUrl?.(result.session.reference_url);
				return;
			}

			showGameToast(
				result.status === 'failed' ? result.message : 'Could not upload your reference. Try again.',
				'brick'
			);
		} finally {
			uploading = false;
			syncHintToPointer();
		}
	}

	function stageLocally(file: File) {
		const previewUrl = URL.createObjectURL(file);
		onFileSelected?.(file, previewUrl);
	}

	async function handleFileChange(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) {
			dismissPickerHint();
			return;
		}

		if (deferUpload) {
			stageLocally(file);
			input.value = '';
			pickingFile = false;
			syncHintToPointer();
			return;
		}

		await uploadImmediately(file);
		input.value = '';
		pickingFile = false;
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
	class="trainer-reference-camera"
	class:trainer-reference-camera--uploading={uploading}
	disabled={disabled || uploading}
	aria-label="Upload Trainer image"
	aria-busy={uploading}
	onclick={openFilePicker}
	onmouseenter={() => {
		pointerOver = true;
		showHint();
	}}
	onmouseleave={handlePointerLeave}
	onfocus={showHint}
	onblur={() => {
		if (!pickingFile && !uploading) {
			syncHintToPointer();
		}
	}}
>
	<img class="trainer-reference-camera__icon" src={CAMERA_SPRITE} alt="" decoding="async" />
</button>

<input
	bind:this={fileInput}
	class="trainer-reference-camera__input"
	type="file"
	accept="image/*"
	disabled={disabled || uploading}
	aria-hidden="true"
	tabindex={-1}
	onchange={handleFileChange}
	oncancel={dismissPickerHint}
/>

<style>
	.trainer-reference-camera {
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
		transition:
			transform 120ms ease,
			opacity 120ms ease;
	}

	.trainer-reference-camera:hover:not(:disabled),
	.trainer-reference-camera:focus-visible:not(:disabled) {
		transform: scale(1.06);
	}

	.trainer-reference-camera:disabled,
	.trainer-reference-camera--uploading {
		cursor: wait;
		opacity: 0.7;
	}

	.trainer-reference-camera__icon {
		width: 6rem;
		height: auto;
		image-rendering: pixelated;
		image-rendering: crisp-edges;
		user-select: none;
		pointer-events: none;
		filter: drop-shadow(0 2px 0 rgb(42 30 22 / 0.22));
	}

	.trainer-reference-camera__input {
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
</style>
