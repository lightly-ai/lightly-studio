<script lang="ts">
    import { useTags, useAddTagToSample, useRemoveTagFromSample } from '$lib/hooks';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { useWorkflowFileContext } from '$lib/contexts/WorkflowFile.svelte';
    import { toast } from 'svelte-sonner';
    import AddTagPopover from '../AddTagPopover.svelte';
    import { TagChips } from '../TagChips';
    import type { TagItem } from '../types';
    import {
        getAddableTags,
        getAttachedTagNames,
        resolveTagSelection
    } from './resolveTagSelection';

    // The tags of one sample, with add and remove controls for users who may tag. An
    // annotation is a sample too: pass its sample id and annotation collection id.
    interface Props {
        tags: readonly TagItem[];
        collectionId: string;
        sampleId: string;
        onRefetch?: () => void;
        /** Classes of the wrapper, which is left out when there is nothing to show. */
        class?: string;
    }

    let {
        // Callers may pass the tags of a sample that has not loaded yet.
        tags = [],
        collectionId,
        sampleId,
        onRefetch = () => {},
        class: className = ''
    }: Props = $props();

    const { user } = useAuth();
    // A batch file's tags are locked like its annotations when it is not the user's turn.
    const workflow = useWorkflowFileContext();
    const canManageTags = $derived(
        hasMinimumRole(user?.role, 'labeler') && (workflow?.canEdit ?? true)
    );

    const { removeTagFromSample } = useRemoveTagFromSample({ getCollectionId: () => collectionId });

    let removingTagIds = $state(new Set<string>());

    async function handleRemoveTag(tagId: string) {
        removingTagIds = new Set(removingTagIds).add(tagId);
        try {
            await removeTagFromSample(sampleId, tagId);
        } catch {
            toast.error('Failed to remove tag. Please try again.');
            return;
        } finally {
            const remaining = new Set(removingTagIds);
            remaining.delete(tagId);
            removingTagIds = remaining;
        }
        onRefetch();
    }

    const { tags: allCollectionTags, loadTags } = $derived(
        useTags({ collection_id: collectionId })
    );

    const {
        busy: addTagBusy,
        addExisting,
        createAndAdd
    } = useAddTagToSample({
        getCollectionId: () => collectionId,
        getSampleId: () => sampleId,
        onRefetch: (...args) => onRefetch(...args),
        onTagsRefetch: () => loadTags()
    });

    const options = $derived(getAddableTags($allCollectionTags, tags));
    const attachedTagNames = $derived(getAttachedTagNames(tags));

    function handleSelect(name: string) {
        const selection = resolveTagSelection(name, options, attachedTagNames);
        if (selection.kind === 'existing') void addExisting(selection.tag);
        if (selection.kind === 'new') void createAndAdd(selection.name);
    }
</script>

{#if tags.length > 0 || canManageTags}
    <div class={className}>
        <TagChips
            {tags}
            onRemove={canManageTags ? (tagId) => void handleRemoveTag(tagId) : undefined}
            {removingTagIds}
        />
        {#if canManageTags}
            <AddTagPopover
                {options}
                {attachedTagNames}
                busy={$addTagBusy}
                onSelect={handleSelect}
            />
        {/if}
    </div>
{/if}
