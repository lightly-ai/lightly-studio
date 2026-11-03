import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

/**
 * Field ids that a grid tile can show. One tag uses `tag:<tag_id>`, one annotation source uses
 * `source:<collection_id>`, and a metadata field uses `metadata:<key>`.
 */
export const TILE_FIELD_CLASSES = 'classes';
export const TILE_FIELD_TAGS = 'tags';
export const TILE_FIELD_SOURCE = 'source';
const TAG_PREFIX = 'tag:';
const SOURCE_PREFIX = 'source:';
const METADATA_PREFIX = 'metadata:';

export const tagTileField = (tagId: string): string => `${TAG_PREFIX}${tagId}`;
export const sourceTileField = (sourceId: string): string => `${SOURCE_PREFIX}${sourceId}`;
export const metadataTileField = (key: string): string => `${METADATA_PREFIX}${key}`;

const stripPrefix = (fieldId: string, prefix: string): string | undefined =>
    fieldId.startsWith(prefix) ? fieldId.slice(prefix.length) : undefined;

/** Returns the tag id of a field id, or undefined when the field is not one tag. */
export const getTagId = (fieldId: string): string | undefined => stripPrefix(fieldId, TAG_PREFIX);

/** Returns the annotation source id of a field id, or undefined when the field is not one source. */
export const getSourceId = (fieldId: string): string | undefined =>
    stripPrefix(fieldId, SOURCE_PREFIX);

/** Returns the metadata key of a field id, or undefined when the field is not metadata. */
export const getMetadataKey = (fieldId: string): string | undefined =>
    stripPrefix(fieldId, METADATA_PREFIX);

/** What a field shows; each kind has its own marker on tiles and in the menu. */
type TileFieldKind = 'class' | 'source' | 'tag' | 'metadata';

/** Returns the kind of a field id. */
export const getTileFieldKind = (fieldId: string): TileFieldKind => {
    if (fieldId === TILE_FIELD_CLASSES) return 'class';
    if (fieldId === TILE_FIELD_SOURCE || getSourceId(fieldId) !== undefined) return 'source';
    if (fieldId === TILE_FIELD_TAGS || getTagId(fieldId) !== undefined) return 'tag';
    return 'metadata';
};

/**
 * The fields shown on a grid's tiles. Until the user picks fields, annotation tiles show their
 * class, since a box alone does not say what it is; image tiles show nothing extra.
 */
export const resolveTileFields = (stored: string[] | undefined, isAnnotations: boolean): string[] =>
    stored ?? (isAnnotations ? [TILE_FIELD_CLASSES] : []);

// Ticked fields per collection id. Kept for the browser session.
const tileFields = useSessionStorage<Record<string, string[]>>('tileFields', {});

/** The fields shown on grid tiles, chosen per collection in the grid header. */
export const useTileFields = () => {
    const toggleTileField = (
        collectionId: string,
        fieldId: string,
        isAnnotations = false
    ): void => {
        tileFields.update((all) => {
            const current = resolveTileFields(all[collectionId], isAnnotations);
            const next = current.includes(fieldId)
                ? current.filter((id) => id !== fieldId)
                : [...current, fieldId];
            return { ...all, [collectionId]: next };
        });
    };

    const clearTileFields = (collectionId: string): void => {
        tileFields.update((all) => ({ ...all, [collectionId]: [] }));
    };

    return { tileFields, toggleTileField, clearTileFields };
};
