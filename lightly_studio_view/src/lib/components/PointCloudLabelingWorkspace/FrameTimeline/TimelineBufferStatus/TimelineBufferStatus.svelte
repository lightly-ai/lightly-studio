<script lang="ts">
    import { LoaderCircle } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';

    interface Props {
        status?: {
            isWaiting: boolean;
            failedCount: number;
            isRetrying: boolean;
            onRetry: () => Promise<void>;
        };
    }

    let { status }: Props = $props();
</script>

{#if status && (status.isWaiting || status.failedCount > 0 || status.isRetrying)}
    <span role="status" class="flex items-center gap-1.5 text-xs text-muted-foreground">
        {#if status.isRetrying || (status.isWaiting && status.failedCount === 0)}
            <LoaderCircle
                class="h-3 w-3 animate-spin motion-reduce:animate-none"
                aria-hidden="true"
            />
            {status.isRetrying ? 'Retrying failed frames…' : 'Buffering…'}
        {:else}
            {status.failedCount}
            {status.failedCount === 1 ? 'frame failed' : 'frames failed'} to load.
        {/if}
    </span>
    {#if status.failedCount > 0}
        <Button
            variant="outline"
            size="sm"
            class="h-6 text-xs"
            disabled={status.isRetrying}
            onclick={status.onRetry}
        >
            Retry failed frames
        </Button>
    {/if}
{/if}
