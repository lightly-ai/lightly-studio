<script lang="ts">
    import { STATUS_ACTION_LABELS, type StatusAction } from './treeStatus';

    interface Props {
        text: string;
        actions: StatusAction[];
        invalid: boolean;
        onAction: (action: StatusAction) => void;
    }

    let { text, actions, invalid, onAction }: Props = $props();
</script>

<p
    class="flex flex-wrap items-center gap-x-1 text-xs text-muted-foreground"
    data-testid="annotation-tree-status"
>
    {#if invalid}
        <span class="text-destructive">Invalid pattern</span>
    {:else}
        <span>{text}</span>
        {#each actions as action (action)}
            <span aria-hidden="true">·</span>
            <button
                type="button"
                class="underline-offset-2 hover:text-foreground hover:underline"
                onclick={() => onAction(action)}>{STATUS_ACTION_LABELS[action]}</button
            >
        {/each}
    {/if}
</p>
