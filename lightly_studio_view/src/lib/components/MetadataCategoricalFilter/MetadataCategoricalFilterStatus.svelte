<script lang="ts">
    import { Button } from '$lib/components';

    interface Props {
        bucketCount: number;
        error?: string;
        onRetry?: () => void;
    }

    const { bucketCount, error, onRetry }: Props = $props();
</script>

{#if error}
    <div class="mt-1 flex items-center justify-between gap-2 text-xs text-destructive" role="alert">
        <span>
            {bucketCount === 0
                ? 'Could not load metadata distribution.'
                : 'Could not update metadata distribution.'}
        </span>
        {#if onRetry}
            <Button
                variant="ghost"
                buttonProps={{
                    size: 'sm',
                    type: 'button',
                    class: 'shrink-0 h-8 px-2 text-xs max-sm:min-h-11',
                    onclick: onRetry
                }}>Retry</Button
            >
        {/if}
    </div>
{/if}
