<script lang="ts">
    import {
        Check as CheckIcon,
        ChevronsUpDown as ChevronsUpDownIcon,
        Info as InfoIcon
    } from '@lucide/svelte';
    import * as Command from '$lib/components/ui/command/index.js';
    import * as Popover from '$lib/components/ui/popover/index.js';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import ColorMarker from '$lib/components/SideMenu/ColorMarker/ColorMarker.svelte';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { cn } from '$lib/utils';

    // Not built on SelectList: it has no slot for a custom trigger or per-item colour swatch, and
    // it owns its selection + mutates its `items` on create — whereas our selection lives in the
    // shared context and the list is a query cache (new sources arrive via invalidation, not push).
    // TODO: reuse SelectList if it gains optional `trigger`/item-prefix slots + external selection.

    interface Props {
        collectionId: string;
    }

    let { collectionId }: Props = $props();

    // The backend default collection new annotations land in when no name is sent.
    const DEFAULT_SOURCE_NAME = 'annotation';

    const { context: annotationLabelContext, setAnnotationSource } = useAnnotationLabelContext();
    const { updateLastAnnotationSource } = useGlobalStorage();
    const annotationCollections = useAnnotationCollections(() => ({ collectionId }));

    const sourceNames = $derived(annotationCollections.data?.map((c) => c.name) ?? []);

    // The source new annotations are written to. Falls back to the conventional default
    // collection, then the first existing source, then the default.
    const effectiveSource = $derived(
        annotationLabelContext.annotationSource ??
            sourceNames.find((name) => name === DEFAULT_SOURCE_NAME) ??
            sourceNames[0] ??
            DEFAULT_SOURCE_NAME
    );

    // Merge the effective source so a just-typed (not yet persisted) source stays listed
    // and selected until the collections query refetches after the first annotation lands.
    const options = $derived([...new Set([...sourceNames, effectiveSource])]);

    // Seed the context with the displayed source once the list has loaded.
    $effect(() => {
        if (!annotationLabelContext.annotationSource && sourceNames.length > 0) {
            setAnnotationSource(effectiveSource);
        }
    });

    let open = $state(false);
    let inputValue = $state('');
    let highlightedValue = $state('');

    $effect(() => {
        if (!open) {
            inputValue = '';
            highlightedValue = '';
        }
    });

    const selectSource = (name: string) => {
        const trimmed = name.trim();
        if (!trimmed) return;
        setAnnotationSource(trimmed);
        updateLastAnnotationSource(collectionId, trimmed);
        open = false;
    };

    // Mirror SelectList: Enter with no highlighted item creates/selects the typed name.
    const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Enter' && !highlightedValue && inputValue.trim()) {
            selectSource(inputValue);
            event.preventDefault();
            event.stopPropagation();
        }
    };

    const canCreate = $derived(
        inputValue.trim().length > 0 && !options.includes(inputValue.trim())
    );
</script>

<div
    class="pointer-events-auto flex max-w-full items-center gap-1.5 rounded-lg bg-muted/80 px-2.5 py-1.5 text-sm shadow-md"
>
    <Popover.Root bind:open>
        <Popover.Trigger>
            {#snippet child({ props })}
                <button
                    {...props}
                    type="button"
                    class="flex min-w-0 items-center gap-1.5 whitespace-nowrap"
                    data-testid="annotation-source-pill-trigger"
                >
                    <span class="shrink-0 text-muted-foreground">Adding to</span>
                    <ColorMarker label={effectiveSource} />
                    <span class="min-w-0 truncate font-medium">{effectiveSource}</span>
                    <ChevronsUpDownIcon class="size-3.5 shrink-0 opacity-50" />
                </button>
            {/snippet}
        </Popover.Trigger>
        <Popover.Content class="w-[220px] p-0" side="top" align="start">
            <Command.Root bind:value={highlightedValue}>
                <Command.Input
                    placeholder="Search or create a source..."
                    onkeydown={handleKeyDown}
                    bind:value={inputValue}
                    data-testid="annotation-source-pill-input"
                />
                <Command.List class="dark:[color-scheme:dark]">
                    <Command.Group>
                        {#each options as name (name)}
                            <Command.Item
                                value={name}
                                onSelect={() => selectSource(name)}
                                data-testid={`annotation-source-pill-option-${name}`}
                            >
                                <CheckIcon
                                    class={cn(effectiveSource !== name && 'text-transparent')}
                                />
                                <ColorMarker label={name} />
                                <span class="min-w-0 flex-1 truncate">{name}</span>
                            </Command.Item>
                        {/each}
                    </Command.Group>
                    {#if canCreate}
                        <div class="border-t">
                            <Command.Item
                                value="__create__"
                                onSelect={() => selectSource(inputValue)}
                                forceMount
                                keywords={[]}
                                data-testid="annotation-source-pill-create"
                            >
                                <span class="opacity-50">Create:</span>
                                <span class="ml-1 font-semibold">{inputValue.trim()}</span>
                            </Command.Item>
                        </div>
                    {/if}
                </Command.List>
            </Command.Root>
        </Popover.Content>
    </Popover.Root>

    <div class="h-4 w-px shrink-0 bg-white/15"></div>

    <Tooltip
        content="The annotation will be associated with the selected annotation source."
        position="top"
        triggerClass="flex shrink-0 items-center"
        ariaLabel="Annotation source help"
    >
        <InfoIcon
            class="size-3.5 text-muted-foreground"
            aria-hidden="true"
            data-testid="annotation-source-pill-info"
        />
    </Tooltip>
</div>
