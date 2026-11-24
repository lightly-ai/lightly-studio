<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Label } from '$lib/components/ui/label';
    import type { ScopeTag } from '../TriggerEvaluationDialog.helpers';

    interface Props {
        /** Tags of the collection. */
        tags: ScopeTag[];
        /** Tags that select the evaluated images. Empty means all images. */
        selectedTagIds: string[];
    }

    let { tags, selectedTagIds = $bindable([]) }: Props = $props();

    const setSelected = (tagId: string, checked: boolean) => {
        selectedTagIds = checked
            ? [...selectedTagIds, tagId]
            : selectedTagIds.filter((id) => id !== tagId);
    };
</script>

<div class="grid gap-2" data-testid="evaluation-scope-field">
    <Label class="text-foreground">Images</Label>
    <p class="text-xs text-muted-foreground">
        {#if tags.length === 0}
            All images. Add tags to evaluate a subset.
        {:else if selectedTagIds.length === 0}
            All images
        {:else}
            Images with any of the selected tags
        {/if}
    </p>
    {#if tags.length > 0}
        <div class="flex max-h-32 flex-col gap-1.5 overflow-y-auto">
            {#each tags as tag (tag.tag_id)}
                <label class="flex items-center gap-2 text-sm">
                    <Checkbox
                        checked={selectedTagIds.includes(tag.tag_id)}
                        onCheckedChange={(checked) => setSelected(tag.tag_id, checked === true)}
                        aria-label={tag.name}
                    />
                    {tag.name}
                </label>
            {/each}
        </div>
    {/if}
</div>
