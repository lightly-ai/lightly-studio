<script lang="ts">
    import type { Snippet } from 'svelte';
    import { PanelLeftClose, SlidersHorizontal } from '@lucide/svelte';
    import Button from '$lib/components/Button/Button.svelte';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { cn } from '$lib/utils/shadcn';
    import { useGlobalStorage } from '$lib/hooks';

    interface Props {
        /** Filter controls rendered inside the expanded panel body. */
        children: Snippet;
    }

    const { children }: Props = $props();

    const { filterPanelCollapsed, toggleFilterPanelCollapsed } = useGlobalStorage();
</script>

<div class={cn('flex h-full min-h-0 flex-col', $filterPanelCollapsed ? 'w-14' : 'w-80')}>
    {#if $filterPanelCollapsed}
        <div class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card p-1.5">
            <Tooltip content="Show filters" position="right" triggerClass="w-full" class="w-max">
                <button
                    type="button"
                    class={cn(
                        'flex aspect-square w-full flex-col items-center justify-center gap-0.5 rounded-md p-1.5 text-[10px] font-medium transition-colors',
                        'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                    )}
                    data-testid="filter-panel-expand"
                    aria-label="Show filters"
                    aria-expanded={false}
                    onclick={toggleFilterPanelCollapsed}
                >
                    <SlidersHorizontal class="size-4" />
                    <span>Filters</span>
                </button>
            </Tooltip>
        </div>
    {/if}

    <!-- Kept mounted (only visually hidden) while collapsed so the filter children run
         their initialization effects on load — e.g. AnnotationCollectionsMenu seeding the
         selected annotation sources. -->
    <div
        data-testid="filter-panel-body"
        class={cn(
            'min-h-0 flex-1 flex-col rounded-[1vw] bg-card py-4',
            $filterPanelCollapsed ? 'hidden' : 'flex'
        )}
    >
        <div class="min-h-0 flex-1 space-y-2 overflow-y-auto px-4 pb-2 dark:[color-scheme:dark]">
            <h2 class="flex items-center justify-between py-2 text-lg font-semibold">
                <span class="flex items-center space-x-2">
                    <SlidersHorizontal class="size-5" />
                    <span>Filters</span>
                </span>
                <Tooltip content="Hide filters" position="bottom" class="w-max">
                    <Button
                        variant="ghost"
                        icon={PanelLeftClose}
                        ariaLabel="Hide filters"
                        buttonProps={{
                            onclick: toggleFilterPanelCollapsed,
                            'aria-expanded': true,
                            'data-testid': 'filter-panel-collapse'
                        }}
                    />
                </Tooltip>
            </h2>

            {@render children()}
        </div>
    </div>
</div>
