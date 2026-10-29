import type { AnnotationWithPayloadView, ImageView } from '$lib/api/lightly_studio_local';
import {
    getMetadataKey,
    TILE_FIELD_CLASSES,
    TILE_FIELD_SOURCE,
    TILE_FIELD_TAGS
} from '$lib/hooks/useTileFields/useTileFields';
import { formatMetadataValue } from '$lib/utils/formatter';

export interface TileChip {
    id: string;
    /** Short text shown on the tile; truncated to fit. */
    text: string;
    /** Full value for the tooltip. */
    title: string;
}

interface FieldValue {
    label: string;
    value: string;
    /** Metadata chips name their key on the tile; other fields show the bare value. */
    showLabel?: boolean;
}

type MetadataDict = ImageView['metadata_dict'];

/** Chips for an image tile, in the order the fields were ticked. */
export const getImageTileChips = ({
    fields,
    sample,
    isSourceVisible
}: {
    fields: string[];
    sample: Pick<ImageView, 'annotations' | 'tags' | 'metadata_dict'>;
    isSourceVisible: (sourceId: string) => boolean;
}): TileChip[] =>
    buildChips(fields, (fieldId) => {
        if (fieldId === TILE_FIELD_CLASSES) {
            const names = sample.annotations
                .filter((annotation) => isSourceVisible(annotation.annotation_collection_id))
                .map((annotation) => annotation.annotation_label.annotation_label_name);
            return { label: 'Annotation classes', value: formatClassCounts(names) };
        }
        if (fieldId === TILE_FIELD_TAGS) {
            return { label: 'Tags', value: sample.tags.map((tag) => tag.name).join(', ') };
        }
        return getMetadataValue(fieldId, sample.metadata_dict);
    });

/** Chips for an annotation tile, in the order the fields were ticked. */
export const getAnnotationTileChips = ({
    fields,
    annotation,
    sourceName
}: {
    fields: string[];
    annotation: Pick<AnnotationWithPayloadView, 'annotation' | 'metadata_dict'>;
    sourceName: string;
}): TileChip[] =>
    buildChips(fields, (fieldId) => {
        if (fieldId === TILE_FIELD_CLASSES) {
            return {
                label: 'Annotation class',
                value: annotation.annotation.annotation_label.annotation_label_name
            };
        }
        if (fieldId === TILE_FIELD_TAGS) {
            const tags = annotation.annotation.tags ?? [];
            return { label: 'Tags', value: tags.map((tag) => tag.name).join(', ') };
        }
        if (fieldId === TILE_FIELD_SOURCE) {
            return { label: 'Annotation source', value: sourceName };
        }
        return getMetadataValue(fieldId, annotation.metadata_dict);
    });

/** Formats class names as "2 deer, 1 cat", most frequent first. */
export const formatClassCounts = (names: string[]): string => {
    const counts = new Map<string, number>();
    for (const name of names) {
        counts.set(name, (counts.get(name) ?? 0) + 1);
    }
    return [...counts.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .map(([name, count]) => `${count} ${name}`)
        .join(', ');
};

const buildChips = (
    fields: string[],
    getValue: (fieldId: string) => FieldValue | undefined
): TileChip[] =>
    fields.flatMap((fieldId) => {
        const field = getValue(fieldId);
        // An empty value draws no chip, so tiles without the field stay clean.
        if (!field || field.value === '') return [];
        return [
            {
                id: fieldId,
                text: field.showLabel ? `${field.label}: ${field.value}` : field.value,
                title: `${field.label}: ${field.value}`
            }
        ];
    });

const getMetadataValue = (fieldId: string, metadata: MetadataDict): FieldValue | undefined => {
    const key = getMetadataKey(fieldId);
    if (key === undefined || metadata?.data[key] === undefined) return undefined;
    return { label: key, value: formatMetadataValue(metadata.data[key]), showLabel: true };
};
