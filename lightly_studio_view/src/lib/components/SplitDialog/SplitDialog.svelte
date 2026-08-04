<script lang="ts">
    import { page } from '$app/state';
    import { get, derived } from 'svelte/store';
    import { Plus, Trash2, ChevronDown } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import * as Dialog from '$lib/components/ui/dialog';
    import * as Collapsible from '$lib/components/ui/collapsible';
    import { useGlobalStorage } from '$lib/hooks';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { useSplitDialog } from '$lib/hooks/useSplitDialog/useSplitDialog';
    import { useCreateSplit } from '$lib/hooks/useCreateSplit/useCreateSplit';
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

    const existingTagNames = derived(tags, ($tags) => $tags.map((tag) => tag.name));
    const {
        rows,
        percentageSum,
        errorMessage,
        isValid,
        previewCounts,
        overwrittenTagNames,
        addRow,
        removeRow,
        updateName,
        updatePercentage,
        reset,
        getSizes
    } = useSplitForm({ filteredSampleCount, existingTagNames });

    const { isSubmitting, submit } = useCreateSplit({
        tags,
        setTagSelected,
        loadTags,
        closeSplitDialog
    });

    let showAdvanced = $state(false);
    let seed = $state<number | null>(null);
    let confirmingOverwrite = $state(false);

    function buildFilter(): SplitCreateBody['filter'] {
        if (isVideoCollection) {
            const f = get(videoFilter);
            return f ? { ...f, filter_type: 'video' } : null;
        }
        const f = get(imageFilter);
        return f ? { ...f, filter_type: 'image' } : null;
    }

    const isFiltered = $derived(buildFilter() !== null);

    async function handleSubmit(event: Event) {
        event.preventDefault();
        if (!$isValid || $isSubmitting) return;
        if ($overwrittenTagNames.length > 0 && !confirmingOverwrite) {
            confirmingOverwrite = true;
            return;
        }
        const success = await submit({
            collectionId,
            sizes: getSizes(),
            filter: buildFilter(),
            seed
        });
        if (success) {
            reset();
            seed = null;
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
                        {$filteredSampleCount === 1 ? 'sample' : 'samples'} to named split tags.
                    </Dialog.Description>
                </Dialog.Header>

                <div class="grid max-h-[60vh] gap-4 overflow-y-auto p-2 py-4">
                    <div class="grid gap-2">
                        {#each $rows as row (row.id)}
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
                                    class="w-20"
                                    min="0"
                                    max="100"
                                    value={row.percentage}
                                    oninput={(e) =>
                                        updatePercentage(row.id, e.currentTarget.valueAsNumber)}
                                    data-testid="split-percentage-input"
                                />
                                <span class="w-10 text-xs text-muted-foreground">%</span>
                                <span
                                    class="w-16 text-right text-xs text-muted-foreground"
                                    data-testid="split-count-preview"
                                >
                                    {$previewCounts[row.name] ?? 0}
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
                        <span class="text-xs text-muted-foreground">Total: {$percentageSum}%</span>
                    </div>

                    <Collapsible.Root bind:open={showAdvanced}>
                        <Collapsible.Trigger
                            class="flex items-center gap-1 text-sm text-muted-foreground"
                        >
                            <ChevronDown class="size-4" /> Advanced
                        </Collapsible.Trigger>
                        <Collapsible.Content class="pt-2">
                            <div class="grid gap-2">
                                <Label for="split-seed" class="text-foreground"
                                    >Seed (optional)</Label
                                >
                                <Input
                                    id="split-seed"
                                    type="number"
                                    placeholder="Random"
                                    value={seed ?? ''}
                                    oninput={(e) =>
                                        (seed = Number.isFinite(e.currentTarget.valueAsNumber)
                                            ? e.currentTarget.valueAsNumber
                                            : null)}
                                    data-testid="split-seed-input"
                                />
                            </div>
                        </Collapsible.Content>
                    </Collapsible.Root>

                    {#if $errorMessage}
                        <p class="text-sm text-destructive-text" data-testid="split-error">
                            {$errorMessage}
                        </p>
                    {/if}

                    {#if confirmingOverwrite && $overwrittenTagNames.length > 0}
                        <p
                            class="text-sm text-destructive-text"
                            data-testid="split-overwrite-warning"
                        >
                            This will clear and reassign the existing
                            {$overwrittenTagNames.join(', ')}
                            {$overwrittenTagNames.length === 1 ? 'tag' : 'tags'}. Confirm to
                            continue.
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
                        {:else if confirmingOverwrite && $overwrittenTagNames.length > 0}
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
