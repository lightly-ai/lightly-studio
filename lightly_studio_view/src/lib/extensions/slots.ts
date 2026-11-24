import type { Component } from 'svelte';

// Every slot and the props it passes to registered components. Slot names describe a place in
// the screen, never a feature. The comment above each slot is its layout contract: where it is
// and what fits there.
export interface SlotProps {
    // Header navigation, in the row after the OSS links: one link per component. The row grows
    // to the right; keep each link as small as an OSS link.
    'nav.items': Record<string, never>;
    // Dataset grid header, right side after the order-by controls: small buttons in one row. The
    // row wraps when the screen is narrow.
    'dataset.toolbar': { datasetId: string; collectionId: string };
}

export type SlotRegistry = {
    [Name in keyof SlotProps]?: Component<SlotProps[Name]>[];
};
