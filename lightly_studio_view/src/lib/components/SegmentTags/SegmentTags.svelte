<script lang="ts">
    import { Segment } from '$lib/components';
    import { TagsIcon } from '@lucide/svelte';

    interface Tag {
        tag_id?: string;
        name: string;
    }

    const {
        tags,
        onClick
    }: {
        tags: Tag[];
        onClick: (tag_id: string) => Promise<void>;
    } = $props();
</script>

{#if tags.length > 0}
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
                            // TODO(Kondrat 17.03.2026): Fix the case when tag_id is undefined, we need proper TagView from the backend.
                            if (tag.tag_id) {
                                onClick(tag.tag_id);
                            }
                        }}
                    >
                        x
                    </button>
                </div>
            {/each}
        </div>
    </Segment>
{/if}
