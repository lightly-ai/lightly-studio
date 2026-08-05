<script lang="ts">
    import { page } from '$app/state';
    import { Plus, Trash2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import * as Dialog from '$lib/components/ui/dialog';
    import { useGlobalStorage } from '$lib/hooks';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { useSplitDialog } from '$lib/hooks/useSplitDialog/useSplitDialog';
    import { useCreateSplit } from '$lib/hooks/useCreateSplit/useCreateSplit';
    import { useSelectionTagOverlap } from '$lib/hooks/useSelectionTagOverlap/useSelectionTagOverlap.svelte';
    import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import type { SplitCreateBody } from '$lib/api/lightly_studio_local/types.gen';
    import { useSplitForm } from './useSplitForm';
    import { formatClearedMessage, formatCreatedMessage } from './splitDialogMessages';

    const collectionId = $derived(page.params.collection_id!);
    const isVideoCollection = $derived(
        page.data.collection?.sample_type === 'video' ||
            page.data.collection?.sample_type === 'video_frame'
    );

    const { isSplitDialogOpen, closeSplitDialog } = useSplitDialog();
    const { filteredSampleCount } = useGlobalStorage();
    const { tags, loadTags, setTagSelected } = useTags({
        collection_id: page.params.collection_id!,
        kind: ['sample']
    });
    const { imageFilter } = useImageFilters();
    const { videoFilter } = useVideoFilters();

    const {
        rows,
        errorMessage,
        isValid,
        preview,
        addRow,
        removeRow,
        updateName,
        updateParts,
        reset,
        getSizes
    } = useSplitForm({ filteredSampleCount });

    const { isSubmitting, submit } = useCreateSplit({
        tags,
        setTagSelected,
        loadTags,
        closeSplitDialog
    });

    let confirmingOverwrite = $state(false);

    const currentFilter = $derived.by((): SplitCreateBody['filter'] => {
        if (isVideoCollection) {
            return $videoFilter ? { ...$videoFilter, filter_type: 'video' } : null;
        }
        return $imageFilter ? { ...$imageFilter, filter_type: 'image' } : null;
    });

    const isFiltered = $derived(currentFilter !== null);

    // Overlap of the current filtered selection with existing sample tags, so we
    // can warn about which target splits will be cleared before submitting.
    const overlapQuery = useSelectionTagOverlap(() => ({
        collectionId,
        filter: currentFilter,
        enabled: $isSplitDialogOpen
    }));

    const overlapCounts = $derived.by(() => {
        const counts = new Map<string, number>();
        for (const tag of overlapQuery.data?.tags ?? []) counts.set(tag.name, tag.count);
        return counts;
    });

    const targetNames = $derived($rows.map((row) => row.name.trim()).filter((name) => name.length));

    // Target splits already carrying selected samples — these get overwritten.
    const clearedTags = $derived(
        targetNames
            .filter((name) => (overlapCounts.get(name) ?? 0) > 0)
            .map((name) => ({ name, count: overlapCounts.get(name)! }))
    );

    // Target splits that do not yet exist as sample tags in the collection.
    const existingTagNames = $derived(new Set($tags.map((tag) => tag.name)));
    const createdNames = $derived(targetNames.filter((name) => !existingTagNames.has(name)));

    const clearedMessage = $derived(formatClearedMessage(clearedTags));
    const createdMessage = $derived(formatCreatedMessage(createdNames));

    async function handleSubmit(event: Event) {
        event.preventDefault();
        if (!$isValid || $isSubmitting || overlapQuery.isLoading) return;
        if (clearedTags.length > 0 && !confirmingOverwrite) {
            confirmingOverwrite = true;
            return;
        }
        const success = await submit({
            collectionId,
            sizes: getSizes(),
            filter: currentFilter
        });
        if (success) {
            reset();
            confirmingOverwrite = false;
        }
    }
</script>

<Dialog.Root
    open={$isSplitDialogOpen}
    onOpenChange={(open) => (open ? undefined : closeSplitDialog())}
>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[520px]">
            <form onsubmit={handleSubmit}>
                <Dialog.Header>
                    <Dialog.Title class="text-foreground">Split dataset</Dialog.Title>
                    <Dialog.Description class="text-foreground">
                        Randomly assign the
                        <strong class="font-semibold text-primary">{$filteredSampleCount}</strong>
                        {isFiltered ? 'filtered' : ''}
                        {$filteredSampleCount === 1 ? 'sample' : 'samples'} to named split tags. Sizes
                        are relative parts — the share and sample count are shown alongside.
                    </Dialog.Description>
                </Dialog.Header>

                <div class="grid max-h-[60vh] gap-4 overflow-y-auto p-2 py-4">
                    <div class="grid gap-2">
                        {#each $rows as row (row.id)}
                            {@const info = $preview[row.id] ?? { percentage: 0, count: 0 }}
                            <div class="flex items-center gap-2">
                                <Input
                                    type="text"
                                    class="flex-1"
                                    placeholder="Split name"
                                    value={row.name}
                                    oninput={(e) => updateName(row.id, e.currentTarget.value)}
                                    data-testid="split-name-input"
                                />
                                <Input
                                    type="number"
                                    class="w-16"
                                    min="1"
                                    step="1"
                                    value={row.parts}
                                    oninput={(e) =>
                                        updateParts(row.id, e.currentTarget.valueAsNumber)}
                                    aria-label={`Parts for ${row.name || 'split'}`}
                                    data-testid="split-parts-input"
                                />
                                <span
                                    class="shrink-0 whitespace-nowrap text-right text-xs text-muted-foreground"
                                    data-testid="split-preview"
                                >
                                    {info.percentage}% · {info.count}
                                    {info.count === 1 ? 'sample' : 'samples'}
                                </span>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    type="button"
                                    disabled={$rows.length <= 1}
                                    onclick={() => removeRow(row.id)}
                                    aria-label="Remove split"
                                >
                                    <Trash2 class="size-4" />
                                </Button>
                            </div>
                        {/each}
                    </div>

                    <div class="flex items-center justify-between">
                        <Button variant="outline" size="sm" type="button" onclick={addRow}>
                            <Plus class="mr-1 size-4" /> Add split
                        </Button>
                    </div>

                    {#if $errorMessage}
                        <p class="text-sm text-destructive-text" data-testid="split-error">
                            {$errorMessage}
                        </p>
                    {/if}

                    {#if !overlapQuery.isLoading && clearedMessage}
                        <p
                            class="text-sm text-destructive-text"
                            data-testid="split-cleared-warning"
                        >
                            {clearedMessage}
                        </p>
                    {/if}

                    {#if createdMessage}
                        <p class="text-sm text-muted-foreground" data-testid="split-created-info">
                            {createdMessage}
                        </p>
                    {/if}
                </div>

                <Dialog.Footer class="mt-4">
                    <Button
                        variant="outline"
                        type="button"
                        onclick={closeSplitDialog}
                        disabled={$isSubmitting}
                    >
                        Cancel
                    </Button>
                    <Button
                        type="submit"
                        disabled={!$isValid || $isSubmitting}
                        data-testid="split-submit"
                    >
                        {#if $isSubmitting}
                            Splitting...
                        {:else if confirmingOverwrite && clearedTags.length > 0}
                            Overwrite &amp; split
                        {:else}
                            Split
                        {/if}
                    </Button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
