<script lang="ts">
    import { Checkbox } from '$lib/components';
    import type { GridType } from '$lib/types';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Tags as Tagsicon } from '@lucide/svelte';
    import { useTags } from '$lib/hooks/useTags/useTags.js';

    let { collection_id, gridType }: Parameters<typeof useTags>[0] & { gridType: GridType } =
        $props();

    const { tags, tagsSelected, tagSelectionToggle } = $derived(
        useTags({
            collection_id,
            kind: [gridType === 'annotations' ? 'annotation' : 'sample']
        })
    );
</script>

<Segment title="Tags" icon={Tagsicon}>
    <div class="mb-3 w-full space-y-2">
        {#each $tags as tag (tag.tag_id)}
            <div class="flex items-center space-x-2 py-1" data-testid="tag-menu-item">
                <Checkbox
                    name={tag.tag_id}
                    isChecked={$tagsSelected.has(tag.tag_id)}
                    label={tag.name}
                    onCheckedChange={() => tagSelectionToggle(tag.tag_id)}
                />
            </div>
        {:else}
            <p>No tag, create a tag</p>
        {/each}
    </div>
</Segment>
