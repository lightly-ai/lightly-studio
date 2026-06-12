<script lang="ts">
    import { cn } from '$lib/utils/shadcn';
    import { useGlobalStorage } from '$lib/hooks';
    import { ChartNetwork, Gauge, SearchCode } from '@lucide/svelte';

    type PanelType = Parameters<ReturnType<typeof useGlobalStorage>['setActivePanel']>[0];

    interface Props {
        isImages: boolean;
        hasMediaWithEmbeddings: boolean;
        hasEvaluationRuns: boolean;
    }
    const { isImages, hasMediaWithEmbeddings, hasEvaluationRuns }: Props = $props();

    const { activePanel, setActivePanel } = useGlobalStorage();

    function toggle(panel: PanelType) {
        setActivePanel($activePanel === panel ? 'none' : panel);
    }
</script>

<div class="flex w-14 flex-col gap-2 rounded-xl bg-card p-1.5">
    {#if hasMediaWithEmbeddings}
        <button
            class={cn(
                'flex aspect-square w-full flex-col items-center justify-center gap-0.5 rounded-md p-1.5 text-[10px] font-medium transition-colors',
                $activePanel === 'embeddingPlot'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
            )}
            data-testid="right-rail-embed"
            aria-label="Embeddings"
            aria-pressed={$activePanel === 'embeddingPlot'}
            onclick={() => toggle('embeddingPlot')}
        >
            <ChartNetwork class="size-4" />
            <span>Embed</span>
        </button>
    {/if}
    {#if isImages}
        <button
            class={cn(
                'flex aspect-square w-full flex-col items-center justify-center gap-0.5 rounded-md p-1.5 text-[10px] font-medium transition-colors',
                $activePanel === 'queryEditor'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
            )}
            data-testid="right-rail-query"
            aria-label="Query"
            aria-pressed={$activePanel === 'queryEditor'}
            onclick={() => toggle('queryEditor')}
        >
            <SearchCode class="size-4" />
            <span>Query</span>
        </button>
    {/if}
    {#if hasEvaluationRuns}
        <button
            class={cn(
                'flex aspect-square w-full flex-col items-center justify-center gap-0.5 rounded-md p-1.5 text-[10px] font-medium transition-colors',
                $activePanel === 'evaluationRuns'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
            )}
            data-testid="right-rail-eval"
            aria-label="Evaluation"
            aria-pressed={$activePanel === 'evaluationRuns'}
            onclick={() => toggle('evaluationRuns')}
        >
            <Gauge class="size-4" />
            <span>Eval</span>
        </button>
    {/if}
</div>
