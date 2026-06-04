<script lang="ts">
    import Spinner from '$lib/components/Spinner/Spinner.svelte';
    import { useOperatorsDialog } from '$lib/hooks';

    const { isPluginExecuting } = useOperatorsDialog();
</script>

{#if $isPluginExecuting}
    <div
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/50"
        aria-modal="true"
        role="dialog"
        aria-label="Plugin executing"
    >
        <div class="flex flex-col items-center gap-4 rounded-lg bg-background p-8 shadow-lg">
            <Spinner size="large" />
            <p class="text-sm text-foreground">
                Plugin executing. This might take up to several minutes…
            </p>
        </div>
    </div>
{/if}
