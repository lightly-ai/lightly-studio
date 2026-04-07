<script lang="ts">
    import { Segment } from '$lib/components';
    import { TagsIcon } from '@lucide/svelte';
    import { useRemoveTagFromSample } from '$lib/hooks/useRemoveTagFromSample/useRemoveTagFromSample';
    import { toast } from 'svelte-sonner';

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

    let {
        tags,
        collectionId,
        sampleId,
        onRefetch = () => {}
    }: Props = $props();

    const { removeTagFromSample } = useRemoveTagFromSample({ collectionId });

    async function handleRemoveTag(tagId: string) {
        try {
            await removeTagFromSample(sampleId, tagId);
        } catch {
            toast.error('Failed to remove tag. Please try again.');
            return;
        }
        onRefetch();
    }
</script>

<Segment title="Tags" icon={TagsIcon}>
    <div class="flex flex-wrap gap-1">
        {#each tags as tag (tag.tag_id)}
            <div class="inline-flex items-center gap-1 rounded-lg bg-card px-2 py-1 text-xs">
                <span data-testid="segment-tag-name">{tag.name}</span>
                <button
                    type="button"
                    class="flex size-4 items-center justify-center rounded-full text-muted-foreground transition hover:text-destructive focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                    aria-label={`Remove tag ${tag.name}`}
                    data-testid={`remove-tag-${tag.name}`}
                    onclick={(event) => {
                        event.stopPropagation();
                        if (tag.tag_id) void handleRemoveTag(tag.tag_id);
                    }}
                >
                    x
                </button>
            </div>
        {/each}
    </div>
</Segment>
