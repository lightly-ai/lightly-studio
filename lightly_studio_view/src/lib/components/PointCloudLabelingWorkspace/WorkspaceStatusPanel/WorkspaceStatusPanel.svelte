<script lang="ts">
    import { AlertTriangle, Loader2, RotateCw } from '@lucide/svelte';
    import { Button } from '$lib/components';

    /**
     * Shared placeholder body for every non-`ready` state the workspace can be in.
     * `loading` covers both the lazy chunk import and (once wired up) the initial frame
     * fetch; `unsupported` is a sample/collection the workspace cannot open at all; `empty`
     * is an eligible MCAP sample with no decodable point-cloud frames; `error` is a
     * recoverable failure (chunk load, future frame fetch) with a retry action.
     */
    interface Props {
        status: 'loading' | 'unsupported' | 'empty' | 'error';
        onRetry?: () => void;
        onExit?: () => void;
    }

    let { status, onRetry, onExit }: Props = $props();

    const copy: Record<typeof status, { title: string; description: string }> = {
        loading: {
            title: 'Loading labeling workspace…',
            description: 'Setting up the 3D scene and point-cloud data.'
        },
        unsupported: {
            title: 'This sample can’t be opened here',
            description: 'The point-cloud labeling workspace only supports eligible MCAP samples.'
        },
        empty: {
            title: 'No point-cloud frames yet',
            description: 'This recording has no frames available to label.'
        },
        error: {
            title: 'Something went wrong',
            description: 'The labeling workspace failed to load.'
        }
    };
</script>

<div
    class="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center"
    data-testid="workspace-status-panel"
    data-status={status}
>
    {#if status === 'loading'}
        <Loader2 class="size-8 animate-spin text-muted-foreground" aria-hidden="true" />
    {:else if status === 'error' || status === 'unsupported'}
        <AlertTriangle class="size-8 text-destructive" aria-hidden="true" />
    {/if}
    <p class="text-sm font-medium">{copy[status].title}</p>
    <p class="max-w-sm text-sm text-muted-foreground">{copy[status].description}</p>
    <div class="mt-2 flex gap-2">
        {#if status === 'error' && onRetry}
            <Button icon={RotateCw} variant="outline" buttonProps={{ onclick: onRetry }}>
                Retry
            </Button>
        {/if}
        {#if onExit}
            <Button variant="ghost" buttonProps={{ onclick: onExit }}>Back to samples</Button>
        {/if}
    </div>
</div>
