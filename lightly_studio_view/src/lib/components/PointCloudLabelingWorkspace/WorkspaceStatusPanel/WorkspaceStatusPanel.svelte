<script lang="ts">
    interface Props {
        status: 'loading' | 'unsupported' | 'error';
        onExit?: () => void;
        onRetry?: () => void;
    }

    let { status, onExit, onRetry }: Props = $props();
</script>

<div
    role={status === 'error' ? 'alert' : 'status'}
    data-testid="workspace-status-panel"
    data-status={status}
>
    {#if status === 'loading'}
        <p>Loading…</p>
    {:else if status === 'unsupported'}
        <p>This view is not supported.</p>
    {:else if status === 'error'}
        <p>Something went wrong.</p>
    {/if}
    {#if status === 'error' && onRetry}
        <button onclick={onRetry}>Retry</button>
    {/if}
    {#if onExit}
        <button onclick={onExit}>Exit</button>
    {/if}
</div>
