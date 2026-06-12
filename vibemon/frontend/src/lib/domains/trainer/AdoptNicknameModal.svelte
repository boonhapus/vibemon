<script lang="ts">
	import GameButton from '$lib/ui/GameButton.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';

	let {
		open = $bindable(false),
		speciesName = '',
		busy = false,
		onConfirm
	}: {
		open?: boolean;
		speciesName?: string;
		busy?: boolean;
		onConfirm?: (nickname: string | null) => void | Promise<void>;
	} = $props();

	let nickname = $state('');

	$effect(() => {
		if (open) nickname = '';
	});

	function close() {
		open = false;
	}

	function handleSkip() {
		void onConfirm?.(null);
	}

	function handleConfirm() {
		const trimmed = nickname.trim();
		void onConfirm?.(trimmed || null);
	}
</script>

{#if open}
	<div class="adopt-nickname-modal" role="presentation">
		<button type="button" class="adopt-nickname-modal__backdrop" aria-label="Close" onclick={close}></button>
		<GamePanel tone="status" class="adopt-nickname-modal__panel">
			<p class="adopt-nickname-modal__prompt">Want to give {speciesName} a nickname before they join the crew?</p>
			<input
				class="adopt-nickname-modal__input"
				type="text"
				maxlength="18"
				bind:value={nickname}
				placeholder="Nickname (optional)"
				disabled={busy}
			/>
			<div class="adopt-nickname-modal__actions">
				<GameButton
					variant="secondary"
					class="adopt-nickname-modal__action"
					ariaLabel="Skip nickname"
					disabled={busy}
					onclick={handleSkip}
				>
					Skip
				</GameButton>
				<GameButton
					variant="primary"
					class="adopt-nickname-modal__action"
					ariaLabel="Confirm nickname"
					disabled={busy}
					onclick={handleConfirm}
				>
					Adopt
				</GameButton>
			</div>
		</GamePanel>
	</div>
{/if}

<style>
	.adopt-nickname-modal {
		position: fixed;
		inset: 0;
		z-index: 30;
		display: grid;
		place-items: center;
		padding: 1rem;
		pointer-events: auto;
	}

	.adopt-nickname-modal__backdrop {
		position: absolute;
		inset: 0;
		border: 0;
		background: rgb(26 18 36 / 0.48);
		cursor: pointer;
	}

	:global(.adopt-nickname-modal__panel) {
		position: relative;
		z-index: 1;
		width: min(100%, 20rem);
	}

	.adopt-nickname-modal__prompt {
		margin: 0 0 0.75rem;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.625rem, 2vw, 0.8125rem);
		line-height: 1.6;
		letter-spacing: 0.04em;
	}

	.adopt-nickname-modal__input {
		width: 100%;
		box-sizing: border-box;
		margin-bottom: 0.85rem;
		padding: 0.55rem 0.65rem;
		border: 2px solid var(--vm-tobacco);
		background: var(--vm-parchment);
		color: var(--vm-tobacco);
		font-family: var(--vm-font-ui);
		font-size: clamp(0.5625rem, 1.8vw, 0.75rem);
		line-height: 1.5;
	}

	.adopt-nickname-modal__actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.55rem;
	}

	.adopt-nickname-modal__actions :global(.adopt-nickname-modal__action) {
		min-width: clamp(4.5rem, 16vw, 6rem);
		font-size: clamp(0.5625rem, 1.8vw, 0.75rem);
	}
</style>
