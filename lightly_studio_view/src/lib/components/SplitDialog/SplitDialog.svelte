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

    let showClearConfirm = $state(false);

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

    // Existing sample tags in the collection, so we can tell new tags apart from
    // ones that will be overwritten.
    const existingTagNames = $derived(new Set($tags.map((tag) => tag.name)));

    // Target tags that do not exist yet — they will be created.
    const createdNames = $derived(targetNames.filter((name) => !existingTagNames.has(name)));

    // Target tags that already hold selected samples — wiped before reassignment.
    const clearedNames = $derived(
        overlapQuery.isLoading
            ? []
            : targetNames.filter(
                  (name) => existingTagNames.has(name) && (overlapCounts.get(name) ?? 0) > 0
              )
    );

    // Cleared tags gate the overwrite confirmation.
    const clearedTags = $derived(clearedNames);

    async function handleSubmit(event: Event) {
        event.preventDefault();
        if (!$isValid || $isSubmitting || overlapQuery.isLoading) return;
        // Clearing existing tags is destructive, so confirm it in a popup first.
        if (clearedTags.length > 0) {
            showClearConfirm = true;
            return;
        }
        await runSplit();
    }

    async function runSplit() {
        const success = await submit({
            collectionId,
            sizes: getSizes(),
            filter: currentFilter
        });
        if (success) reset();
    }

    async function confirmClearAndSplit() {
        showClearConfirm = false;
        await runSplit();
    }
</script>

<!-- Renders tag names in bold, comma-separated with a trailing "and": "a, b and c". -->
{#snippet tagNames(names: string[])}
    {#each names as name, i (name)}{#if i > 0}{i === names.length - 1 ? ' and ' : ', '}{/if}<strong
            class="font-semibold">{name}</strong
        >{/each}
{/snippet}

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
                        {$filteredSampleCount === 1 ? 'sample' : 'samples'} to named split tags.
                    </Dialog.Description>
                </Dialog.Header>

                <div class="flex max-h-[60vh] flex-col gap-4 overflow-y-auto p-2 py-4">
                    <div
                        class="grid grid-cols-[minmax(0,1fr)_5.5rem_auto_auto_2rem] items-center gap-x-3 gap-y-2"
                    >
                        <span class="text-xs font-medium text-muted-foreground">Tag</span>
                        <span class="text-xs font-medium text-muted-foreground">Relative size</span>
                        <span class="text-right text-xs font-medium text-muted-foreground"
                            >Share</span
                        >
                        <span class="text-right text-xs font-medium text-muted-foreground">
                            Samples
                        </span>
                        <span></span>

                        {#each $rows as row (row.id)}
                            {@const info = $preview[row.id] ?? { percentage: 0, count: 0 }}
                            <Input
                                type="text"
                                class="w-full"
                                placeholder="Split name"
                                value={row.name}
                                oninput={(e) => updateName(row.id, e.currentTarget.value)}
                                data-testid="split-name-input"
                            />
                            <Input
                                type="number"
                                class="w-full"
                                min="1"
                                step="1"
                                value={row.parts}
                                oninput={(e) => updateParts(row.id, e.currentTarget.valueAsNumber)}
                                aria-label={`Parts for ${row.name || 'split'}`}
                                data-testid="split-parts-input"
                            />
                            <span
                                class="justify-self-end whitespace-nowrap text-right text-xs tabular-nums text-muted-foreground"
                                data-testid="split-share"
                            >
                                {info.percentage}%
                            </span>
                            <span
                                class="justify-self-end whitespace-nowrap text-right text-xs tabular-nums text-muted-foreground"
                                data-testid="split-count"
                            >
                                {info.count}
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
                        {/each}
                    </div>

                    <Button
                        variant="outline"
                        size="sm"
                        type="button"
                        class="self-start"
                        onclick={addRow}
                    >
                        <Plus class="mr-1 size-4" /> Add split
                    </Button>

                    {#if $errorMessage}
                        <p class="text-sm text-destructive-text" data-testid="split-error">
                            {$errorMessage}
                        </p>
                    {/if}

                    {#if createdNames.length > 0}
                        <p
                            class="rounded-md border border-border bg-muted/40 p-3 text-sm text-muted-foreground"
                            data-testid="split-created-info"
                        >
                            {createdNames.length === 1 ? 'Tag' : 'Tags'}
                            {@render tagNames(createdNames)}
                            will be created.
                        </p>
                    {/if}

                    {#if clearedNames.length > 0}
                        <p
                            class="rounded-md border border-destructive-text/40 bg-destructive-text/10 p-3 text-sm text-destructive-text"
                            data-testid="split-cleared-warning"
                        >
                            {clearedNames.length === 1 ? 'Tag' : 'Tags'}
                            {@render tagNames(clearedNames)}
                            will be cleared before assignment.
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
                        {$isSubmitting ? 'Splitting...' : 'Split'}
                    </Button>
                </Dialog.Footer>
            </form>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>

<!-- Confirmation popup shown before clearing tags that already hold selected samples. -->
<Dialog.Root open={showClearConfirm} onOpenChange={(open) => (showClearConfirm = open)}>
    <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content class="border-border bg-background sm:max-w-[440px]">
            <Dialog.Header>
                <Dialog.Title class="text-foreground">Clear existing tags?</Dialog.Title>
                <Dialog.Description class="text-foreground">
                    {clearedNames.length === 1 ? 'Tag' : 'Tags'}
                    <span class="text-destructive-text">{@render tagNames(clearedNames)}</span>
                    already {clearedNames.length === 1 ? 'has' : 'have'} assigned samples. Splitting will
                    clear {clearedNames.length === 1 ? 'it' : 'them'} first, then reassign. This cannot
                    be undone.
                </Dialog.Description>
            </Dialog.Header>
            <Dialog.Footer class="mt-4">
                <Button
                    variant="outline"
                    type="button"
                    onclick={() => (showClearConfirm = false)}
                    disabled={$isSubmitting}
                >
                    Cancel
                </Button>
                <Button
                    variant="destructive"
                    type="button"
                    onclick={confirmClearAndSplit}
                    disabled={$isSubmitting}
                    data-testid="split-confirm-clear"
                >
                    {$isSubmitting ? 'Splitting...' : 'Clear and split'}
                </Button>
            </Dialog.Footer>
        </Dialog.Content>
    </Dialog.Portal>
</Dialog.Root>
