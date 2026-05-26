<script lang="ts">
    import { createQuery, useQueryClient } from '@tanstack/svelte-query';
    import { Button } from '$lib/components/ui/button';
    import { ChevronDown, ChevronUp, LoaderCircle, X } from '@lucide/svelte';
    import { toast } from 'svelte-sonner';
    import { dismissExecution } from '$lib/api/lightly_studio_local';
    import {
        listExecutionsOptions,
        listExecutionsQueryKey
    } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import {
        OperatorStatus,
        type OperatorExecutionResponse
    } from '$lib/api/lightly_studio_local';

    const POLL_INTERVAL_MS = 1000;
    const queryClient = useQueryClient();

    const executionsQuery = createQuery(() => ({
        ...listExecutionsOptions(),
        refetchInterval: (q: { state: { data?: OperatorExecutionResponse[] } }) => {
            const data = q.state.data ?? [];
            const hasRunning = data.some((r) => r.status === OperatorStatus.RUNNING);
            // Only poll while at least one execution is running, otherwise idle.
            return hasRunning ? POLL_INTERVAL_MS : false;
        }
    }));

    // Notify on transitions RUNNING -> done.
    const previousStatusById = new Map<string, OperatorStatus>();
    $effect(() => {
        const list = (executionsQuery.data ?? []) as OperatorExecutionResponse[];
        for (const rec of list) {
            const prev = previousStatusById.get(rec.execution_id);
            if (prev === OperatorStatus.RUNNING && rec.status !== OperatorStatus.RUNNING) {
                if (rec.status === OperatorStatus.ERROR) {
                    toast.error(`${rec.operator_name} failed`, {
                        description: rec.error_message || rec.result?.message || undefined
                    });
                } else {
                    toast.success(`${rec.operator_name} finished`, {
                        description: rec.result?.message || undefined
                    });
                }
                // Other queries may depend on the side-effects of the operator.
                queryClient.invalidateQueries();
            }
            previousStatusById.set(rec.execution_id, rec.status);
        }
    });

    const executions = $derived((executionsQuery.data ?? []) as OperatorExecutionResponse[]);
    const runningCount = $derived(
        executions.filter((r) => r.status === OperatorStatus.RUNNING).length
    );
    const hasAny = $derived(executions.length > 0);

    let minimized = $state(false);

    async function handleDismiss(id: string) {
        const response = await dismissExecution({ path: { execution_id: id } });
        if (response.error) {
            toast.error('Could not dismiss execution', {
                description: String(response.error)
            });
            return;
        }
        queryClient.invalidateQueries({ queryKey: listExecutionsQueryKey() });
    }

    function statusLabel(status: OperatorStatus): string {
        if (status === OperatorStatus.RUNNING) return 'Running';
        if (status === OperatorStatus.ERROR) return 'Failed';
        if (status === OperatorStatus.READY) return 'Succeeded';
        return status;
    }

    function statusClass(status: OperatorStatus): string {
        if (status === OperatorStatus.RUNNING)
            return 'bg-blue-500/15 text-blue-700 dark:text-blue-300';
        if (status === OperatorStatus.ERROR)
            return 'bg-destructive/15 text-destructive';
        return 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300';
    }
</script>

{#if hasAny}
    <div
        class="fixed bottom-4 right-4 z-50 w-80 overflow-hidden rounded-lg border border-border bg-background shadow-xl"
    >
        <button
            type="button"
            class="flex w-full items-center justify-between gap-2 border-b border-border bg-muted px-3 py-2 text-left text-sm font-medium"
            onclick={() => (minimized = !minimized)}
        >
            <span class="flex items-center gap-2">
                {#if runningCount > 0}
                    <LoaderCircle class="size-4 animate-spin text-blue-600" />
                {/if}
                <span>
                    Operators
                    {#if runningCount > 0}
                        ({runningCount} running)
                    {:else}
                        ({executions.length} finished)
                    {/if}
                </span>
            </span>
            {#if minimized}
                <ChevronUp class="size-4" />
            {:else}
                <ChevronDown class="size-4" />
            {/if}
        </button>

        {#if !minimized}
            <ul class="max-h-64 divide-y divide-border overflow-y-auto">
                {#each executions as rec (rec.execution_id)}
                    <li class="flex items-start gap-2 px-3 py-2 text-sm">
                        <div class="min-w-0 flex-1">
                            <div class="truncate font-medium" title={rec.operator_name}>
                                {rec.operator_name}
                            </div>
                            <div class="mt-1 flex items-center gap-2">
                                <span
                                    class="inline-flex items-center rounded-full px-2 py-0.5 text-xs {statusClass(
                                        rec.status
                                    )}"
                                >
                                    {statusLabel(rec.status)}
                                </span>
                            </div>
                            {#if rec.status !== OperatorStatus.RUNNING && (rec.result?.message || rec.error_message)}
                                <div
                                    class="mt-1 line-clamp-2 text-xs text-muted-foreground"
                                    title={rec.error_message || rec.result?.message || ''}
                                >
                                    {rec.error_message || rec.result?.message}
                                </div>
                            {/if}
                        </div>
                        {#if rec.status !== OperatorStatus.RUNNING}
                            <Button
                                variant="ghost"
                                size="icon"
                                class="size-6 shrink-0"
                                onclick={() => handleDismiss(rec.execution_id)}
                                aria-label="Dismiss"
                            >
                                <X class="size-3.5" />
                            </Button>
                        {/if}
                    </li>
                {/each}
            </ul>
        {/if}
    </div>
{/if}
