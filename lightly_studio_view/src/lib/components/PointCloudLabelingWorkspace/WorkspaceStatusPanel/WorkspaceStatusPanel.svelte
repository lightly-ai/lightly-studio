<script lang="ts">
    interface Props {
        status: 'loading' | 'unsupported' | 'error';
        onExit?: () => void;
        onRetry?: () => void;
    }

    let { status, onExit, onRetry }: Props = $props();
</script>

<div data-testid="workspace-status-panel" data-status={status}>
    {#if status === 'error' && onRetry}
        <button onclick={onRetry}>Retry</button>
    {/if}
    {#if onExit}
        <button onclick={onExit}>Exit</button>
    {/if}
</div>
