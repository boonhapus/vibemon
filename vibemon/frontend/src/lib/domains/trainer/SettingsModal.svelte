<script lang="ts">
	import { goto } from '$app/navigation';

	import { clearPendingUsername } from '$lib/domains/trainer/trainerRegisterStore.svelte';
	import FreeFormButton from '$lib/ui/FreeFormButton.svelte';
	import GameModal from '$lib/ui/GameModal.svelte';
	import GamePanel from '$lib/ui/GamePanel.svelte';

	type SettingsOption = {
		id: string;
		label: string;
		available: boolean;
	};

	const SETTINGS_OPTIONS: SettingsOption[] = [
		{ id: 'profile', label: 'Profile', available: false },
		{ id: 'audio', label: 'Audio', available: false },
		{ id: 'controls', label: 'Controls', available: false },
		{ id: 'sign-out', label: 'Sign out', available: true }
	];

	let { open = $bindable(false) }: { open?: boolean } = $props();

	function close() {
		open = false;
	}

	function signOut() {
		clearPendingUsername();
		close();
		void goto('/');
	}

	function handleOptionClick(option: SettingsOption) {
		if (!option.available) return;
		if (option.id === 'sign-out') {
			signOut();
		}
	}

	function optionPanelClass(option: SettingsOption) {
		return ['settings-modal__option-panel', !option.available && 'settings-modal__option-panel--disabled']
			.filter(Boolean)
			.join(' ');
	}
</script>

<GameModal
	bind:open
	ariaLabel="Settings"
	placement="center"
	panelClass="settings-modal__panel"
	width="min(100%, 22rem)"
>
	<div class="settings-modal__header">
		<h2 class="settings-modal__title">Settings</h2>
	</div>

	<ul class="settings-modal__options" role="menu">
		{#each SETTINGS_OPTIONS as option (option.id)}
			<li class="settings-modal__option-item" role="none">
				<FreeFormButton
					class="settings-modal__option-button"
					ariaLabel={option.label}
					disabled={!option.available}
					onclick={() => handleOptionClick(option)}
				>
					<GamePanel tone="command" class={optionPanelClass(option)}>
						<span class="settings-modal__option-label">{option.label}</span>
					</GamePanel>
				</FreeFormButton>
			</li>
		{/each}
	</ul>
</GameModal>

<style>
	:global(.settings-modal__panel .game-modal__body) {
		padding: clamp(0.85rem, 2.4vw, 1.15rem);
	}

	.settings-modal__header {
		margin-bottom: clamp(0.65rem, 1.8vh, 0.9rem);
	}

	.settings-modal__title {
		margin: 0;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.75rem, 2.2vw, 0.9375rem);
		line-height: 1.6;
		letter-spacing: 0.06em;
		text-align: center;
		color: inherit;
	}

	.settings-modal__options {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: clamp(0.45rem, 1.2vh, 0.6rem);
	}

	.settings-modal__option-item,
	:global(.settings-modal__option-button) {
		width: 100%;
	}

	:global(.settings-modal__option-panel) {
		width: 100%;
	}

	:global(.settings-modal__option-panel--disabled) {
		opacity: 0.48;
		filter: grayscale(0.45);
		--panel-command-accent: color-mix(in srgb, var(--vm-tobacco) 55%, var(--vm-brass));
		--panel-command-clamp: color-mix(in srgb, var(--vm-tobacco) 55%, var(--vm-brass));
		--panel-command-surface: color-mix(in srgb, var(--vm-tobacco) 8%, var(--vm-panel-command-bg));
	}

	.settings-modal__option-label {
		display: block;
		font-family: var(--vm-font-ui);
		font-size: clamp(0.6875rem, 2vw, 0.875rem);
		line-height: 1.5;
		letter-spacing: 0.06em;
		text-align: center;
		color: inherit;
	}
</style>
