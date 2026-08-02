<script lang="ts">
    import Spinner from '$lib/components/Spinner/Spinner.svelte';
    import { Progress } from '$lib/components/ui/progress';
    import { useOperatorsDialog } from '$lib/hooks';

    const { isPluginExecuting, pluginProgress } = useOperatorsDialog();

    // Plugins report a total of 0 until they know how much work there is.
    const hasProgress = $derived($pluginProgress !== null && $pluginProgress.total > 0);
    const percent = $derived(
        hasProgress && $pluginProgress
            ? Math.round(($pluginProgress.current / $pluginProgress.total) * 100)
            : 0
    );
</script>

{#if $isPluginExecuting}
    <div
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50"
        aria-modal="true"
        role="dialog"
        aria-label="Plugin executing"
    >
        <div class="flex flex-col items-center gap-4 rounded-lg bg-background p-8 shadow-lg">
            {#if hasProgress && $pluginProgress}
                <div class="flex w-72 flex-col gap-2">
                    <div class="flex items-baseline justify-between">
                        <p class="text-sm text-foreground">
                            {$pluginProgress.description || 'Plugin executing'}
                        </p>
                        <span class="text-sm font-medium text-foreground">{percent}%</span>
                    </div>
                    <Progress value={percent} aria-label="Plugin execution progress" />
                    <p class="text-xs text-muted-foreground">
                        {$pluginProgress.current} / {$pluginProgress.total} samples
                    </p>
                </div>
            {:else}
                <Spinner size="large" />
                <p class="text-sm text-foreground">
                    Plugin executing. This might take up to several minutes…
                </p>
            {/if}
        </div>
    </div>
{/if}
