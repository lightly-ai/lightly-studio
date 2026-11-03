<script lang="ts">
    import { cn } from '$lib/utils';
    import { Plus } from '@lucide/svelte';

    interface Props {
        name: string;
        // The row is the only match, so Enter adds the class.
        isEnterTarget: boolean;
        onAdd: () => void;
    }

    const { name, isEnterTarget, onAdd }: Props = $props();
</script>

<li class={cn(!isEnterTarget && 'mt-1 border-t border-border/40 pt-1')}>
    <button
        type="button"
        class={cn(
            'flex h-10 w-full items-center gap-3 rounded-md px-2 text-left text-sm hover:bg-accent',
            isEnterTarget ? 'bg-accent/50' : 'text-muted-foreground hover:text-foreground'
        )}
        onclick={onAdd}
    >
        <Plus class="size-3 shrink-0 text-primary" />
        <span class="min-w-0 flex-1 truncate">
            Add new annotation class
            <span class="font-medium text-foreground">"{name}"</span>
        </span>
        {#if isEnterTarget}
            <kbd class="rounded border border-border px-1.5 text-xs text-muted-foreground"
                >Enter</kbd
            >
        {/if}
    </button>
</li>
