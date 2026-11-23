import { fromStore } from 'svelte/store';
import {
    useDimensions,
    useMetadataFilters,
    usePostHog,
    useVideoBounds,
    useVideoFramesBounds
} from '$lib/hooks';
import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
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
    getIsVideos: () => boolean;
    getIsVideoFrames: () => boolean;
    getCategoricalKeys: () => string[];
    /** Called after a range commit, for the existing range analytics. */
    onRangeCommitted?: (key: string, min: number, max: number) => void;
}

export interface UseMetadataFieldListReturn {
    /** All fields in default order: dimensions, video, frame number, numeric, categorical. */
    readonly fields: MetadataField[];
    commitRange: (id: string, range: Range) => void;
    reset: (id: string) => void;
    resetAll: () => void;
}

interface RangeUpdate {
    field: RangeField;
    range: Range;
}

const rangeField = ({ bound, value, ...field }: Omit<RangeField, 'kind' | 'id'>): RangeField => ({
    ...field,
    kind: 'range',
    id: fieldId(field.source, field.key),
    bound: { min: bound.min, max: bound.max },
    value: { min: value.min, max: value.max }
});

const withDimensionRange = (
    values: DimensionBounds,
    { field, range }: RangeUpdate
): DimensionBounds => {
    if (field.key === 'width') return { ...values, min_width: range.min, max_width: range.max };
    if (field.key === 'height') return { ...values, min_height: range.min, max_height: range.max };
    return values;
};

export function useMetadataFieldList(
    params: UseMetadataFieldListParams
): UseMetadataFieldListReturn {
    const { trackEvent } = usePostHog();

    const dimensions = useDimensions();
    const dimensionsBounds = fromStore(dimensions.dimensionsBounds);
    const dimensionsValues = fromStore(dimensions.dimensionsValues);

    const videoStores = useVideoBounds();
    const videoBounds = fromStore(videoStores.videoBounds);
    const videoValues = fromStore(videoStores.videoBoundsValues);

    const frameStores = useVideoFramesBounds();
    const frameBounds = fromStore(frameStores.videoFramesBounds);
    const frameValues = fromStore(frameStores.videoFramesBoundsValues);

    const metadataStores = useMetadataFilters();
    const metadataBounds = fromStore(metadataStores.metadataBounds);
    const metadataValues = fromStore(metadataStores.metadataValues);
    const metadataInfo = fromStore(metadataStores.metadataInfo);
    const categoricalValues = fromStore(metadataStores.categoricalMetadataValues);

    // The video hooks and the metadata hook fetch their bounds when given a collection id.
    $effect(() => {
        const collectionId = params.getCollectionId();
        if (params.getIsVideos()) useVideoBounds(collectionId);
        if (params.getIsVideoFrames()) useVideoFramesBounds(collectionId);
        useMetadataFilters(collectionId);
    });

    const dimensionFields = (): RangeField[] => {
        const bounds = dimensionsBounds.current;
        const values = dimensionsValues.current;
        if (!params.getShowImageDimensions() || !bounds || !values) return [];
        return [
            rangeField({
                source: 'dimension',
                key: 'width',
                title: 'Width',
                unit: 'px',
                integer: true,
                bound: { min: bounds.min_width, max: bounds.max_width },
                value: { min: values.min_width, max: values.max_width }
            }),
            rangeField({
                source: 'dimension',
                key: 'height',
                title: 'Height',
                unit: 'px',
                integer: true,
                bound: { min: bounds.min_height, max: bounds.max_height },
                value: { min: values.min_height, max: values.max_height }
            })
        ];
    };

    const videoFields = (): RangeField[] => {
        const bounds = videoBounds.current;
        const values = videoValues.current;
        if (!params.getIsVideos() || !bounds || !values) return [];
        const field = (key: 'width' | 'height' | 'fps' | 'duration_s', title: string, unit = '') =>
            rangeField({
                source: 'video',
                key,
                title,
                unit,
                integer: key === 'width' || key === 'height',
                bound: bounds[key],
                value: values[key]
            });
        return [
            field('width', 'Width', 'px'),
            field('height', 'Height', 'px'),
            ...(bounds.fps.min !== bounds.fps.max ? [field('fps', 'FPS')] : []),
            field('duration_s', 'Duration', 's')
        ];
    };

    const frameFields = (): RangeField[] => {
        const bounds = frameBounds.current;
        const values = frameValues.current;
        if (!params.getIsVideoFrames() || !bounds || !values) return [];
        return [
            rangeField({
                source: 'frame',
                key: 'frame_number',
                title: 'Frame number',
                unit: '',
                integer: true,
                bound: bounds.frame_number,
                value: values.frame_number
            })
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
            if (!isNumeric) return [];
            const type = metadataInfo.current.find((info) => info.name === key)?.type;
            return [
                rangeField({
                    source: 'numeric',
                    key,
                    title: key,
                    unit: '',
                    integer: type === 'integer',
                    bound,
                    value
                })
            ];
        });

    // A metadata key can be any string, e.g. `constructor`, so read only own keys.
    const selectedValues = (key: string) =>
        Object.hasOwn(categoricalValues.current, key) ? categoricalValues.current[key] : [];

    const categoricalFields = (): CategoricalField[] =>
        params.getCategoricalKeys().map((key) => ({
            kind: 'categorical',
            id: fieldId('categorical', key),
            source: 'categorical',
            key,
            title: key,
            selected: selectedValues(key)
        }));

    const fields = $derived<MetadataField[]>([
        ...dimensionFields(),
        ...videoFields(),
        ...frameFields(),
        ...numericFields(),
        ...categoricalFields()
    ]);

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
            dimensions.updateDimensionsValues(
                dimensionUpdates.reduce(withDimensionRange, dimensionValues)
            );
        }
        const videoCurrent = videoValues.current;
        if (ofSource('video').length > 0 && videoCurrent) {
            videoStores.updateVideoBoundsValues({ ...videoCurrent, ...merge('video') });
        }
        const frameCurrent = frameValues.current;
        if (ofSource('frame').length > 0 && frameCurrent) {
            frameStores.updateVideoFramesBoundsValues({ ...frameCurrent, ...merge('frame') });
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
        if (field && isFieldActive(field)) resetFields([field]);
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
