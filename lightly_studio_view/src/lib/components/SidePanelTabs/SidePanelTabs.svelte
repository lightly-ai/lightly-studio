<script lang="ts">
    import { cn } from '$lib/utils/shadcn';
    import { ChartColumn, ChartNetwork, Gauge, SearchCode } from '@lucide/svelte';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { useSidePanelTabs } from './useSidePanelTabs';
    import type { PanelType } from '$lib/hooks/useGlobalStorage';
    import type { Component } from 'svelte';

    interface Props {
        collectionId: string;
        isImages: boolean;
        hasMediaWithEmbeddings: boolean;
        supportsEvaluation: boolean;
        /**
         * Called after a panel is activated from a route that cannot host it (a detail view).
         * Use it to return to the grid, where the panel is rendered.
         */
        onLeaveDetails?: () => void;
    }
    const {
        collectionId,
        isImages,
        hasMediaWithEmbeddings,
        supportsEvaluation,
        onLeaveDetails
    }: Props = $props();

    const { activePanel, toggle } = useSidePanelTabs({ getCollectionId: () => collectionId });

    interface RailItem {
        panel: PanelType;
        label: string;
        ariaLabel: string;
        tooltip: string;
        icon: Component;
        testId: string;
        enabled: boolean;
    }

    const items = $derived.by<RailItem[]>(() =>
        (
            [
                {
                    panel: 'embeddingPlot',
                    label: 'Embed',
                    ariaLabel: 'Embeddings',
                    tooltip: 'Explore the embedding space',
                    icon: ChartNetwork,
                    testId: 'side-panel-tabs-embed',
                    enabled: hasMediaWithEmbeddings
                },
                {
                    panel: 'queryEditor',
                    label: 'Query',
                    ariaLabel: 'Query',
                    tooltip: 'Write a query expression to filter your dataset',
                    icon: SearchCode,
                    testId: 'side-panel-tabs-query',
                    enabled: isImages
                },
                {
                    panel: 'evaluationRuns',
                    label: 'Eval',
                    ariaLabel: 'Evaluation',
                    tooltip: 'Review evaluation run results',
                    icon: Gauge,
                    testId: 'side-panel-tabs-eval',
                    enabled: supportsEvaluation
                },
                {
                    panel: 'distribution',
                    label: 'Distr',
                    ariaLabel: 'Distribution',
                    tooltip: 'View dataset distribution',
                    icon: ChartColumn,
                    testId: 'side-panel-tabs-distribution',
                    enabled: isImages
                }
            ] satisfies RailItem[]
        ).filter((item) => item.enabled)
    );
</script>

<div
    class="flex w-[62px] shrink-0 flex-col items-center gap-1 border-l border-border-hard bg-sidebar py-1.5"
>
    {#each items as item (item.panel)}
        {@const Icon = item.icon}
        {@const isActive = $activePanel === item.panel}
        <Tooltip content={item.tooltip} position="left" triggerClass="w-[50px]" class="w-max">
            <button
                class={cn(
                    'flex h-[50px] w-[50px] flex-col items-center justify-center gap-1 rounded-lg text-[9.5px] transition-colors',
                    isActive
                        ? 'bg-sidebar-accent text-foreground'
                        : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground'
                )}
                data-testid={item.testId}
                aria-label={item.ariaLabel}
                aria-pressed={isActive}
                onclick={() => {
                    toggle($activePanel, item.panel);
                    onLeaveDetails?.();
                }}
            >
                <Icon class="size-[17px]" />
                <span>{item.label}</span>
            </button>
        </Tooltip>
    {/each}
</div>
