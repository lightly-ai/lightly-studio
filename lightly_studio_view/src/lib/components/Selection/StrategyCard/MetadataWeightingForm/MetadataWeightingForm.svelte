<script lang="ts">
    import { page } from '$app/state';
    import { Label } from '$lib/components/ui/label';
    import { Input } from '$lib/components/ui/input';
    import * as Select from '$lib/components/ui/select';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import type {
        MetadataWeightingParams,
        StrategyParams
    } from '../../useStrategyBuilder/useStrategyBuilder';

    interface Props {
        params: MetadataWeightingParams;
        onUpdate: (params: Partial<StrategyParams>) => void;
    }

    let { params, onUpdate }: Props = $props();

    const collectionId = $derived(page.params.collection_id!);
    const { metadataInfo } = $derived(useMetadataFilters(collectionId));
</script>

<div class="grid gap-3" data-testid="metadata-weighting-form">
    <div class="grid gap-2">
        <Label for="metadata-weighting-key">Metadata Key</Label>
        {#if $metadataInfo.length > 0}
            <Select.Root
                type="single"
                name="metadata-weighting-key"
                value={params.metadata_key}
                onValueChange={(value) => onUpdate({ metadata_key: value })}
            >
                <Select.Trigger class="w-full" data-testid="strategy-metadata-key-input">
                    {params.metadata_key || 'Select a metadata field'}
                </Select.Trigger>
                <Select.Content>
                    <Select.Group>
                        {#each $metadataInfo as field (field.name)}
                            <Select.Item value={field.name} label={field.name}>
                                {field.name}
                            </Select.Item>
                        {/each}
                    </Select.Group>
                </Select.Content>
            </Select.Root>
        {:else}
            <Input
                id="metadata-weighting-key"
                value={params.metadata_key}
                placeholder="weather"
                oninput={(event) =>
                    onUpdate({ metadata_key: (event.currentTarget as HTMLInputElement).value })}
                data-testid="strategy-metadata-key-input"
            />
        {/if}
    </div>
    <div class="grid gap-2">
        <Label for="metadata-weighting-strength">Strength</Label>
        <Input
            id="metadata-weighting-strength"
            type="number"
            min="0"
            step="0.1"
            value={params.strength}
            oninput={(event) =>
                onUpdate({ strength: Number((event.currentTarget as HTMLInputElement).value) })}
            data-testid="strategy-metadata-strength-input"
        />
    </div>
</div>
