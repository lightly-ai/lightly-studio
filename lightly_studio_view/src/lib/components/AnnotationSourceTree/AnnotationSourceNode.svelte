<script lang="ts">
    import { ChevronRight } from '@lucide/svelte';
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

<div data-testid="annotation-source-node">
    <div class="group flex w-full items-center gap-2" data-testid="annotation-source-row">
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
        <span class="flex-1 truncate text-base font-medium">{node.name}</span>
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
        <div class="mt-1 space-y-1 pl-6">
            <AnnotationClassRows
                items={node.classes}
                {showClassColor}
                {showVisibilityToggle}
                onToggle={onTogglePair}
            />
        </div>
    {/if}
</div>
