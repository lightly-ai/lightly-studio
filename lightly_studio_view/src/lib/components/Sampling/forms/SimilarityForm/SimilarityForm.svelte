<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import { Select, SelectMenuItem } from '$lib/components/Select';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import type { SimilarityParams, StrategySummaryTag } from '$lib/hooks/useStrategyBuilder';
    import StrengthField from '../StrengthField/StrengthField.svelte';

    interface Props {
        params: SimilarityParams;
        tags: StrategySummaryTag[];
        onUpdate: (params: Partial<SimilarityParams>) => void;
    }
    let { params, tags, onUpdate }: Props = $props();
    const selectedQueryTagName = $derived(
        tags.find((tag) => tag.tag_id === params.query_tag_id)?.name ?? 'Select tag'
    );
</script>

<div class="grid gap-3" data-testid="similarity-form">
    <div class="grid gap-2">
        <div class="flex items-center gap-1.5">
            <Label for="similarity-query-tag">Query Tag</Label>
            <FieldTooltip
                content="Samples in this tag serve as the similarity reference. The strategy selects samples most similar to them."
            />
        </div>
        <Select
            value={params.query_tag_id}
            triggerLabel={selectedQueryTagName}
            class="w-full"
            testId="similarity-query-tag-select"
            onValueChange={(queryTagId) => onUpdate({ query_tag_id: queryTagId })}
        >
            {#snippet children()}
                {#if tags.length === 0}
                    <div
                        class="py-1.5 pl-8 pr-2 text-sm italic text-muted-foreground"
                        data-testid="similarity-no-query-tags"
                    >
                        No sample tags available.
                    </div>
                {:else}
                    {#each tags as tag (tag.tag_id)}
                        <SelectMenuItem
                            value={tag.tag_id}
                            label={tag.name}
                            data-testid={`similarity-query-tag-${tag.tag_id}`}
                        >
                            {tag.name}
                        </SelectMenuItem>
                    {/each}
                {/if}
            {/snippet}
        </Select>
    </div>

    <StrengthField
        strength={params.strength}
        id="similarity-strength"
        testid="strategy-similarity-strength-input"
        onUpdate={(strength) => onUpdate({ strength })}
    />
</div>
