<script lang="ts">
    import type { GridType } from '$lib/types';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Checkbox } from '$lib/components';
    import { Tags as Tagsicon } from '@lucide/svelte';
    import type { TagView } from '$lib/services/types';
    import { useTags } from '$lib/hooks/useTags/useTags.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import {
        createTag,
        addSampleIdsToTagId,
        deleteTag,
        renameTag
    } from '$lib/api/lightly_studio_local';
    import TagAssignInput from './TagAssignInput.svelte';
    import TagRenameInput from './TagRenameInput.svelte';
    import TagActionMenu from './TagActionMenu.svelte';
    import { toast } from 'svelte-sonner';

    let { collection_id, gridType }: Parameters<typeof useTags>[0] & { gridType: GridType } =
        $props();

    const tagKind = $derived(gridType === 'annotations' ? 'annotation' : 'sample');

    const { tags, tagsSelected, tagSelectionToggle, loadTags, clearTagSelected } = $derived(
        useTags({ collection_id, kind: [tagKind] })
    );

    const { getSelectedSampleIds, selectedSampleAnnotationCropIds } = useGlobalStorage();

    const selectedSampleIds = $derived(getSelectedSampleIds(collection_id));
    const hasSelection = $derived(
        tagKind === 'annotation'
            ? ($selectedSampleAnnotationCropIds[collection_id]?.size ?? 0) > 0
            : $selectedSampleIds.size > 0
    );
    const selectedIds = $derived(
        tagKind === 'annotation'
            ? ($selectedSampleAnnotationCropIds[collection_id] ?? new Set<string>())
            : $selectedSampleIds
    );

    let assignBusy = $state(false);
    let deletingTagId = $state<string | null>(null);
    let editingTagId = $state<string | null>(null);
    let renamingTagId = $state<string | null>(null);
    let openActionsTagId = $state<string | null>(null);
    let suppressCloseAutoFocusTagId = $state<string | null>(null);

    async function handleAssign(name: string) {
        assignBusy = true;
        try {
            const existingTag = $tags.find(
                (t: TagView) => t.name.toLowerCase() === name.toLowerCase()
            );
            if (existingTag) {
                const response = await addSampleIdsToTagId({
                    path: { collection_id, tag_id: existingTag.tag_id },
                    body: { sample_ids: [...selectedIds] }
                });
                if (response.error) {
                    toast.error('Failed to assign tag. Please try again.');
                    return;
                }
            } else {
                const createResponse = await createTag({
                    path: { collection_id },
                    body: { name, kind: tagKind }
                });
                if (createResponse.error || !createResponse.data?.tag_id) {
                    toast.error('Failed to create tag. Please try again.');
                    return;
                }
                const assignResponse = await addSampleIdsToTagId({
                    path: { collection_id, tag_id: createResponse.data.tag_id },
                    body: { sample_ids: [...selectedIds] }
                });
                if (assignResponse.error) {
                    toast.error('Failed to assign tag. Please try again.');
                    return;
                }
            }
            loadTags();
        } catch (error) {
            console.error('Failed to assign tag', error);
            toast.error('Failed to assign tag. Please try again.');
        } finally {
            assignBusy = false;
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

<Segment title="Tags" icon={Tagsicon}>
    <div class="mb-3 w-full space-y-1">
        <div class="space-y-1">
            {#each $tags as tag (tag.tag_id)}
                <div class="flex items-center gap-2 py-0.5" data-testid="tag-menu-item">
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
                    {#if editingTagId !== tag.tag_id}
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

        <TagAssignInput
            options={$tags}
            busy={assignBusy || !hasSelection}
            showSelectionHint={!hasSelection}
            onSelect={handleAssign}
        />
    </div>
</Segment>
