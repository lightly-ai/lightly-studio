<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import * as Select from '$lib/components/ui/select';

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
    <Select.Root type="single" name="query-tag" value={queryTagId} onValueChange={onQueryTagChange}>
        <Select.Trigger class="col-span-3" data-testid="selection-dialog-query-tag-select">
            {selectedQueryTagName}
        </Select.Trigger>
        <Select.Content>
            <Select.Group>
                {#if tags.length === 0}
                    <div
                        class="py-1.5 pl-8 pr-2 text-sm italic text-muted-foreground"
                        data-testid="selection-dialog-no-query-tags"
                    >
                        No sample tags available.
                    </div>
                {:else}
                    {#each tags as tag (tag.tag_id)}
                        <Select.Item
                            value={tag.tag_id}
                            label={tag.name}
                            data-testid={`selection-query-tag-${tag.tag_id}`}
                        >
                            {tag.name}
                        </Select.Item>
                    {/each}
                {/if}
            </Select.Group>
        </Select.Content>
    </Select.Root>
</div>
