<script lang="ts">
    import type { EvaluationRunView } from '$lib/api/lightly_studio_local/types.gen';
    import { Typography } from '$lib/components';
    import { formatDate } from '$lib/utils';
    import { ChevronDown, ChevronRight } from '@lucide/svelte';

    interface Props {
        // The evaluation run to display.
        run: EvaluationRunView;
        // Whether the details section is expanded.
        expanded: boolean;
        // Callback to toggle the expanded state.
        onToggle: () => void;
    }

    const { run, expanded, onToggle }: Props = $props();

    const formatConfigValue = (value: unknown): string => {
        if (value === null || value === undefined) return '—';
        if (typeof value === 'object') return JSON.stringify(value);
        return String(value);
    };

    const configEntries = $derived(Object.entries(run.evaluation_run_configuration ?? {}));
</script>

<li class="rounded-md border border-border bg-background">
    <button
        type="button"
        class="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-muted/50"
        onclick={onToggle}
        data-testid="evaluation-run-item"
        aria-expanded={expanded}
    >
        <div class="min-w-0 flex-1">
            <Typography
                variant="subtitle2"
                className="truncate"
                props={{ 'data-testid': 'evaluation-run-name' }}
            >
                {run.name}
            </Typography>
            <Typography
                variant="caption"
                className="text-muted-foreground"
                props={{ 'data-testid': 'evaluation-run-date' }}
            >
                {formatDate(run.created_at)}
            </Typography>
        </div>
        {#if expanded}
            <ChevronDown class="size-4 shrink-0" />
        {:else}
            <ChevronRight class="size-4 shrink-0" />
        {/if}
    </button>
    {#if expanded}
        <div class="border-t border-border px-3 py-3" data-testid="evaluation-run-details">
            <section>
                <Typography variant="subtitle2" component="h3" className="mb-2">
                    Configuration
                </Typography>
                {#if configEntries.length === 0}
                    <Typography variant="body2" className="text-muted-foreground">
                        No configuration recorded.
                    </Typography>
                {:else}
                    <dl
                        class="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1"
                        data-testid="evaluation-run-config"
                    >
                        {#each configEntries as [key, value] (key)}
                            <Typography
                                variant="body2"
                                component="dt"
                                className="text-muted-foreground"
                            >
                                {key}
                            </Typography>
                            <Typography variant="body2" component="dd" className="break-words">
                                {formatConfigValue(value)}
                            </Typography>
                        {/each}
                    </dl>
                {/if}
            </section>
            <section class="mt-4">
                <Typography variant="subtitle2" component="h3" className="mb-2">Metrics</Typography>
                <Typography variant="body2" className="text-muted-foreground">
                    Metrics not yet available — backend support pending.
                </Typography>
            </section>
        </div>
    {/if}
</li>
