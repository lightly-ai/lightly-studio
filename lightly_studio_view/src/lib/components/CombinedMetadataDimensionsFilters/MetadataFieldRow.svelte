<script lang="ts">
    import { MetadataCategoricalFilter } from '$lib/components/MetadataCategoricalFilter';
    import type { useCategoricalFieldCounts } from '$lib/components/CategoricalMetadataFilters/useCategoricalFieldCounts.svelte';
    import type { CategoricalMetadataValue } from '$lib/services/types';
    import MetadataFilterItem from './MetadataFilterItem/MetadataFilterItem.svelte';
    import {
        formatRangeSummary,
        isFieldActive,
        type MetadataField,
        type Range
    } from './metadataFields';

    interface Props {
        field: MetadataField;
        expanded: boolean;
        onToggleExpanded: () => void;
        /** Value counts of the categorical fields. */
        counts: ReturnType<typeof useCategoricalFieldCounts>;
        onCommitRange: (range: Range) => void;
        /** Removes the filter of the field. */
        onReset: () => void;
        onCategoricalValueToggle: (field: string, value: CategoricalMetadataValue) => void;
        onCategoricalValuesSet: (field: string, values: CategoricalMetadataValue[]) => void;
        onCategoricalValuesClear: (field: string) => void;
    }

    const {
        field,
        expanded,
        onToggleExpanded,
        counts,
        onCommitRange,
        onReset,
        onCategoricalValueToggle,
        onCategoricalValuesSet,
        onCategoricalValuesClear
    }: Props = $props();
</script>

{#if field.kind === 'range'}
    <MetadataFilterItem
        metadataKey={field.key}
        title={field.title}
        unit={field.unit}
        bound={field.bound}
        value={field.value}
        onValueCommit={(_, [min, max]) => onCommitRange({ min, max })}
        {expanded}
        {onToggleExpanded}
        checked={isFieldActive(field)}
        summary={formatRangeSummary(field)}
        onClear={onReset}
    />
{:else}
    <MetadataCategoricalFilter
        layout="list"
        fieldLabel={field.title}
        buckets={counts.distributions[field.key] ?? []}
        selectedValues={field.selected}
        {expanded}
        {onToggleExpanded}
        loading={counts.loading}
        updating={expanded && counts.updating}
        error={expanded ? counts.error : undefined}
        onRetry={() => counts.refetch()}
        onToggle={(value) => onCategoricalValueToggle(field.key, value)}
        onSetValues={(values) => onCategoricalValuesSet(field.key, values)}
        onClear={() => onCategoricalValuesClear(field.key)}
        checked={isFieldActive(field)}
        onClearField={onReset}
    />
{/if}
