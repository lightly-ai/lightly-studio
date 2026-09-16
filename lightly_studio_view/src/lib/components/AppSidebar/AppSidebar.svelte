<script lang="ts">
    import type { Snippet } from 'svelte';
    import { cn } from '$lib/utils';
    import { setSegmentDensity } from '$lib/components/Segment/segmentDensity';
    import DatasetSwitcher from './DatasetSwitcher/DatasetSwitcher.svelte';
    import SidebarFooter from './SidebarFooter/SidebarFooter.svelte';
    import SidebarNav from './SidebarNav/SidebarNav.svelte';
    import SidebarSelectionActions from './SidebarSelectionActions/SidebarSelectionActions.svelte';
    import type { SidebarNavItem } from './SidebarNav/buildSidebarNavItems';

    interface Props {
        datasetName: string;
        datasetHref: string;
        sampleCount: number | undefined;
        navItems: SidebarNavItem[];
        /**
         * Hides the sidebar without unmounting it. The filter groups run mount-time effects that
         * seed their stores, so a collapsed sidebar must still be in the tree after a reload.
         */
        collapsed: boolean;
        selectedCount: number;
        onClearSelection: () => void;
        onExportSelection: (() => void) | undefined;
        onMoreActions: (() => void) | undefined;
        /** Clears every sidebar filter at once. */
        onResetFilters: () => void;
        /** The route's filter groups, rendered inside the scrolling Filters section. */
        filters: Snippet;
    }

    const {
        datasetName,
        datasetHref,
        sampleCount,
        navItems,
        collapsed,
        selectedCount,
        onClearSelection,
        onExportSelection,
        onMoreActions,
        onResetFilters,
        filters
    }: Props = $props();

    // Every filter group below renders through `Segment`; switching density here rescales all
    // of them at once instead of threading a prop through each menu.
    setSegmentDensity('compact');
</script>

<aside
    class={cn(
        'h-full w-[264px] shrink-0 flex-col border-r border-border-hard bg-sidebar text-[13px]',
        collapsed ? 'hidden' : 'flex'
    )}
    aria-hidden={collapsed}
    data-testid="filter-panel-body"
>
    <DatasetSwitcher {datasetName} {sampleCount} href={datasetHref} />
    <SidebarNav items={navItems} />

    <div class="mx-3 border-t border-border-hard"></div>

    <div class="min-h-0 flex-1 overflow-y-auto px-1.5 pb-3 pt-2.5 dark:[color-scheme:dark]">
        <div class="mb-1 flex h-[22px] items-center justify-between px-2">
            <span class="text-[10.5px] font-bold uppercase tracking-[0.07em] text-muted-foreground">
                Filters
            </span>
            <button
                class="text-[11px] text-muted-foreground transition-colors hover:text-foreground"
                onclick={onResetFilters}
                data-testid="sidebar-filters-reset">Reset</button
            >
        </div>
        {@render filters()}
    </div>

    <SidebarSelectionActions
        {selectedCount}
        onClear={onClearSelection}
        onExport={onExportSelection}
        onMore={onMoreActions}
    />
    <SidebarFooter />
</aside>
