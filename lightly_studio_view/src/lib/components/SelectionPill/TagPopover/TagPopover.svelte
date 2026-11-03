<script lang="ts">
    import { Tag } from '@lucide/svelte';
    import { useQueryClient } from '@tanstack/svelte-query';
    import { toast } from 'svelte-sonner';
    import * as Command from '$lib/components/ui/command';
    import * as Popover from '$lib/components/ui/popover';
    import {
        addSampleIdsToTagId,
        addSamplesToTagByFilter,
        createTag,
        removeSamplesFromTagByFilter,
        removeThingIdsToTagId
    } from '$lib/api/lightly_studio_local';
    import { countTagsForSelectionQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
    import { getImagesInfiniteQueryKeyPrefix } from '$lib/hooks/useImagesInfinite/createImagesInfiniteOptions';
    import { getAnnotationsInfiniteQueryKeyPrefix } from '$lib/hooks/useAnnotationsInfinite/createAnnotationsInfiniteOptions';
    import { getSelectionTarget } from '$lib/hooks/useSelectionTarget/useSelectionTarget';
    import { useSelectionTagCounts } from '$lib/hooks/useSelectionTagCounts';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import type { GridType } from '$lib/types';
    import SelectionCountRow from '../SelectionCountRow/SelectionCountRow.svelte';
    import { formatTagAddToast, formatTagRemoveToast } from './tagToasts';
    import { useSelectionUndo } from '../useSelectionUndo/useSelectionUndo';

    interface Props {
        collectionId: string;
        gridType: GridType;
        selectedCount: number;
        open: boolean;
        onOpenChange: (open: boolean) => void;
        /** The key that opens this menu, shown on the trigger. */
        shortcutHint?: string;
    }
    let { collectionId, gridType, selectedCount, open, onOpenChange, shortcutHint }: Props =
        $props();

    const client = useQueryClient();
    const { offerUndo } = useSelectionUndo();
    const { tags, loadTags } = $derived(useTags({ collection_id: collectionId }));
    // Reading selectedCount makes the target (and so the counts query) follow the selection.
    const target = $derived.by(() => {
        void selectedCount;
        return getSelectionTarget(collectionId, gridType);
    });
    const { query } = useSelectionTagCounts(() => ({ collectionId, target, enabled: open }));
    const counts = $derived(query.data ?? new Map<string, number>());

    let name = $state('');
    let busy = $state(false);
    const trimmed = $derived(name.trim());
    const exists = $derived($tags.some((t) => t.name.toLowerCase() === trimmed.toLowerCase()));

    function add(tagId: string) {
        const path = { collection_id: collectionId, tag_id: tagId };
        return target.kind === 'filter'
            ? addSamplesToTagByFilter({ path, body: { filter: target.filter } })
            : addIds(tagId, target.ids);
    }

    function remove(tagId: string) {
        return target.kind === 'filter'
            ? removeSamplesFromTagByFilter({
                  path: { collection_id: collectionId, tag_id: tagId },
                  body: { filter: target.filter }
              })
            : removeIds(tagId, target.ids);
    }

    const addIds = (tagId: string, ids: string[]) =>
        addSampleIdsToTagId({
            path: { collection_id: collectionId, tag_id: tagId },
            body: { sample_ids: ids }
        });
    const removeIds = (tagId: string, ids: string[]) =>
        removeThingIdsToTagId({
            path: { tag_id: tagId },
            body: { sample_ids: ids }
        });

    type Revert = (changedIds: string[]) => Promise<{ error?: unknown }>;

    // Undo touches only the items the action changed, so items that had the tag keep it.
    function offerUndoFor(message: string, changedIds: string[], revert: Revert) {
        if (changedIds.length === 0) {
            toast.success(message);
            return;
        }
        offerUndo({
            message,
            revert: async () => {
                const response = await revert(changedIds);
                if (response.error) throw new Error('Failed to undo.');
                refresh();
            }
        });
    }

    function refresh() {
        const queryKeys = [
            countTagsForSelectionQueryKey({ path: { collection_id: collectionId }, body: {} }),
            [...getImagesInfiniteQueryKeyPrefix(collectionId)],
            [...getAnnotationsInfiniteQueryKeyPrefix(collectionId)]
        ];
        queryKeys.forEach((queryKey) => client.invalidateQueries({ queryKey }));
        void loadTags();
    }

    async function run(
        action: () => Promise<{ data?: { changed_ids: string[] }; error?: unknown }>,
        message: (changed: number, selected: number) => string,
        fail: string,
        revert: Revert
    ): Promise<boolean> {
        busy = true;
        try {
            const response = await action();
            if (response.error) throw new Error(fail);
            const changedIds = response.data?.changed_ids ?? [];
            offerUndoFor(message(changedIds.length, selectedCount), changedIds, revert);
            refresh();
            return true;
        } catch {
            toast.error(fail);
            return false;
        } finally {
            busy = false;
        }
    }

    const addTag = (tagId: string, tagName: string) =>
        run(
            () => add(tagId),
            (changed, selected) => formatTagAddToast(tagName, changed, selected),
            'Failed to add tag.',
            (ids) => removeIds(tagId, ids)
        );
    const removeTag = (tagId: string, tagName: string) =>
        run(
            () => remove(tagId),
            (changed, selected) => formatTagRemoveToast(tagName, changed, selected),
            'Failed to remove tag.',
            (ids) => addIds(tagId, ids)
        );

    async function createAndAdd(tagName: string) {
        try {
            const created = await createTag({
                path: { collection_id: collectionId },
                body: { name: tagName }
            });
            const tagId = created.data?.tag_id;
            if (created.error || !tagId) throw new Error('Failed to create tag.');
            // Refresh right away so a failed add leaves the new tag in the list for a retry.
            refresh();
            if (await addTag(tagId, tagName)) name = '';
        } catch {
            toast.error('Failed to create tag.');
        }
    }
</script>

<Popover.Root {open} {onOpenChange}>
    <Popover.Trigger
        class="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-sm font-medium hover:bg-accent"
        aria-label="Tag"
    >
        <Tag class="size-4" /> Tag
        {#if shortcutHint}<kbd
                class="ml-1 rounded border border-border bg-muted px-1 text-[10px] uppercase text-muted-foreground"
                >{shortcutHint}</kbd
            >{/if}
    </Popover.Trigger>
    <Popover.Content class="w-64 p-0" align="center">
        <Command.Root label="Tags">
            <Command.Input placeholder="Search or create a tag…" bind:value={name} />
            <Command.List class="max-h-40" data-testid="tag-popover-list">
                {#each $tags as tag (tag.tag_id)}
                    <SelectionCountRow
                        name={tag.name}
                        count={counts.get(tag.tag_id) ?? 0}
                        total={selectedCount}
                        {busy}
                        onAdd={() => addTag(tag.tag_id, tag.name)}
                        onRemove={() => removeTag(tag.tag_id, tag.name)}
                    />
                {/each}
                {#if trimmed && !exists}
                    <Command.Item
                        value="__create__"
                        forceMount
                        keywords={[]}
                        disabled={busy}
                        onSelect={() => createAndAdd(trimmed)}
                    >
                        Create '{trimmed}'
                    </Command.Item>
                {/if}
            </Command.List>
        </Command.Root>
    </Popover.Content>
</Popover.Root>
