import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';

/** Field ids that a grid tile can show. Metadata fields use `metadata:<key>`. */
export const TILE_FIELD_CLASSES = 'classes';
export const TILE_FIELD_TAGS = 'tags';
export const TILE_FIELD_SOURCE = 'source';
const METADATA_PREFIX = 'metadata:';

export const metadataTileField = (key: string): string => `${METADATA_PREFIX}${key}`;

/** Returns the metadata key of a field id, or undefined when the field is not metadata. */
export const getMetadataKey = (fieldId: string): string | undefined =>
    fieldId.startsWith(METADATA_PREFIX) ? fieldId.slice(METADATA_PREFIX.length) : undefined;

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
