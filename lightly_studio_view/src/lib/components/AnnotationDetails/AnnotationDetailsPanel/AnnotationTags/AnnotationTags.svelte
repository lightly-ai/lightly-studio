<script lang="ts">
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { Segment } from '$lib/components';
    import { TagsIcon } from '@lucide/svelte';

    const {
        annotation
    }: {
        annotation: AnnotationView;
    } = $props();

    const tags = $derived(annotation.tags ?? []);
</script>

{#if tags.length > 0}
    <Segment title="Tags" icon={TagsIcon}>
        <div class="flex flex-wrap gap-1">
            {#each tags as tag (tag.tag_id)}
                <div class="inline-flex items-center gap-1 rounded-lg bg-card px-2 py-1 text-xs">
                    <span>{tag.name}</span>
                </div>
            {/each}
        </div>
    </Segment>
{/if}
