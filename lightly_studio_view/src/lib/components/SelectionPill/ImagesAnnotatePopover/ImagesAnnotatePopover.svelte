<script lang="ts">
    import { Tags } from '@lucide/svelte';
    import { useQueryClient } from '@tanstack/svelte-query';
    import { untrack } from 'svelte';
    import { get } from 'svelte/store';
    import { toast } from 'svelte-sonner';
    import { page } from '$app/state';
    import { deleteForSamples } from '$lib/api/lightly_studio_local';
    import { Button } from '$lib/components/ui/button';
    import * as Command from '$lib/components/ui/command';
    import * as Dialog from '$lib/components/ui/dialog';
    import * as Popover from '$lib/components/ui/popover';
    import {
        useAnnotationCollections,
        useAnnotationCollectionsFilter,
        useBulkCreateClassifications,
        useGlobalStorage
    } from '$lib/hooks';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import {
        getTargetBlockedReason,
        resolveTargetSource
    } from '$lib/hooks/useAnnotationTarget/resolveTargetSource';
    import {
        useImageAnnotationCounts,
        useImageAnnotationCountsQueryKey
    } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
    import { getImagesInfiniteQueryKeyPrefix } from '$lib/hooks/useImagesInfinite/createImagesInfiniteOptions';
    import { getSelectionTarget } from '$lib/hooks/useSelectionTarget/useSelectionTarget';
    import SelectionCountRow from '../SelectionCountRow/SelectionCountRow.svelte';
    import AnnotateSourceMenu from './AnnotateSourceMenu.svelte';
    import {
        buildSelectionCountsFilter,
        formatDeleteConfirm,
        numberKeyIndex
    } from './imagesAnnotatePopover.helpers';
    import {
        readRememberedSource,
        rememberSource,
        usableRememberedSource
    } from './rememberedSource';

    interface Props {
        collectionId: string;
        selectedCount: number;
        open: boolean;
        onOpenChange: (open: boolean) => void;
        /** The key that opens this menu, shown on the trigger. */
        shortcutHint?: string;
    }
    let { collectionId, selectedCount, open, onOpenChange, shortcutHint }: Props = $props();

    const client = useQueryClient();
    const { addClass } = useBulkCreateClassifications();
    const { isSourceVisible } = useAnnotationCollectionsFilter();
    const { getSelectedSampleIds, getSelectAllSnapshot } = useGlobalStorage();
    const sourcesQuery = useAnnotationCollections(() => ({ collectionId }));
    const labelsQuery = useAnnotationLabels(() => ({ collectionId }));

    const sources = $derived(sourcesQuery.data ?? []);
    const labels = $derived(labelsQuery.data ?? []);
    const sourceByName = (name: string | null) => sources.find((s) => s.name === name);
    const isHidden = (name: string | null) => {
        const source = sourceByName(name);
        return source !== undefined && !$isSourceVisible(source.collection_id);
    };
    const sourceNames = $derived(sources.map((s) => s.name));
    const remembered = readRememberedSource(untrack(() => collectionId));
    let chosenSource = $state<string | null>(null);
    const targetSource = $derived(
        resolveTargetSource(
            chosenSource ?? usableRememberedSource(remembered, sourceNames, isHidden),
            sourceNames
        )
    );
    const targetSourceId = $derived(sourceByName(targetSource)?.collection_id);

    // Reading selectedCount makes the target (and so the counts query) follow the selection.
    const target = $derived.by(() => {
        void selectedCount;
        return getSelectionTarget(collectionId, 'images');
    });
    const countsQuery = useImageAnnotationCounts(() => ({
        collectionId,
        filter: targetSourceId ? buildSelectionCountsFilter(target, targetSourceId) : undefined,
        annotationType: 'classification',
        countMode: 'samples',
        enabled: open && targetSourceId !== undefined
    }));
    const counts = $derived(
        new Map(
            targetSourceId
                ? (countsQuery.data ?? []).map((row) => [
                      String(row.label_name),
                      Number(row.current_count)
                  ])
                : []
        )
    );

    let name = $state('');
    let busy = $state(false);
    let pendingDelete = $state<{ labelId: string; className: string; count: number } | null>(null);
    const trimmed = $derived(name.trim());
    const exists = $derived(
        labels.some((l) => l.annotation_label_name.toLowerCase() === trimmed.toLowerCase())
    );

    function refresh() {
        const queryKeys = [
            [...useImageAnnotationCountsQueryKey],
            [...getImagesInfiniteQueryKeyPrefix(collectionId)]
        ];
        queryKeys.forEach((queryKey) => client.invalidateQueries({ queryKey }));
    }

    async function pickSource(sourceName: string) {
        if (isHidden(sourceName)) {
            toast.error(getTargetBlockedReason(sourceName, true)!);
            return false;
        }
        chosenSource = sourceName;
        rememberSource(collectionId, sourceName);
        return true;
    }

    // 1-9 add the first nine classes while the search is empty; typed digits search otherwise.
    function handleNumberKey(event: KeyboardEvent) {
        if (name !== '' || busy || event.ctrlKey || event.metaKey || event.altKey) return;
        const index = numberKeyIndex(event.key);
        const label = index === null ? undefined : labels[index];
        if (!label) return;
        event.preventDefault();
        const className = label.annotation_label_name;
        if ((counts.get(className) ?? 0) < selectedCount) void addToSelection(className);
    }

    async function addToSelection(className: string) {
        const blocked = getTargetBlockedReason(targetSource, isHidden(targetSource));
        if (blocked || !targetSource) {
            toast.error(blocked ?? 'Pick an annotation source.');
            return;
        }
        busy = true;
        try {
            await addClass({
                collectionId,
                selectedIds: get(getSelectedSampleIds(collectionId)),
                className,
                sourceName: targetSource,
                selectAllSnapshot: get(getSelectAllSnapshot(collectionId)),
                rootCollectionId: page.params.dataset_id ?? collectionId
            });
            name = '';
            refresh();
        } catch {
            // addClass already showed the error toast.
        } finally {
            busy = false;
        }
    }

    async function confirmDelete() {
        if (!pendingDelete || !targetSourceId) return;
        const { labelId, className } = pendingDelete;
        busy = true;
        try {
            const selection =
                target.kind === 'filter' ? { filter: target.filter } : { sample_ids: target.ids };
            const { data, error } = await deleteForSamples({
                path: { collection_id: collectionId },
                body: {
                    ...selection,
                    annotation_label_id: labelId,
                    annotation_collection_id: targetSourceId
                }
            });
            if (error || !data) throw new Error();
            toast.success(`Deleted ${className} from ${data.deleted_count} images`);
            refresh();
        } catch {
            toast.error('Failed to delete the classifications.');
        } finally {
            busy = false;
            pendingDelete = null;
        }
    }
