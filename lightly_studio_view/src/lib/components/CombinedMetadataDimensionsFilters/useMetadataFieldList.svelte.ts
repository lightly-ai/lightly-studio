import { fromStore } from 'svelte/store';
import { usePostHog } from '$lib/hooks';
import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import {
    fieldId,
    isFieldActive,
    type CategoricalField,
    type MetadataField,
    type Range,
    type RangeField,
    type RangeSource
} from './metadataFields';

export interface UseMetadataFieldListParams {
    getCollectionId: () => string;
    getShowImageDimensions: () => boolean;
    getCategoricalKeys: () => string[];
    /** Called after a range commit, for the existing range analytics. */
    onRangeCommitted?: (key: string, min: number, max: number) => void;
}

export interface UseMetadataFieldListReturn {
    /** All fields in default order: dimensions, numeric, categorical. */
    readonly fields: MetadataField[];
    commitRange: (id: string, range: Range) => void;
    reset: (id: string) => void;
    resetAll: () => void;
}

const rangeField = (
    source: RangeField['source'],
    key: string,
    title: string,
    unit: string,
    bound: Range,
    value: Range
): RangeField => ({
    kind: 'range',
    id: fieldId(source, key),
    source,
    key,
    title,
    unit,
    bound: { min: bound.min, max: bound.max },
    value: { min: value.min, max: value.max }
});

export function useMetadataFieldList(
    params: UseMetadataFieldListParams
): UseMetadataFieldListReturn {
    const { trackEvent } = usePostHog();

    const dimensions = useDimensions();
    const dimensionsBounds = fromStore(dimensions.dimensionsBounds);
    const dimensionsValues = fromStore(dimensions.dimensionsValues);

    const metadataStores = useMetadataFilters();
    const metadataBounds = fromStore(metadataStores.metadataBounds);
    const metadataValues = fromStore(metadataStores.metadataValues);
    const categoricalValues = fromStore(metadataStores.categoricalMetadataValues);

    // The metadata hook fetches its bounds when given a collection id.
    $effect(() => {
        useMetadataFilters(params.getCollectionId());
    });

    const dimensionFields = (): RangeField[] => {
        const bounds = dimensionsBounds.current;
        const values = dimensionsValues.current;
        if (!params.getShowImageDimensions() || !bounds || !values) return [];
        return [
            rangeField(
                'dimension',
                'width',
                'Width',
                'px',
                { min: bounds.min_width, max: bounds.max_width },
                { min: values.min_width, max: values.max_width }
            ),
            rangeField(
                'dimension',
                'height',
                'Height',
                'px',
                { min: bounds.min_height, max: bounds.max_height },
                { min: values.min_height, max: values.max_height }
            )
        ];
    };

    const numericFields = (): RangeField[] =>
        Object.keys(metadataBounds.current).flatMap((key) => {
            const bound = metadataBounds.current[key];
            const value = metadataValues.current[key];
            const isNumeric =
                bound &&
                value &&
                typeof bound.min === 'number' &&
                typeof bound.max === 'number' &&
                typeof value.min === 'number' &&
                typeof value.max === 'number';
            return isNumeric ? [rangeField('numeric', key, key, '', bound, value)] : [];
        });

    const categoricalFields = (): CategoricalField[] =>
        params.getCategoricalKeys().map((key) => ({
            kind: 'categorical',
            id: fieldId('categorical', key),
            source: 'categorical',
            key,
            title: key,
            selected: categoricalValues.current[key] ?? []
        }));

    const fields = $derived<MetadataField[]>([
        ...dimensionFields(),
        ...numericFields(),
        ...categoricalFields()
    ]);

    type RangeUpdate = { field: RangeField; range: Range };

    const writeRanges = (updates: RangeUpdate[]): void => {
        const ofSource = (source: RangeSource) =>
            updates.filter(({ field }) => field.source === source);
        const merge = (source: RangeSource) =>
            Object.fromEntries(
                ofSource(source).map(({ field, range }) => [
                    field.key,
                    { min: range.min, max: range.max }
                ])
            );

        const dimensionUpdates = ofSource('dimension');
        const dimensionValues = dimensionsValues.current;
        if (dimensionUpdates.length > 0 && dimensionValues) {
            const next = { ...dimensionValues };
            for (const { field, range } of dimensionUpdates) {
                if (field.key === 'width') {
                    next.min_width = range.min;
                    next.max_width = range.max;
                } else {
                    next.min_height = range.min;
                    next.max_height = range.max;
                }
            }
            dimensions.updateDimensionsValues(next);
        }
        if (ofSource('numeric').length > 0) {
            metadataStores.updateMetadataValues({ ...metadataValues.current, ...merge('numeric') });
        }
    };

    const findField = (id: string): MetadataField | undefined =>
        fields.find((field) => field.id === id);

    const commitRange = (id: string, range: Range): void => {
        const field = findField(id);
        if (field?.kind !== 'range') return;
        writeRanges([{ field, range }]);
        params.onRangeCommitted?.(field.key, range.min, range.max);
    };

    const resetFields = (targets: MetadataField[]): void => {
        writeRanges(
            targets.flatMap((field) =>
                field.kind === 'range' ? [{ field, range: field.bound }] : []
            )
        );
        const categorical = targets.filter((field) => field.kind === 'categorical');
        if (categorical.length > 0) {
            const remaining = { ...categoricalValues.current };
            for (const field of categorical) delete remaining[field.key];
            metadataStores.updateCategoricalMetadataValues(remaining);
        }
        for (const field of targets) {
            trackEvent('metadata_filter_changed', {
                collection_id: params.getCollectionId(),
                field_name: field.key,
                source: field.source,
                action: 'disabled'
            });
        }
    };

    const reset = (id: string): void => {
        const field = findField(id);
        if (field) resetFields([field]);
    };

    const resetAll = (): void => resetFields(fields.filter(isFieldActive));

    return {
        get fields() {
            return fields;
        },
        commitRange,
        reset,
        resetAll
    };
}
