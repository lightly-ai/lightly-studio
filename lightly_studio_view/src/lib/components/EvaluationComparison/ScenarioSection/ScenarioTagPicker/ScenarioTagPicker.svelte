<script lang="ts">
    import type { TagView } from '$lib/api/lightly_studio_local';
    import { Checkbox } from '$lib/components/ui/checkbox';

    interface Props {
        tags: Pick<TagView, 'tag_id' | 'name'>[];
        selectedTagIds: string[];
        onSelectedTagIdsChange: (tagIds: string[]) => void;
    }

    const { tags, selectedTagIds, onSelectedTagIdsChange }: Props = $props();

    const setSelected = (tagId: string, checked: boolean) =>
        onSelectedTagIdsChange(
            checked ? [...selectedTagIds, tagId] : selectedTagIds.filter((id) => id !== tagId)
        );
</script>

<div class="flex flex-wrap gap-x-4 gap-y-2" data-testid="scenario-tag-picker">
    {#each tags as tag (tag.tag_id)}
        <label class="flex items-center gap-2 text-sm">
            <Checkbox
                checked={selectedTagIds.includes(tag.tag_id)}
                onCheckedChange={(checked) => setSelected(tag.tag_id, checked === true)}
                aria-label={tag.name}
            />
            {tag.name}
        </label>
    {:else}
        <p class="text-sm text-muted-foreground">Add tags to compare the runs on subsets.</p>
    {/each}
</div>