</script>

<Popover.Root {open} {onOpenChange}>
    <Popover.Trigger
        class="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-sm font-medium hover:bg-accent"
        aria-label="Annotate"
    >
        <Tags class="size-4" /> Annotate
        {#if shortcutHint}<kbd
                class="ml-1 rounded border border-border bg-muted px-1 text-[10px] uppercase text-muted-foreground"
                >{shortcutHint}</kbd
            >{/if}
    </Popover.Trigger>
    <Popover.Content class="w-72 p-0" align="center" onkeydown={handleNumberKey}>
        <AnnotateSourceMenu
            {collectionId}
            sourceName={targetSource}
            disabled={busy}
            onPick={pickSource}
        />
        <Command.Root label="Annotation classes">
            <Command.Input placeholder="Search or create a class…" bind:value={name} />
            <Command.List class="max-h-56" data-testid="annotate-popover-list">
                {#each labels as label, index (label.annotation_label_id)}
                    {@const className = label.annotation_label_name}
                    {@const count = counts.get(className) ?? 0}
                    <SelectionCountRow
                        name={className}
                        {count}
                        total={selectedCount}
                        {busy}
                        shortcut={name === '' && index < 9 ? index + 1 : undefined}
                        onAdd={() => addToSelection(className)}
                        onRemove={() =>
                            (pendingDelete = {
                                labelId: label.annotation_label_id!,
                                className,
                                count
                            })}
                    />
                {/each}
                {#if trimmed && !exists}
                    <Command.Item
                        value="__create__"
                        forceMount
                        keywords={[]}
                        disabled={busy}
                        onSelect={() => addToSelection(trimmed)}
                    >
                        Create '{trimmed}'
                    </Command.Item>
                {/if}
            </Command.List>
        </Command.Root>
    </Popover.Content>
</Popover.Root>

<Dialog.Root
    open={pendingDelete !== null}
    onOpenChange={(isOpen) => {
        if (!isOpen) pendingDelete = null;
    }}
>
    <Dialog.Content class="max-w-sm">
        <Dialog.Header>
            <Dialog.Title>
                {#if pendingDelete}
                    {formatDeleteConfirm(
                        pendingDelete.className,
                        pendingDelete.count,
                        targetSource ?? ''
                    )}
                {/if}
            </Dialog.Title>
            <Dialog.Description>This cannot be undone.</Dialog.Description>
        </Dialog.Header>
        <Dialog.Footer>
            <Button variant="outline" disabled={busy} onclick={() => (pendingDelete = null)}
                >Cancel</Button
            >
            <Button variant="destructive" disabled={busy} onclick={confirmDelete}>Delete</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
