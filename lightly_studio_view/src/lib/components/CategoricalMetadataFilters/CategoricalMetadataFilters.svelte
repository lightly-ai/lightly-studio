<script lang="ts">
    import { getErrorMessage } from '$lib/utils';
    import { validate as validateUUID } from 'uuid';
    import { MetadataCategoricalFilter } from '$lib/components/MetadataCategoricalFilter';
    import { useCategoricalMetadataDistribution } from '$lib/hooks';
    import type { ImageFilter } from '$lib/api/lightly_studio_local';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { CategoricalMetadataValue } from '$lib/services/types';

    interface Props {
        collectionId: string;
        filter?: ImageFilter;
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
    const categoricalQuery = useCategoricalMetadataDistribution(() => ({
        collectionId,
        filter: { ...filter, filter_type: 'image' },
        fields: expandedFields,
        enabled: validateUUID(collectionId) && expandedFields.length > 0
    }));
    const distributions = $derived(categoricalQuery.data ?? {});
    const loading = $derived(
        categoricalQuery.isFetching &&
            (categoricalQuery.isLoading || categoricalQuery.isPlaceholderData)
    );
    const updating = $derived(categoricalQuery.isFetching && !categoricalQuery.isLoading);
</script>

{#each fields as field (field)}
    {@const expanded = isExpanded(field)}
    <MetadataCategoricalFilter
        layout="list"
        fieldLabel={field}
        buckets={distributions[field] ?? []}
        selectedValues={$categoricalMetadataValues[field] ?? []}
        {expanded}
        onToggleExpanded={() => onToggleExpanded(field)}
        {loading}
        updating={expanded && updating}
        error={expanded ? getErrorMessage(categoricalQuery.error) : undefined}
        onRetry={() => categoricalQuery.refetch()}
        onToggle={(value) => onValueToggle(field, value)}
        onSetValues={(values) => onValuesSet(field, values)}
        onClear={() => onValuesClear(field)}
    />
{/each}
