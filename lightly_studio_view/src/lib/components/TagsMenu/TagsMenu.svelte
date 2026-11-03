<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { FilterList } from '$lib/components/FilterList';
    import type { TagView } from '$lib/services/types';
    import { useTags } from '$lib/hooks/useTags/useTags.js';
    import { deleteTag, renameTag } from '$lib/api/lightly_studio_local';
    import { ItemRenameInput } from '$lib/components/ItemRenameInput';
    import { ItemActionMenu } from '$lib/components/ItemActionMenu';
    import { toast } from 'svelte-sonner';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';

    let { collection_id }: Parameters<typeof useTags>[0] = $props();

    const { tags, tagsSelected, tagSelectionToggle, setTagSelected, loadTags, clearTagSelected } =
        $derived(useTags({ collection_id }));

    const tagById = $derived(new Map($tags.map((tag) => [tag.tag_id, tag])));
    const tagItems = $derived(
        $tags.map((tag) => ({
            id: tag.tag_id,
            label: tag.name,
            selected: $tagsSelected.has(tag.tag_id)
        }))
    );
    const handleSelectionChange = (ids: string[]) => {
        $tags.forEach((tag) => setTagSelected(tag.tag_id, ids.includes(tag.tag_id)));
    };

    const { user } = useAuth();
    const canManageTags = $derived(hasMinimumRole(user?.role, 'labeler'));

    let deletingTagId = $state<string | null>(null);
    let editingTagId = $state<string | null>(null);
    let renamingTagId = $state<string | null>(null);
    let openActionsTagId = $state<string | null>(null);
    let suppressCloseAutoFocusTagId = $state<string | null>(null);

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
    <div class="mb-3 w-full space-y-2">
        <FilterList
            items={tagItems}
            onToggle={tagSelectionToggle}
            onSelectionChange={handleSelectionChange}
            testId="tags-menu"
            searchPlaceholder="Search tags…"
            showSearch={tagItems.length > 0}
            emptyText="No tags yet"
            customRowId={editingTagId}
        >
            {#snippet customRow(item)}
                {@const tag = tagById.get(item.id)!}
                <ItemRenameInput
                    id={tag.tag_id}
                    name={tag.name}
                    kind="tag"
                    renamingId={renamingTagId}
                    checked={$tagsSelected.has(tag.tag_id)}
                    onCheckedChange={() => tagSelectionToggle(tag.tag_id)}
                    onSave={(newName) => handleRename(tag, newName)}
                    onCancel={cancelRename}
                />
            {/snippet}
            {#snippet trailing(item)}
                {@const tag = tagById.get(item.id)!}
                {#if canManageTags}
                    <ItemActionMenu
                        id={tag.tag_id}
                        name={tag.name}
                        kind="tag"
                        open={openActionsTagId === tag.tag_id}
                        deletingId={deletingTagId}
                        renamingId={renamingTagId}
                        onOpenChange={(open) => {
                            openActionsTagId = open ? tag.tag_id : null;
                        }}
                        onCloseAutoFocus={(event) => {
                            if (suppressCloseAutoFocusTagId === tag.tag_id) {
                                event.preventDefault();
                                suppressCloseAutoFocusTagId = null;
                            }
                        }}
                        onRename={(event) => openRename(tag, event)}
                        onDelete={(event) => handleDeleteTag(tag, event)}
                    />
                {/if}
            {/snippet}
        </FilterList>
    </div>
</Segment>
