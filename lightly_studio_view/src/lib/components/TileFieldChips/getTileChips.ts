import type { AnnotationWithPayloadView, ImageView } from '$lib/api/lightly_studio_local';
import {
    getMetadataKey,
    getSourceId,
    getTagId,
    getTileFieldKind,
    TILE_FIELD_CLASSES,
    TILE_FIELD_SOURCE,
    TILE_FIELD_TAGS
} from '$lib/hooks/useTileFields/useTileFields';
import { formatMetadataValue } from '$lib/utils/formatter';

type TileFieldKind = ReturnType<typeof getTileFieldKind>;

interface ClassCount {
    /** The annotation class name, which picks the class color. */
    name: string;
    /** "2 deer" on image tiles, "deer" on annotation tiles. */
    text: string;
}

export interface TileChip {
    id: string;
    kind: TileFieldKind;
    /** Muted lead text: the metadata key or the annotation source name. */
    label?: string;
    /** Classes drawn with their class color. Class chips and image-tile source chips. */
    classes?: ClassCount[];
    /** Plain value text: tag names, a metadata value, or a source name. */
    value?: string;
    /** The annotation source name, which picks the source color. Source chips only. */
    sourceName?: string;
    /** Full text for the tooltip, naming the kind. */
    title: string;
}

type ChipContent = Omit<TileChip, 'id' | 'kind'>;

// Chips stack in this order whatever the order the fields were ticked in.
const KIND_ORDER: TileFieldKind[] = ['class', 'source', 'tag', 'metadata'];

/** Chips for an image tile: classes, sources, tags, then metadata. */
export const getImageTileChips = ({
    fields,
    sample,
    isSourceVisible,
    sourceNames
}: {
    fields: string[];
    sample: Pick<ImageView, 'annotations' | 'tags' | 'metadata_dict'>;
    isSourceVisible: (sourceId: string) => boolean;
    /** Annotation source names by id, for the chips of single sources. */
    sourceNames: Record<string, string>;
}): TileChip[] =>
    buildChips(fields, (fieldId) => {
        if (fieldId === TILE_FIELD_CLASSES) {
            const classes = countClasses(
                sample.annotations
                    .filter((annotation) => isSourceVisible(annotation.annotation_collection_id))
                    .map((annotation) => annotation.annotation_label.annotation_label_name)
            );
            return classes.length > 0 ? { classes, title: `Classes: ${joinTexts(classes)}` } : null;
        }
        if (fieldId === TILE_FIELD_TAGS) {
            return getAllTagsContent(sample.tags);
        }
        const sourceId = getSourceId(fieldId);
        if (sourceId !== undefined) {
            // A ticked source shows even while the source filter hides it: the user asked for it.
            const classes = countClasses(
                sample.annotations
                    .filter((annotation) => annotation.annotation_collection_id === sourceId)
                    .map((annotation) => annotation.annotation_label.annotation_label_name)
            );
            if (classes.length === 0) return null;
            const sourceName = sourceNames[sourceId];
            const label = sourceName ?? 'Annotation source';
            return { label, classes, sourceName, title: `Source ${label}: ${joinTexts(classes)}` };
        }
        return (
            getTagContent(fieldId, sample.tags) ?? getMetadataContent(fieldId, sample.metadata_dict)
        );
    });

/** Chips for an annotation tile: class, source, tags, then metadata. */
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
        const tags = annotation.annotation.tags ?? [];
        if (fieldId === TILE_FIELD_CLASSES) {
            const name = annotation.annotation.annotation_label.annotation_label_name;
            return { classes: [{ name, text: name }], title: `Class: ${name}` };
        }
        if (fieldId === TILE_FIELD_TAGS) {
            return getAllTagsContent(tags);
        }
        if (fieldId === TILE_FIELD_SOURCE) {
            if (sourceName === '') return null;
            return { value: sourceName, sourceName, title: `Source: ${sourceName}` };
        }
        return (
            getTagContent(fieldId, tags) ?? getMetadataContent(fieldId, annotation.metadata_dict)
        );
    });

/** Counts class names as "2 deer", "1 cat", most frequent first. */
const countClasses = (names: string[]): ClassCount[] => {
    const counts = new Map<string, number>();
    for (const name of names) {
        counts.set(name, (counts.get(name) ?? 0) + 1);
    }
    return [...counts.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .map(([name, count]) => ({ name, text: `${count} ${name}` }));
};

const joinTexts = (classes: ClassCount[]): string =>
    classes.map((classCount) => classCount.text).join(', ');

const buildChips = (
    fields: string[],
    getContent: (fieldId: string) => ChipContent | null
): TileChip[] => {
    const chips = fields.flatMap((fieldId) => {
        const content = getContent(fieldId);
        // A field without a value draws no chip, so tiles without the field stay clean.
        return content ? [{ id: fieldId, kind: getTileFieldKind(fieldId), ...content }] : [];
    });
    // Array.sort is stable, so fields of one kind keep the order they were ticked in.
    return chips.sort((a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind));
};

type Tag = { tag_id: string; name: string };

const getAllTagsContent = (tags: Tag[]): ChipContent | null => {
    if (tags.length === 0) return null;
    const value = tags.map((tag) => tag.name).join(', ');
    return { value, title: `Tags: ${value}` };
};

/** A single-tag field shows the tag name, only on tiles that carry the tag. */
const getTagContent = (fieldId: string, tags: Tag[]): ChipContent | null => {
    const tagId = getTagId(fieldId);
    const tag = tagId === undefined ? undefined : tags.find((t) => t.tag_id === tagId);
    return tag ? { value: tag.name, title: `Tag: ${tag.name}` } : null;
};

const getMetadataContent = (
    fieldId: string,
    metadata: ImageView['metadata_dict']
): ChipContent | null => {
    const key = getMetadataKey(fieldId);
    if (key === undefined || metadata?.data[key] === undefined) return null;
    const value = formatMetadataValue(metadata.data[key]);
    return value === '' ? null : { label: key, value, title: `${key}: ${value}` };
};
