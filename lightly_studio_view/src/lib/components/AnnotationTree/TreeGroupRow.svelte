<script lang="ts">
    import { ChevronRight, Database } from '@lucide/svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { cn } from '$lib/utils/shadcn';
    import OnlyButton from './OnlyButton.svelte';
    import TreeChildRow from './TreeChildRow.svelte';
    import TreeEye from './TreeEye.svelte';
    import { eyeState, tickState, type TreeBranch, type TreeLeaf } from './treeBranches';

    interface Props {
        branch: TreeBranch;
        open: boolean;
        onToggleOpen: () => void;
        onSetTicked: (leaves: TreeLeaf[], ticked: boolean) => void;
        onOnly: (leaves: TreeLeaf[]) => void;
        onSetVisible: (leaves: TreeLeaf[], visible: boolean) => void;
    }

    let { branch, open, onToggleOpen, onSetTicked, onOnly, onSetVisible }: Props = $props();

    const tick = $derived(tickState(branch.leaves));
    const eye = $derived(eyeState(branch.leaves));
    const isEmpty = $derived(branch.leaves.length === 0);
    const expanded = $derived(open && !isEmpty);
    const tickedCount = $derived(branch.leaves.filter((leaf) => leaf.ticked).length);
</script>

<div data-testid="annotation-tree-group">
    <div class="group flex w-full items-center gap-2 rounded-md bg-muted px-2 py-1.5">
        <button
            type="button"
            aria-label="{expanded ? 'Collapse' : 'Expand'} {branch.name}"
            aria-expanded={expanded}
            disabled={isEmpty}
            class="flex shrink-0 items-center disabled:opacity-30"
            onclick={onToggleOpen}
        >
            <ChevronRight class={cn('size-4 transition-transform', expanded && 'rotate-90')} />
        </button>
        <Checkbox
            checked={tick === 'on'}
            indeterminate={tick === 'partial'}
            aria-label={branch.name}
            disabled={isEmpty}
            onCheckedChange={() => onSetTicked(branch.leaves, tick !== 'on')}
        />
        {#if branch.isSource}
            <Database class="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        {/if}
        <span
            class={cn(
                'min-w-0 truncate text-sm font-medium',
                tick === 'off' && 'text-muted-foreground'
            )}
            title={branch.name}
            data-testid="annotation-tree-group-name">{branch.name}</span
        >
        {#if !expanded && tick === 'partial'}
            <span
                class="min-w-0 shrink-[1000] truncate text-xs text-muted-foreground"
                data-testid="annotation-tree-group-summary"
                >{tickedCount}/{branch.leaves.length}</span
            >
        {/if}
        <span class="flex-1"></span>
        {#if !isEmpty}
            <OnlyButton target={branch.name} onclick={() => onOnly(branch.leaves)} />
        {/if}
        {#if branch.count}
            <span class="shrink-0 whitespace-nowrap text-sm text-diffuse-foreground"
                >{branch.count}</span
            >
        {/if}
        {#if eye}
            <TreeEye
                {eye}
                target={branch.name}
                dimmed={tick === 'off'}
                onToggle={(visible) => onSetVisible(branch.leaves, visible)}
            />
        {/if}
    </div>
    {#if expanded}
        <!-- The guide line runs under the group checkbox. -->
        <div
            class="ml-10 mt-1 space-y-1 border-l border-foreground/30 pl-3 pr-2"
            data-testid="annotation-tree-children"
        >
            {#each branch.leaves as leaf (leaf.id)}
                <TreeChildRow
                    {leaf}
                    onToggle={() => onSetTicked([leaf], !leaf.ticked)}
                    onOnly={() => onOnly([leaf])}
                    onToggleEye={(visible) => onSetVisible([leaf], visible)}
                />
            {/each}
        </div>
    {/if}
</div>
