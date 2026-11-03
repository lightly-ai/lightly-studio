<script lang="ts">
    import { FolderInput, Tags, Trash2 } from '@lucide/svelte';
    import { createQuery, useQueryClient } from '@tanstack/svelte-query';
    import { untrack } from 'svelte';
    import { get } from 'svelte/store';
    import { toast } from 'svelte-sonner';
    import { page } from '$app/state';
    import { labelCountsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import { AnnotationSourcePicker } from '$lib/components/AnnotationSourcePicker';
    import DeleteAnnotationsDialog from '$lib/components/DeleteAnnotationsDialog/DeleteAnnotationsDialog.svelte';
    import * as Command from '$lib/components/ui/command';
    import * as Popover from '$lib/components/ui/popover';
    import {
        useBulkDeleteAnnotations,
        useBulkRelabelAnnotations,
        useGlobalStorage,
        useMoveAnnotationsToSource
    } from '$lib/hooks';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useCollection } from '$lib/hooks/useCollection/useCollection';
    import { getAnnotationsInfiniteQueryKeyPrefix } from '$lib/hooks/useAnnotationsInfinite/createAnnotationsInfiniteOptions';
    import { useUpdateAnnotationsMutation } from '$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
    import { addAnnotationLabelChangeToUndoStack } from '$lib/services/addAnnotationLabelChangeToUndoStack';
    import { getSelectionTarget } from '$lib/hooks/useSelectionTarget/useSelectionTarget';
    import { buildSelectionAnnotationsFilter } from './annotationsAnnotatePopover.helpers';

    interface Props {
        /** The annotation source the grid shows. */
        collectionId: string;
        selectedCount: number;
        open: boolean;
        onOpenChange: (open: boolean) => void;
        /** The key that opens this menu, shown on the trigger. */
        shortcutHint?: string;
    }
    let { collectionId, selectedCount, open, onOpenChange, shortcutHint }: Props = $props();

    const client = useQueryClient();
    const {
        selectedSampleAnnotationCropIds,
        clearSelectedSampleAnnotationCrops,
        addReversibleAction
    } = useGlobalStorage();
    const { updateAnnotations } = useUpdateAnnotationsMutation({
        getCollectionId: () => collectionId
    });
    const { deleteAnnotations } = useBulkDeleteAnnotations();
    const { relabelAnnotations } = useBulkRelabelAnnotations();
    const { moveToSource } = useMoveAnnotationsToSource();
    const labelsQuery = useAnnotationLabels(() => ({ collectionId }));
    // The sources are children of the collection that owns the source on screen.
    const { collection } = useCollection({ collectionId: untrack(() => collectionId) });
    const ownerCollectionId = $derived(collection.data?.parent_collection_id ?? '');

    // Reading selectedCount makes the target (and so the counts query) follow the selection.
    const target = $derived.by(() => {
        void selectedCount;
        return getSelectionTarget(collectionId, 'annotations');
    });
    const selectionFilter = $derived(buildSelectionAnnotationsFilter(target, collectionId));
    const countsQuery = createQuery(() => ({
        ...labelCountsOptions({
            path: { collection_id: collectionId },
            body: { filter: selectionFilter }
        }),
        enabled: open
    }));
    const rows = $derived(countsQuery.data ?? []);

    let name = $state('');
    let busy = $state(false);
    const trimmed = $derived(name.trim());
    const labels = $derived(labelsQuery.data ?? []);
    const exists = $derived(
        labels.some((l) => l.annotation_label_name.toLowerCase() === trimmed.toLowerCase())
    );

    const selectedIds = () => get(selectedSampleAnnotationCropIds)[collectionId] ?? new Set();

    function finish() {
        client.invalidateQueries({ queryKey: [{ _id: 'labelCounts' }] });
        clearSelectedSampleAnnotationCrops(collectionId);
    }

    async function deleteClass(labelId: string) {
        const ids = selectedIds();
        const filter = { ...selectionFilter, annotation_label_ids: [labelId] };
        // A snapshot the size of the selection makes the hook delete by this filter.
        const { data } = await deleteAnnotations({
            collectionId,
            rootCollectionId: page.params.dataset_id ?? collectionId,
            selectedIds: ids,
            selectAllSnapshot: { filter: { ...filter, filter_type: 'annotations' }, size: ids.size }
        });
        if (!data) {
            toast.error('Failed to delete annotations. Please try again.');
            return;
        }
        const noun = data.deleted_count === 1 ? 'annotation' : 'annotations';
        toast.success(`Deleted ${data.deleted_count} ${noun}`);
        finish();
    }

    async function relabel(labelName: string) {
        busy = true;
        const { data } = await relabelAnnotations({
            collectionId,
            selectedIds: selectedIds(),
            selectAllSnapshot:
                target.kind === 'filter' && target.filter.filter_type === 'annotations'
                    ? { filter: target.filter, size: target.size }
                    : null,
            labelName
        });
        busy = false;
        if (!data) {
            toast.error('Failed to relabel the annotations.');
            return;
        }
        addAnnotationLabelChangeToUndoStack({
            annotations: data.previous_labels.map((previous) => ({
                sample_id: previous.annotation_id,
                annotation_label: { annotation_label_name: previous.label_name }
            })),
            collectionId,
            addReversibleAction,
            updateAnnotations,
            refresh: () =>
                client.invalidateQueries({
                    queryKey: [...getAnnotationsInfiniteQueryKeyPrefix(collectionId)]
                })
        });
        toast.success(`Relabeled ${data.previous_labels.length} annotations to '${labelName}'`);
        name = '';
        finish();
    }

    async function move(sourceName: string) {
        const moved = await moveToSource({
            collectionId: ownerCollectionId,
            annotationIds: [...selectedIds()],
            sourceName
        });
        if (moved) finish();
        return moved;
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
    <Popover.Content class="w-72 p-0" align="center">
        <div class="border-b px-3 py-2 text-sm font-medium">All {selectedCount} selected</div>
        <ul class="max-h-40 overflow-y-auto py-1" data-testid="annotate-class-counts">
            {#each rows as row (row.annotation_label_id)}
                <li class="flex h-8 items-center justify-between gap-2 px-3 text-sm">
                    <span class="min-w-0 truncate">{row.label_name}</span>
                    <span class="flex items-center gap-1">
                        <span class="text-xs text-muted-foreground">{row.count}</span>
                        <DeleteAnnotationsDialog
                            selectedCount={row.count}
                            disabled={busy}
                            onDelete={() => deleteClass(row.annotation_label_id)}
                        >
                            {#snippet trigger({ props })}
                                <button
                                    {...props}
                                    class="rounded p-0.5 hover:bg-accent"
                                    aria-label={`Delete ${row.label_name} annotations`}
                                    ><Trash2 class="size-3.5" /></button
                                >
                            {/snippet}
                        </DeleteAnnotationsDialog>
                    </span>
                </li>
            {/each}
        </ul>
        <Command.Root label="Relabel" class="border-t">
            <Command.Input placeholder="Relabel all to…" bind:value={name} />
            {#if trimmed}
                <Command.List class="max-h-40">
                    {#each labels as label (label.annotation_label_id)}
                        <Command.Item
                            value={label.annotation_label_name}
                            disabled={busy}
                            onSelect={() => relabel(label.annotation_label_name)}
                        >
                            {label.annotation_label_name}
                        </Command.Item>
                    {/each}
                    {#if !exists}
                        <Command.Item
                            value="__create__"
                            forceMount
                            keywords={[]}
                            disabled={busy}
                            onSelect={() => relabel(trimmed)}
                        >
                            Create '{trimmed}'
                        </Command.Item>
                    {/if}
                </Command.List>
            {/if}
        </Command.Root>
        <div class="border-t p-2">
            <AnnotationSourcePicker
                collectionId={ownerCollectionId}
                excludeSourceId={collectionId}
                label="Move the selected annotations to another annotation source"
                heading="Move to"
                icon={FolderInput}
                triggerText="Move to annotation source…"
                disabled={busy || !ownerCollectionId}
                onPick={move}
            />
        </div>
    </Popover.Content>
</Popover.Root>
