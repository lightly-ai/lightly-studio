<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { cn } from '$lib/utils/shadcn';
    import OnlyButton from './OnlyButton.svelte';
    import TreeEye from './TreeEye.svelte';
    import type { TreeLeaf } from './treeBranches';

    interface Props {
        leaf: TreeLeaf;
        onToggle: () => void;
        onOnly: () => void;
        onToggleEye: (visible: boolean) => void;
    }

    let { leaf, onToggle, onOnly, onToggleEye }: Props = $props();

    const rowId = $props.id();
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
        data-testid="annotation-tree-row-name">{leaf.label}</label
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
