<script lang="ts">
    import { Segment } from '$lib/components';
    import { TagsIcon } from '@lucide/svelte';
    import { toast } from 'svelte-sonner';

    interface Tag {
        tagId: string;
        name: string;
    }

    const {
        tags,
        onClick
    }: {
        tags: Tag[];
        onClick: (tagId: string) => Promise<void>;
    } = $props();

    const handleRemoveTag = async (tagId: string) => {
        try {
            await onClick(tagId);
            toast.success('Tag removed successfully');
        } catch (error) {
            toast.error('Failed to remove tag. Please try again.');
            console.error('Error removing tag from sample:', error);
        }
    };
</script>

{#if tags.length > 0}
    <Segment title="Tags" icon={TagsIcon}>
        <div class="flex flex-wrap gap-1">
            {#each tags as tag (tag.tagId)}
                <div class="inline-flex items-center gap-1 rounded-lg bg-card px-2 py-1 text-xs">
                    <span data-testid="segment-tag-name">{tag.name}</span>
                    <button
                        type="button"
                        class="flex size-4 items-center justify-center rounded-full text-muted-foreground transition hover:text-destructive focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                        aria-label={`Remove tag ${tag.name}`}
                        onclick={(event) => {
                            event.stopPropagation();
                            handleRemoveTag(tag.tagId);
                        }}
                    >
                        x
                    </button>
                </div>
            {/each}
        </div>
    </Segment>
{/if}
