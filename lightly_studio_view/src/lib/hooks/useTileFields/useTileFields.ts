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
