<script lang="ts">
    import { ChevronRight, Database } from '@lucide/svelte';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import { useColorPicker } from '$lib/hooks';
    import AnnotationClassRows from './AnnotationClassRows.svelte';
    import SourceVisibilityToggle from './SourceVisibilityToggle.svelte';
    import type { buildSourceTree } from './buildSourceTree';

    interface Props {
        node: ReturnType<typeof buildSourceTree>[number];
        isHidden: boolean;
        showSourceColor: boolean;
        showClassColor: boolean;
        /** Opens the source while a search is active, whatever the user chose. */
        forceOpen?: boolean;
        /** Highlights the match of this text in the class names. */
        highlight?: string;
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
        forceOpen = false,
        highlight = '',
        showVisibilityToggle,
        onToggleSource,
        onTogglePair,
        onToggleVisibility
    }: Props = $props();

    const picker = useColorPicker(() => node.name);
    const isEmpty = $derived(node.classes.length === 0);
    // A source starts open, an empty one collapsed, until the user clicks the chevron.
    let userOpen = $state<boolean | null>(null);
    const open = $derived(forceOpen || (userOpen ?? !isEmpty));
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
        <span class="shrink-0" title="Annotation source">
            <Database
                class="size-4 {showSourceColor ? '' : 'text-muted-foreground'}"
                style={showSourceColor ? `color: ${picker.borderColor}` : undefined}
                aria-hidden="true"
            />
        </span>
        <span class="min-w-0 flex-1 truncate text-base font-medium">{node.name}</span>
        {#if node.count}
            <span
                class="shrink-0 whitespace-nowrap text-sm text-diffuse-foreground"
                data-testid="annotation-source-count">{node.count}</span
            >
        {/if}
        {#if showVisibilityToggle}
            <span class="flex size-4 shrink-0 items-center justify-center">
                <SourceVisibilityToggle
                    {isHidden}
                    sourceName={node.name}
                    onToggle={onToggleVisibility}
                />
            </span>
        {/if}
    </div>
    {#if open && !isEmpty}
        <div class="ml-4 mt-1 space-y-1 border-l border-foreground/30 pl-3 pr-2">
            <AnnotationClassRows
                items={node.classes}
                {showClassColor}
                {highlight}
                {showVisibilityToggle}
                onToggle={onTogglePair}
            />
        </div>
    {/if}
</div>
