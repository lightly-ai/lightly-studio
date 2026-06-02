<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import * as Select from '$lib/components/ui/select';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import type {
        SimilarityParams,
        StrategyParams,
        StrategySummaryTag
    } from '$lib/hooks/useStrategyBuilder';
    import StrengthField from '../StrengthField/StrengthField.svelte';

    interface Props {
        params: SimilarityParams;
        tags: StrategySummaryTag[];
        onUpdate: (params: Partial<StrategyParams>) => void;
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
        <Select.Root
            type="single"
            name="similarity-query-tag"
            value={params.query_tag_id}
            onValueChange={(queryTagId) => onUpdate({ query_tag_id: queryTagId })}
        >
            <Select.Trigger class="w-full" data-testid="similarity-query-tag-select">
                {selectedQueryTagName}
            </Select.Trigger>
            <Select.Content>
                <Select.Group>
                    {#if tags.length === 0}
                        <div
                            class="py-1.5 pl-8 pr-2 text-sm italic text-muted-foreground"
                            data-testid="similarity-no-query-tags"
                        >
                            No sample tags available.
                        </div>
                    {:else}
                        {#each tags as tag (tag.tag_id)}
                            <Select.Item
                                value={tag.tag_id}
                                label={tag.name}
                                data-testid={`similarity-query-tag-${tag.tag_id}`}
                            >
                                {tag.name}
                            </Select.Item>
                        {/each}
                    {/if}
                </Select.Group>
            </Select.Content>
        </Select.Root>
    </div>

    <StrengthField
        strength={params.strength}
        id="similarity-strength"
        testid="strategy-similarity-strength-input"
        onUpdate={(strength) => onUpdate({ strength })}
    />
</div>
