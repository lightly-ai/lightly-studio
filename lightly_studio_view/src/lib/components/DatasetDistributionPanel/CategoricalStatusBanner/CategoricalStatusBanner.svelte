<script lang="ts">
    import { Button } from '$lib/components';

    interface Props {
        loading?: boolean;
        error?: string;
        onRetry?: () => void;
    }

    const { loading, error, onRetry }: Props = $props();
</script>

{#if loading}
    <div class="mt-2 text-sm text-muted-foreground" role="status">Updating values…</div>
{:else if error}
    <div
        class="mt-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
        role="alert"
    >
        <div class="font-medium">Could not update categorical values</div>
        {#if onRetry}
            <Button
                variant="ghost"
                buttonProps={{
                    size: 'sm',
                    class: 'mt-2 h-8 px-2 text-sm',
                    onclick: onRetry
                }}
                ariaLabel="Retry categorical refresh"
            >
                Retry
            </Button>
        {/if}
    </div>
{/if}
