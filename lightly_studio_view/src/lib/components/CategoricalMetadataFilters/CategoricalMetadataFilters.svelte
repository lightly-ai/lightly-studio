<script lang="ts">
    import { validate as validateUUID } from 'uuid';
    import CategoricalMetadataFieldPicker from '$lib/components/CategoricalMetadataFieldPicker/CategoricalMetadataFieldPicker.svelte';
    import { MetadataCategoricalFilter } from '$lib/components/MetadataCategoricalFilter';
    import { useCategoricalMetadataDistribution } from '$lib/hooks';
    import type { ImageFilter } from '$lib/api/lightly_studio_local';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { CategoricalMetadataValue } from '$lib/services/types';
    import { withAllValues } from './withAllValues';

    interface Props {
        collectionId: string;
        filter?: ImageFilter;
        categoricalKeys: string[];
        onValueToggle: (field: string, value: CategoricalMetadataValue) => void;
        onValuesSet: (field: string, values: CategoricalMetadataValue[]) => void;
        onValuesClear: (field: string) => void;
    }

    const {
        collectionId,
        filter,
        categoricalKeys,
        onValueToggle,
        onValuesSet,
        onValuesClear
    }: Props = $props();
    const { categoricalMetadataValues } = useGlobalStorage();

    let addedFields = $state<string[]>([]);

    const activeFields = $derived(
        categoricalKeys.filter((key) => $categoricalMetadataValues[key]?.length)
    );
    const visibleFields = $derived([
        ...new Set([...addedFields.filter((key) => categoricalKeys.includes(key)), ...activeFields])
    ]);
    const availableFields = $derived(
        categoricalKeys
            .filter((key) => !visibleFields.includes(key))
            .sort((a, b) => a.localeCompare(b))
    );
    const categoricalQuery = useCategoricalMetadataDistribution(() => ({
        collectionId,
        filter: { ...filter, filter_type: 'image' },
        fields: visibleFields,
        enabled: validateUUID(collectionId) && visibleFields.length > 0
    }));
    // Lists every value of each field; `categoricalQuery` only provides the counts.
    const allValuesQuery = useCategoricalMetadataDistribution(() => ({
        collectionId,
        filter: { filter_type: 'image' },
        fields: visibleFields,
        enabled: validateUUID(collectionId) && visibleFields.length > 0
    }));
    const distributions = $derived(categoricalQuery.data ?? {});
    const allValues = $derived(allValuesQuery.data ?? {});
    const loading = $derived(
        categoricalQuery.isFetching &&
            (categoricalQuery.isLoading || categoricalQuery.isPlaceholderData)
    );
    const updating = $derived(categoricalQuery.isFetching && !categoricalQuery.isLoading);

    const addField = (field: string): void => {
        addedFields = [...addedFields, field];
    };

    let collapsedFields = $state<Record<string, boolean>>({});
    const toggleExpanded = (field: string): void => {
        collapsedFields = { ...collapsedFields, [field]: !collapsedFields[field] };
    };

    const removeField = (field: string): void => {
        if ($categoricalMetadataValues[field]?.length) onValuesClear(field);
        addedFields = addedFields.filter((candidate) => candidate !== field);
    };
</script>

<CategoricalMetadataFieldPicker fields={availableFields} onAdd={addField} />

{#each visibleFields as field (field)}
    <MetadataCategoricalFilter
        layout="list"
        fieldLabel={field}
        buckets={withAllValues(distributions[field] ?? [], allValues[field] ?? [])}
        selectedValues={$categoricalMetadataValues[field] ?? []}
        {loading}
        {updating}
        error={categoricalQuery.error?.message}
        onRetry={() => categoricalQuery.refetch()}
        onToggle={(value) => onValueToggle(field, value)}
        onSetValues={(values) => onValuesSet(field, values)}
        onClear={() => onValuesClear(field)}
        onRemove={() => removeField(field)}
        expanded={!collapsedFields[field]}
        onToggleExpanded={() => toggleExpanded(field)}
    />
{/each}
