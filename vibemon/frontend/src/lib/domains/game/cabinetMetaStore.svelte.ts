/** Opt-in guide panel — collapsed by default (DESIGN.md §5.2 bezel). */

const STORAGE_KEY = 'vibemon.guide-expanded';

function readPersistedExpanded(): boolean {
	if (typeof localStorage === 'undefined') return false;
	return localStorage.getItem(STORAGE_KEY) === '1';
}

function persistExpanded(expanded: boolean) {
	if (typeof localStorage === 'undefined') return;
	if (expanded) localStorage.setItem(STORAGE_KEY, '1');
	else localStorage.removeItem(STORAGE_KEY);
}

export const cabinetMetaStore = $state({
	expanded: readPersistedExpanded()
});

export function toggleCabinetMeta() {
	cabinetMetaStore.expanded = !cabinetMetaStore.expanded;
	persistExpanded(cabinetMetaStore.expanded);
}

export function closeCabinetMeta() {
	if (!cabinetMetaStore.expanded) return;
	cabinetMetaStore.expanded = false;
	persistExpanded(false);
}
