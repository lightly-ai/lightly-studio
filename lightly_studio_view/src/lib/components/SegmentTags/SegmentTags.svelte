<script lang="ts">
    import { Button, Segment } from '$lib/components';
    import { TagsIcon, X } from '@lucide/svelte';
    import { SampleType } from '$lib/api/lightly_studio_local';
    import { useTags, useGlobalStorage, useAddTagToSample } from '$lib/hooks';
    import { useRemoveTagFromSample } from '$lib/hooks';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { toast } from 'svelte-sonner';
    import AddTagPopover from './AddTagPopover.svelte';

    interface TagItem {
        tag_id?: string;
        name: string;
    }

    interface Props {
        tags: TagItem[];
        collectionId: string;
        sampleId: string;
        onRefetch?: () => void;
    }

    let { tags, collectionId, sampleId, onRefetch = () => {} }: Props = $props();

    const { user } = useAuth();
    const canManageTags = $derived(hasMinimumRole(user?.role, 'labeler'));

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

    const { collections } = useGlobalStorage();
    const tagKind = $derived(
        $collections[collectionId]?.sampleType === SampleType.ANNOTATION ? 'annotation' : 'sample'
    );

    const { tags: allCollectionTags, loadTags } = $derived(
        useTags({ collection_id: collectionId, kind: [tagKind] })
    );

    const {
        busy: addTagBusy,
        addExisting,
        createAndAdd
    } = useAddTagToSample({
        getCollectionId: () => collectionId,
        getSampleId: () => sampleId,
        getTagKind: () => tagKind,
        onRefetch: (...args) => onRefetch(...args),
        onTagsRefetch: () => loadTags()
    });

    const options = $derived(
        $allCollectionTags.filter(
            (t) =>
                !tags.some(
                    (existing) =>
                        existing.tag_id === t.tag_id ||
                        existing.name.trim().toLowerCase() === t.name.trim().toLowerCase()
                )
        )
    );

    const attachedTagNames = $derived(new Set(tags.map((t) => t.name.trim().toLowerCase())));

    function handleSelect(name: string) {
        const trimmed = name.trim();
        const normalized = trimmed.toLowerCase();

        if (attachedTagNames.has(normalized)) return;

        const existing = options.find((t) => t.name.toLowerCase() === normalized);
        if (existing) {
            void addExisting(existing);
        } else {
            void createAndAdd(trimmed);
        }
    }
</script>

<Segment title="Tags" icon={TagsIcon}>
    <div class="flex flex-wrap gap-1">
        {#each tags as tag, index (tag.tag_id ?? `${tag.name}-${index}`)}
            <div class="inline-flex items-center gap-1 rounded-lg bg-card px-2 py-1 text-xs">
                <span data-testid="segment-tag-name">{tag.name}</span>
                {#if canManageTags && tag.tag_id}
                    <Button
                        icon={X}
                        ariaLabel={`Remove tag ${tag.name}`}
                        isPending={removingTagIds.has(tag.tag_id)}
                        buttonProps={{
                            size: 'sm',
                            class: 'size-6 rounded-full p-1 text-muted-foreground hover:text-destructive-text',
                            'data-testid': `remove-tag-${tag.name}`,
                            onclick: (event) => {
                                event.stopPropagation();
                                void handleRemoveTag(tag.tag_id!);
                            }
                        }}
                    />
                {/if}
            </div>
        {/each}
    </div>

    {#if canManageTags}
        <AddTagPopover {options} {attachedTagNames} busy={$addTagBusy} onSelect={handleSelect} />
    {/if}
</Segment>
