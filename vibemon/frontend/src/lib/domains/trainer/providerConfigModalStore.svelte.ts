import type { ProviderCatalogEntry, ProviderStatusEntry } from './providerApi';

export type ProviderConfigModalHandlers = {
	onEnable?: () => void | Promise<void>;
	onDisable?: () => void | Promise<void>;
	onRefresh?: () => void | Promise<void>;
};

export const providerConfigModalStore = $state({
	open: false,
	entry: null as ProviderCatalogEntry | null,
	status: undefined as ProviderStatusEntry | undefined,
	enabled: false,
	canDisable: false,
	locationGranted: false,
	fetching: false,
	handlers: {} as ProviderConfigModalHandlers
});

export function closeProviderConfigModal() {
	providerConfigModalStore.open = false;
}
