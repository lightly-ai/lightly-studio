<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { cn } from '$lib/utils/shadcn';
    import HighlightedText from './HighlightedText.svelte';
    import OnlyButton from './OnlyButton.svelte';
    import TreeEye from './TreeEye.svelte';
    import type { TreeLeaf } from './treeBranches';
    import type { MatchRange } from './treeSearch';

    interface Props {
        leaf: TreeLeaf;
        find?: ((text: string) => MatchRange | null) | null;
        onToggle: () => void;
        onOnly: () => void;
        onToggleEye: (visible: boolean) => void;
    }

    let { leaf, find = null, onToggle, onOnly, onToggleEye }: Props = $props();

    const rowId = $props.id();
    // "No annotations" rows are not searched.
    const range = $derived(find && leaf.pairs.length > 0 ? find(leaf.label) : null);
</script>

<div
    class="group flex w-full items-center gap-2"
    title={leaf.label}
    data-testid="annotation-tree-row"
>
    <Checkbox
        id={rowId}
        checked={leaf.ticked}
        aria-label={leaf.ariaLabel}
        onCheckedChange={onToggle}
    />
    <label
        for={rowId}
        class={cn(
            'min-w-0 flex-1 cursor-pointer truncate text-sm',
            !leaf.ticked && 'text-muted-foreground'
        )}
        data-testid="annotation-tree-row-name"><HighlightedText text={leaf.label} {range} /></label
    >
    <OnlyButton target={leaf.ariaLabel} onclick={onOnly} />
    {#if leaf.count}
        <span class="shrink-0 whitespace-nowrap text-sm text-diffuse-foreground">{leaf.count}</span>
    {/if}
    {#if leaf.visible !== undefined}
        <TreeEye
            eye={leaf.visible ? 'on' : 'off'}
            target={leaf.ariaLabel}
            dimmed={!leaf.ticked}
            onToggle={onToggleEye}
        />
    {/if}
</div>
