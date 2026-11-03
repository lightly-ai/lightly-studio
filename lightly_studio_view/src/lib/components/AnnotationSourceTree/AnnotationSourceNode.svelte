<script lang="ts">
    import { ChevronRight, Database } from '@lucide/svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import ColorMarker from '$lib/components/SideMenu/ColorMarker/ColorMarker.svelte';
    import AnnotationClassRows from './AnnotationClassRows.svelte';
    import SourceVisibilityToggle from './SourceVisibilityToggle.svelte';
    import type { buildSourceTree } from './buildSourceTree';

    interface Props {
        node: ReturnType<typeof buildSourceTree>[number];
        isHidden: boolean;
        showSourceColor: boolean;
        showClassColor: boolean;
        showVisibilityToggle: boolean;
        onToggleSource: (checked: boolean) => void;
        onTogglePair: (labelId: string) => void;
        onToggleVisibility: () => void;
    }

    let {
        node,
        isHidden,
        showSourceColor,
        showClassColor,
        showVisibilityToggle,
        onToggleSource,
        onTogglePair,
        onToggleVisibility
    }: Props = $props();

    const isEmpty = $derived(node.classes.length === 0);
    // A source starts open, an empty one collapsed, until the user clicks the chevron.
    let userOpen = $state<boolean | null>(null);
    const open = $derived(userOpen ?? !isEmpty);
</script>

<div class="mb-1" data-testid="annotation-source-node">
    <div
        class="group flex w-full items-center gap-2 rounded-md bg-muted px-2 py-1.5"
        data-testid="annotation-source-row"
    >
        <button
            type="button"
            aria-label="{open ? 'Collapse' : 'Expand'} {node.name}"
            aria-expanded={open && !isEmpty}
            disabled={isEmpty}
            class="flex shrink-0 items-center disabled:opacity-30"
            onclick={() => (userOpen = !open)}
        >
            <ChevronRight
                class="size-4 transition-transform {open && !isEmpty ? 'rotate-90' : ''}"
            />
        </button>
        <Checkbox
            checked={node.state === 'checked'}
            indeterminate={node.state === 'partial'}
            aria-label={node.name}
            disabled={isEmpty}
            onCheckedChange={() => onToggleSource(node.state !== 'checked')}
        />
        {#if showSourceColor}
            <ColorMarker label={node.name} />
        {/if}
        <Database class="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <span class="truncate text-base font-medium">{node.name}</span>
        <span class="flex-1 text-xs text-muted-foreground" data-testid="annotation-source-caption"
            >source</span
        >
        {#if node.count}
            <span class="text-sm text-diffuse-foreground" data-testid="annotation-source-count"
                >{node.count}</span
            >
        {/if}
        {#if showVisibilityToggle}
            <SourceVisibilityToggle
                {isHidden}
                sourceName={node.name}
                onToggle={onToggleVisibility}
            />
        {/if}
    </div>
    {#if open && !isEmpty}
        <div class="ml-4 mt-1 space-y-1 border-l border-border pl-3">
            <AnnotationClassRows
                items={node.classes}
                {showClassColor}
                {showVisibilityToggle}
                onToggle={onTogglePair}
            />
        </div>
    {/if}
</div>
