<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import { Select, SelectMenuItem } from '$lib/components/Select';

    interface Tag {
        tag_id: string;
        name: string;
    }

    interface Props {
        queryTagId: string;
        tags: Tag[];
        onQueryTagChange: (tagId: string) => void;
    }

    let { queryTagId, tags, onQueryTagChange }: Props = $props();

    const selectedQueryTagName = $derived(
        tags.find((tag) => tag.tag_id === queryTagId)?.name ?? 'Select tag'
    );
</script>

<div class="grid grid-cols-4 items-center gap-4">
    <Label for="query-tag" class="text-right text-foreground">Query Tag</Label>
    <Select
        value={queryTagId}
        triggerLabel={selectedQueryTagName}
        class="col-span-3"
        testId="sampling-dialog-query-tag-select"
        onValueChange={onQueryTagChange}
    >
        {#snippet children()}
            {#if tags.length === 0}
                <div
                    class="py-1.5 pl-8 pr-2 text-sm italic text-muted-foreground"
                    data-testid="sampling-dialog-no-query-tags"
                >
                    No sample tags available.
                </div>
            {:else}
                {#each tags as tag (tag.tag_id)}
                    <SelectMenuItem
                        value={tag.tag_id}
                        label={tag.name}
                        data-testid={`sampling-query-tag-${tag.tag_id}`}
                    >
                        {tag.name}
                    </SelectMenuItem>
                {/each}
            {/if}
        {/snippet}
    </Select>
</div>
