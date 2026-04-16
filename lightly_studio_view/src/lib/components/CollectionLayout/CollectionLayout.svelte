<script lang="ts">
    import type { Snippet } from 'svelte';
    import { GridHeader, SelectionPill } from '$lib/components';
    import Separator from '$lib/components/ui/separator/separator.svelte';
    import { PaneGroup, Pane, PaneResizer } from 'paneforge';
    import { GripVertical } from '@lucide/svelte';

    interface Props {
        showDetails: boolean;
        showLeftSidebar: boolean;
        showWithPlot: boolean;
        showGridHeader: boolean;
        showSelectionPill: boolean;
        selectedCount: number;
        onClearSelection: () => void;
        header?: Snippet;
        sidebar?: Snippet;
        searchBar?: Snippet;
        auxControls?: Snippet;
        plotPanel?: Snippet;
        fewShotDialogs?: Snippet;
        footer?: Snippet;
        children: Snippet;
    }

    let {
        showDetails,
        showLeftSidebar,
        showWithPlot,
        showGridHeader,
        showSelectionPill,
        selectedCount,
        onClearSelection,
        header,
        sidebar,
        searchBar,
        auxControls,
        plotPanel,
        fewShotDialogs,
        footer,
        children
    }: Props = $props();
</script>

<div class="flex-none">
    {@render header?.()}
</div>

<div class="relative flex min-h-0 flex-1 flex-col">
    {#if showDetails}
        {@render children()}
    {:else}
        <div class="flex min-h-0 flex-1 space-x-4 px-4">
            {#if showLeftSidebar}
                <div class="flex h-full min-h-0 w-80 flex-col">
                    <div class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card py-4">
                        <div
                            class="min-h-0 flex-1 space-y-2 overflow-y-auto px-4 pb-2 dark:[color-scheme:dark]"
                        >
                            {@render sidebar?.()}
                        </div>
                    </div>
                </div>
            {/if}

            {#if showWithPlot}
                <PaneGroup direction="horizontal" class="flex-1">
                    <Pane defaultSize={50} minSize={30} class="flex">
                        <div
                            class="relative flex flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4"
                        >
                            <GridHeader>
                                {@render searchBar?.()}
                            </GridHeader>
                            <Separator class="mb-4 bg-border-hard" />
                            <div class="flex min-h-0 flex-1 overflow-hidden">
                                {@render children()}
                            </div>
                            <SelectionPill {selectedCount} onClear={onClearSelection} />
                        </div>
                    </Pane>
                    <PaneResizer
                        class="relative mx-2 flex w-1 cursor-col-resize items-center justify-center"
                    >
                        <div class="bg-brand z-10 flex h-7 min-w-5 items-center justify-center">
                            <GripVertical class="text-diffuse-foreground" />
                        </div>
                    </PaneResizer>
                    <Pane defaultSize={50} minSize={30} class="flex min-h-0 flex-col">
                        {@render plotPanel?.()}
                    </Pane>
                </PaneGroup>
            {:else}
                <div class="relative flex flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4 pb-2">
                    {#if showGridHeader}
                        <GridHeader {auxControls}>
                            {@render searchBar?.()}
                        </GridHeader>
                        <Separator class="mb-4 bg-border-hard" />
                    {/if}
                    <div class="flex min-h-0 flex-1">
                        {@render children()}
                    </div>
                    {#if showSelectionPill}
                        <SelectionPill {selectedCount} onClear={onClearSelection} />
                    {/if}
                </div>
            {/if}

            {@render fewShotDialogs?.()}
        </div>
        {@render footer?.()}
    {/if}
</div>
