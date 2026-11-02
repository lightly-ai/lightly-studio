<script lang="ts">
    import type { GridType } from '$lib/types';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Checkbox } from '$lib/components';
    import type { TagView } from '$lib/services/types';
    import { useTags } from '$lib/hooks/useTags/useTags.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import {
        createTag,
        addSampleIdsToTagId,
        addSamplesToTagByFilter,
        deleteTag,
        renameTag,
        removeThingIdsToTagId,
        removeSamplesFromTagByFilter
    } from '$lib/api/lightly_studio_local';
    import TagAssignInput from './TagAssignInput.svelte';
    import TagRenameInput from './TagRenameInput.svelte';
    import TagActionMenu from './TagActionMenu.svelte';
    import TagSelectionCount from './TagSelectionCount.svelte';
    import { useSelectionTagCounts } from './useSelectionTagCounts.svelte';
    import { toast } from 'svelte-sonner';
    import { cn } from '$lib/utils';
    import { usePostHog } from '$lib/hooks';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';

    let {
        collection_id,
        gridType,
        allowAssign = true
    }: Parameters<typeof useTags>[0] & {
        gridType: GridType;
        /** Set to false for views without a selection to assign tags to, so they only filter. */
        allowAssign?: boolean;
    } = $props();

    const isAnnotationGrid = $derived(gridType === 'annotations');

    const { tags, tagsSelected, tagSelectionToggle, loadTags, clearTagSelected } = $derived(
        useTags({ collection_id })
    );

    const {
        getSelectedSampleIds,
        selectedSampleAnnotationCropIds,
        getSelectAllSnapshot,
        getSelectAllAnnotationSnapshot
    } = useGlobalStorage();

    const selectedSampleIds = $derived(getSelectedSampleIds(collection_id));
    const hasSelection = $derived(
        isAnnotationGrid
            ? ($selectedSampleAnnotationCropIds[collection_id]?.size ?? 0) > 0
            : $selectedSampleIds.size > 0
    );
    const selectedIds = $derived(
        isAnnotationGrid
            ? ($selectedSampleAnnotationCropIds[collection_id] ?? new Set<string>())
            : $selectedSampleIds
    );

    const selectAllSnapshot = $derived(
        isAnnotationGrid
            ? getSelectAllAnnotationSnapshot(collection_id)
            : getSelectAllSnapshot(collection_id)
    );
    // Use the grid filter while the selection is an unmodified select-all, so that a
    // large selection does not send a potentially large ID list.
    const selectionFilter = $derived(
        $selectAllSnapshot != null && $selectAllSnapshot.size === selectedIds.size
            ? $selectAllSnapshot.filter
            : null
    );

    const { query: selectionTagCounts } = useSelectionTagCounts(() => ({
        collection_id,
        selection: selectionFilter ? { filter: selectionFilter } : { sample_ids: [...selectedIds] },
        enabled: hasSelection
    }));
    const tagCounts = $derived(hasSelection ? selectionTagCounts.data : undefined);

    const { trackEvent } = usePostHog();
    const { user } = useAuth();
    const canManageTags = $derived(hasMinimumRole(user?.role, 'labeler'));

    let assignBusy = $state(false);
    let deletingTagId = $state<string | null>(null);
    let editingTagId = $state<string | null>(null);
    let renamingTagId = $state<string | null>(null);
    let openActionsTagId = $state<string | null>(null);
    let suppressCloseAutoFocusTagId = $state<string | null>(null);

    function assignSelectionToTag(tag_id: string) {
        if (selectionFilter) {
            return addSamplesToTagByFilter({
                path: { collection_id, tag_id },
                body: { filter: selectionFilter }
            });
        }
        return addSampleIdsToTagId({
            path: { collection_id, tag_id },
            body: { sample_ids: [...selectedIds] }
        });
    }

    async function handleAssign(name: string) {
        assignBusy = true;
        const snapshotCount = selectedIds.size;

        function trackTagged(isNewTag: boolean) {
            try {
                trackEvent('samples_tagged', {
                    collection_id,
                    grid_type: gridType,
                    sample_count: snapshotCount,
                    is_new_tag: isNewTag
                });
            } catch (e) {
                console.error('Failed to track samples_tagged event', e);
            }
        }

        try {
            const existingTag = $tags.find(
                (t: TagView) => t.name.toLowerCase() === name.toLowerCase()
            );
            if (existingTag) {
                const response = await assignSelectionToTag(existingTag.tag_id);
                if (response.error) {
                    toast.error('Failed to assign tag. Please try again.');
                    return;
                }
                trackTagged(false);
            } else {
                const createResponse = await createTag({
                    path: { collection_id },
                    body: { name }
                });
                if (createResponse.error || !createResponse.data?.tag_id) {
                    toast.error('Failed to create tag. Please try again.');
                    return;
                }
                const assignResponse = await assignSelectionToTag(createResponse.data.tag_id);
                if (assignResponse.error) {
                    toast.error('Failed to assign tag. Please try again.');
                    return;
                }
                trackTagged(true);
            }
            loadTags();
            selectionTagCounts.refetch();
        } catch (error) {
            console.error('Failed to assign tag', error);
            toast.error('Failed to assign tag. Please try again.');
        } finally {
            assignBusy = false;
        }
    }

    let removingTagId = $state<string | null>(null);

    async function handleRemoveFromSelection(tag: TagView, count: number) {
        removingTagId = tag.tag_id;
        try {
            const response = selectionFilter
                ? await removeSamplesFromTagByFilter({
                      path: { collection_id, tag_id: tag.tag_id },
                      body: { filter: selectionFilter }
                  })
                : await removeThingIdsToTagId({
                      path: { tag_id: tag.tag_id },
                      body: { sample_ids: [...selectedIds] }
                  });
            if (response.error) {
                throw new Error('Failed to remove tag.');
            }
            await selectionTagCounts.refetch();
            toast.success(`Removed "${tag.name}" from ${count} items`);
        } catch {
            toast.error('Failed to remove tag. Please try again.');
        } finally {
            removingTagId = null;
        }
    }

    async function handleDeleteTag(tag: TagView, event: MouseEvent) {
        event.stopPropagation();

        if (deletingTagId) {
            return;
        }

        deletingTagId = tag.tag_id;

        try {
            const response = await deleteTag({
                path: { collection_id, tag_id: tag.tag_id }
            });

            if (response.error) {
                throw new Error('Failed to delete tag.');
            }

            clearTagSelected(tag.tag_id);
            loadTags();
            toast.success('Tag deleted successfully');
        } catch {
            toast.error('Failed to delete tag. Please try again.');
        } finally {
            deletingTagId = null;
        }
    }

    async function openRename(tag: TagView, event: MouseEvent) {
        event.stopPropagation();
        if (deletingTagId || renamingTagId) {
            return;
        }
        suppressCloseAutoFocusTagId = tag.tag_id;
        openActionsTagId = null;
        editingTagId = tag.tag_id;
    }

    function cancelRename() {
        editingTagId = null;
    }

    async function handleRename(tag: TagView, newName: string) {
        renamingTagId = tag.tag_id;

        try {
            const response = await renameTag({
                path: { collection_id, tag_id: tag.tag_id },
                body: { name: newName }
            });

            if (response.error) {
                throw new Error('Failed to rename tag.');
            }

            cancelRename();
            loadTags();
        } catch {
            toast.error('Failed to rename tag. Please try again.');
        } finally {
            renamingTagId = null;
        }
    }
