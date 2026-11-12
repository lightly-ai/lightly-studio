import type { Component } from 'svelte';

// Every slot and the props it passes to registered components. Slot names describe a place in
// the screen, never a feature.
export interface SlotProps {
    'nav.items': Record<string, never>;
    'dataset.toolbar': { datasetId: string; collectionId: string };
}

export type SlotRegistry = {
    [Name in keyof SlotProps]?: Component<SlotProps[Name]>[];
};
