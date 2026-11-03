<script lang="ts">
    import { Layers, Plus, Tags, X } from '@lucide/svelte';
    import { useQueryClient } from '@tanstack/svelte-query';
    import { get } from 'svelte/store';
    import { toast } from 'svelte-sonner';
    import { page } from '$app/state';
    import { deleteForSamples } from '$lib/api/lightly_studio_local';
    import { AnnotationSourcePicker } from '$lib/components/AnnotationSourcePicker';
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
    import {
        buildSelectionCountsFilter,
        formatDeleteConfirm
    } from './imagesAnnotatePopover.helpers';

    interface Props {
        collectionId: string;
        selectedCount: number;
        open: boolean;
        onOpenChange: (open: boolean) => void;
    }
    let { collectionId, selectedCount, open, onOpenChange }: Props = $props();

    const client = useQueryClient();
    const { addClass } = useBulkCreateClassifications();
    const { isSourceVisible } = useAnnotationCollectionsFilter();
    const { getSelectedSampleIds, getSelectAllSnapshot } = useGlobalStorage();
    const sourcesQuery = useAnnotationCollections(() => ({ collectionId }));
    const labelsQuery = useAnnotationLabels(() => ({ collectionId }));

    const sources = $derived(sourcesQuery.data ?? []);
    const labels = $derived(labelsQuery.data ?? []);
    let chosenSource = $state<string | null>(null);
    const targetSource = $derived(
        resolveTargetSource(
            chosenSource,
            sources.map((s) => s.name)
        )
    );
    const sourceByName = (name: string | null) => sources.find((s) => s.name === name);
    const isHidden = (name: string | null) => {
        const source = sourceByName(name);
        return source !== undefined && !$isSourceVisible(source.collection_id);
    };
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
        return true;
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
        class="inline-flex h-7 items-center gap-1 rounded-md px-2 text-sm hover:bg-primary-foreground/10"
        aria-label="Annotate"
    >
        <Tags class="size-4" /> Annotate
    </Popover.Trigger>
    <Popover.Content class="w-72 p-0" align="center">
        <div class="border-b p-2">
            <AnnotationSourcePicker
                {collectionId}
                label="Annotation source"
                heading="Add classifications to"
                icon={Layers}
                triggerText={targetSource ?? 'Pick an annotation source'}
                disabled={busy}
                onPick={pickSource}
            />
        </div>
        <Command.Root label="Annotation classes">
            <Command.Input placeholder="Search or create a class…" bind:value={name} />
            <Command.List class="max-h-40" data-testid="annotate-popover-list">
                {#each labels as label (label.annotation_label_id)}
                    {@const className = label.annotation_label_name}
                    {@const count = counts.get(className) ?? 0}
                    <Command.Item
                        value={className}
                        class="group h-8 justify-between"
                        disabled={busy}
                        onSelect={() => count < selectedCount && addToSelection(className)}
                    >
                        <span class="min-w-0 truncate">{className}</span>
                        <span class="flex items-center gap-1">
                            <span class="text-xs text-muted-foreground"
                                >{count}/{selectedCount}</span
                            >
                            {#if count < selectedCount}
                                <button
                                    class="hidden rounded p-0.5 hover:bg-accent group-hover:block group-data-[selected]:block"
                                    aria-label={`Add ${className} to selection`}
                                    disabled={busy}
                                    onclick={(e) => {
                                        e.stopPropagation();
                                        void addToSelection(className);
                                    }}><Plus class="size-3.5" /></button
                                >
                            {/if}
                            {#if count > 0}
                                <button
                                    class="hidden rounded p-0.5 hover:bg-accent group-hover:block group-data-[selected]:block"
                                    aria-label={`Remove ${className} from selection`}
                                    disabled={busy}
                                    onclick={(e) => {
                                        e.stopPropagation();
                                        pendingDelete = {
                                            labelId: label.annotation_label_id!,
                                            className,
                                            count
                                        };
                                    }}><X class="size-3.5" /></button
                                >
                            {/if}
                        </span>
                    </Command.Item>
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