</script>

<Segment title="Tags">
    <div class="mb-3 w-full space-y-1">
        <div class="space-y-1">
            {#each $tags as tag (tag.tag_id)}
                {@const selectionCount = tagCounts?.get(tag.tag_id) ?? 0}
                <div
                    class={cn(
                        'group flex items-center gap-2 py-0.5',
                        tagCounts && selectionCount === 0 && 'opacity-50'
                    )}
                    data-testid="tag-menu-item"
                    data-onboarding-tag
                >
                    <div class="min-w-0 flex-1">
                        {#if editingTagId === tag.tag_id}
                            <TagRenameInput
                                {tag}
                                {renamingTagId}
                                tagsSelected={$tagsSelected}
                                onTagSelectionToggle={tagSelectionToggle}
                                onSave={handleRename}
                                onCancel={cancelRename}
                            />
                        {:else}
                            <Checkbox
                                name={tag.tag_id}
                                isChecked={$tagsSelected.has(tag.tag_id)}
                                label={tag.name}
                                onCheckedChange={() => tagSelectionToggle(tag.tag_id)}
                            />
                        {/if}
                    </div>
                    {#if tagCounts && editingTagId !== tag.tag_id}
                        <TagSelectionCount
                            tagName={tag.name}
                            count={selectionCount}
                            total={selectedIds.size}
                            canRemove={canManageTags && allowAssign}
                            busy={removingTagId === tag.tag_id}
                            onRemove={() => handleRemoveFromSelection(tag, selectionCount)}
                        />
                    {/if}
                    {#if canManageTags && editingTagId !== tag.tag_id}
                        <TagActionMenu
                            {tag}
                            open={openActionsTagId === tag.tag_id}
                            {deletingTagId}
                            {renamingTagId}
                            onOpenChange={(open) => {
                                openActionsTagId = open ? tag.tag_id : null;
                            }}
                            onCloseAutoFocus={(event) => {
                                if (suppressCloseAutoFocusTagId === tag.tag_id) {
                                    event.preventDefault();
                                    suppressCloseAutoFocusTagId = null;
                                }
                            }}
                            onRename={openRename}
                            onDelete={handleDeleteTag}
                        />
                    {/if}
                </div>
            {:else}
                <p>No tags yet</p>
            {/each}
        </div>

        {#if canManageTags && allowAssign}
            <TagAssignInput
                options={$tags}
                {hasSelection}
                busy={assignBusy}
                onSelect={handleAssign}
            />
        {/if}
    </div>
</Segment>
