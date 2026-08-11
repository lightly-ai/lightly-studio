const DUPLICATE_OF_METADATA_KEY = 'duplicate_of';

type MetadataDict = {
    data?: Record<string, unknown>;
};

/**
 * Reads the `duplicate_of` metadata value from a sample metadata dict.
 * Returns the kept sample ID string when present and valid, otherwise null.
 */
export function getDuplicateOfSampleId(metadataDict: unknown): string | null {
    if (!metadataDict || typeof metadataDict !== 'object' || !('data' in metadataDict)) {
        return null;
    }

    const data = (metadataDict as MetadataDict).data;
    if (!data || typeof data !== 'object') {
        return null;
    }

    const value = data[DUPLICATE_OF_METADATA_KEY];
    if (typeof value !== 'string' || value.trim().length === 0) {
        return null;
    }

    return value;
}
