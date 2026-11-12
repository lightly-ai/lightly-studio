<script lang="ts">
    import { MetadataCategoricalFilter } from '$lib/components/MetadataCategoricalFilter';
    import type { MetadataValueCountsFilter } from '$lib/hooks/useCategoricalMetadataDistribution/useCategoricalMetadataDistribution.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { CategoricalMetadataValue } from '$lib/services/types';
    import { useCategoricalFieldCounts } from './useCategoricalFieldCounts.svelte';

    interface Props {
        collectionId: string;
        /** Tagged image or video filter. `undefined` counts all samples. */
        filter?: MetadataValueCountsFilter;
        /** The categorical fields to show, in display order. */
        fields: string[];
        isExpanded: (field: string) => boolean;
        onToggleExpanded: (field: string) => void;
        onValueToggle: (field: string, value: CategoricalMetadataValue) => void;
        onValuesSet: (field: string, values: CategoricalMetadataValue[]) => void;
        onValuesClear: (field: string) => void;
    }

    const {
        collectionId,
        filter,
        fields,
        isExpanded,
        onToggleExpanded,
        onValueToggle,
        onValuesSet,
        onValuesClear
    }: Props = $props();
    const { categoricalMetadataValues } = useGlobalStorage();

    // Only expanded fields show values, so only they are requested.
    const expandedFields = $derived(fields.filter((field) => isExpanded(field)));
    const counts = useCategoricalFieldCounts(() => ({
        collectionId,
        filter,
        fields: expandedFields
    }));
</script>

{#each fields as field (field)}
    {@const expanded = isExpanded(field)}
    <MetadataCategoricalFilter
        layout="list"
        fieldLabel={field}
        buckets={counts.distributions[field] ?? []}
        selectedValues={$categoricalMetadataValues[field] ?? []}
        {expanded}
        onToggleExpanded={() => onToggleExpanded(field)}
        loading={counts.loading}
        updating={expanded && counts.updating}
        error={expanded ? counts.error : undefined}
        onRetry={() => counts.refetch()}
        onToggle={(value) => onValueToggle(field, value)}
        onSetValues={(values) => onValuesSet(field, values)}
        onClear={() => onValuesClear(field)}
    />
{/each}
