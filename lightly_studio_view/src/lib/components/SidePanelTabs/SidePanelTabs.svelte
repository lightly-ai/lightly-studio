<script lang="ts">
    import { cn } from '$lib/utils/shadcn';
    import { useGlobalStorage } from '$lib/hooks';
    import { ChartColumn, ChartNetwork, Gauge, SearchCode } from '@lucide/svelte';
    import { Tooltip } from '$lib/components/ui/tooltip';

    type PanelType = Parameters<ReturnType<typeof useGlobalStorage>['setActivePanel']>[0];

    interface Props {
        isImages: boolean;
        hasMediaWithEmbeddings: boolean;
        supportsEvaluation: boolean;
    }
    const { isImages, hasMediaWithEmbeddings, supportsEvaluation }: Props = $props();

    const { activePanel, setActivePanel } = useGlobalStorage();

    function toggle(panel: PanelType) {
        setActivePanel($activePanel === panel ? 'none' : panel);
    }
</script>

<div class="flex w-14 flex-col gap-2 rounded-xl bg-card p-1.5">
    {#if hasMediaWithEmbeddings}
        <Tooltip
            content="Explore the embedding space"
            position="left"
            triggerClass="w-full"
            class="w-max"
        >
            <button
                class={cn(
                    'flex aspect-square w-full flex-col items-center justify-center gap-0.5 rounded-md p-1.5 text-[10px] font-medium transition-colors',
                    $activePanel === 'embeddingPlot'
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
                data-testid="side-panel-tabs-embed"
                aria-label="Embeddings"
                aria-pressed={$activePanel === 'embeddingPlot'}
                onclick={() => toggle('embeddingPlot')}
            >
                <ChartNetwork class="size-4" />
                <span>Embed</span>
            </button>
        </Tooltip>
    {/if}
    {#if isImages}
        <Tooltip
            content="Write a query expression to filter your dataset"
            position="left"
            triggerClass="w-full"
            class="w-max"
        >
            <button
                class={cn(
                    'flex aspect-square w-full flex-col items-center justify-center gap-0.5 rounded-md p-1.5 text-[10px] font-medium transition-colors',
                    $activePanel === 'queryEditor'
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
                data-testid="side-panel-tabs-query"
                aria-label="Query"
                aria-pressed={$activePanel === 'queryEditor'}
                onclick={() => toggle('queryEditor')}
            >
                <SearchCode class="size-4" />
                <span>Query</span>
            </button>
        </Tooltip>
    {/if}
    {#if supportsEvaluation}
        <Tooltip
            content="Review evaluation run results"
            position="left"
            triggerClass="w-full"
            class="w-max"
        >
            <button
                class={cn(
                    'flex aspect-square w-full flex-col items-center justify-center gap-0.5 rounded-md p-1.5 text-[10px] font-medium transition-colors',
                    $activePanel === 'evaluationRuns'
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
                data-testid="side-panel-tabs-eval"
                aria-label="Evaluation"
                aria-pressed={$activePanel === 'evaluationRuns'}
                onclick={() => toggle('evaluationRuns')}
            >
                <Gauge class="size-4" />
                <span>Eval</span>
            </button>
        </Tooltip>
    {/if}
    {#if isImages}
        <Tooltip
            content="View dataset distribution"
            position="left"
            triggerClass="w-full"
            class="w-max"
        >
            <button
                class={cn(
                    'flex aspect-square w-full flex-col items-center justify-center gap-0.5 rounded-md p-1.5 text-[10px] font-medium transition-colors',
                    $activePanel === 'distribution'
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
                data-testid="side-panel-tabs-distribution"
                aria-label="Distribution"
                aria-pressed={$activePanel === 'distribution'}
                onclick={() => toggle('distribution')}
            >
                <ChartColumn class="size-4" />
                <span>Distr</span>
            </button>
        </Tooltip>
    {/if}
</div>
