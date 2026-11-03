<script lang="ts">
    import { Eye, EyeOff, Filter, Plus } from '@lucide/svelte';
    import { FilterActionButton } from '$lib/components/FilterActionButton';
    import { STATUS_ACTION_LABELS, type StatusAction } from './treeStatus';

    interface Props {
        text: string;
        actions: StatusAction[];
        invalid: boolean;
        onAction: (action: StatusAction) => void;
    }

    let { text, actions, invalid, onAction }: Props = $props();

    const ICONS = { showOnly: Filter, add: Plus, hide: EyeOff, showAll: Eye, hideAll: EyeOff };
</script>

<div
    class="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground"
    data-testid="annotation-tree-status"
>
    {#if invalid}
        <span class="text-destructive">Invalid pattern</span>
    {:else}
        <span class="mr-0.5">{text}</span>
        {#each actions as action (action)}
            <FilterActionButton
                label={STATUS_ACTION_LABELS[action]}
                icon={ICONS[action]}
                onclick={() => onAction(action)}
            />
        {/each}
    {/if}
</div>
