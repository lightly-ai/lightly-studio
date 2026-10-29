import {
    metadataTileField,
    sourceTileField,
    tagTileField,
    TILE_FIELD_CLASSES,
    TILE_FIELD_SOURCE,
    TILE_FIELD_TAGS
} from '$lib/hooks/useTileFields/useTileFields';

interface TileFieldOption {
    id: string;
    label: string;
}

interface TileFieldGroup {
    label: string;
    options: TileFieldOption[];
}

/**
 * The fields the "Show on tiles" menu offers for the images or the annotations grid, grouped
 * under a header each. Groups without options are left out.
 */
export const getTileFieldOptions = ({
    isAnnotations,
    metadataKeys,
    tags,
    sources
}: {
    isAnnotations: boolean;
    metadataKeys: string[];
    /** The tags of the grid's collection. */
    tags: { tag_id: string; name: string }[];
    /** The annotation sources to offer one by one. Only the images grid passes them. */
    sources: { id: string; name: string }[];
}): TileFieldGroup[] => {
    const groups: TileFieldGroup[] = [
        {
            label: 'Fields',
            options: isAnnotations
                ? [
                      { id: TILE_FIELD_CLASSES, label: 'Annotation class' },
                      { id: TILE_FIELD_TAGS, label: 'All tags' },
                      { id: TILE_FIELD_SOURCE, label: 'Annotation source' }
                  ]
                : [
                      { id: TILE_FIELD_CLASSES, label: 'Annotation classes' },
                      { id: TILE_FIELD_TAGS, label: 'All tags' }
                  ]
        },
        {
            label: 'Tags',
            options: tags.map((tag) => ({ id: tagTileField(tag.tag_id), label: tag.name }))
        },
        {
            label: 'Annotation sources',
            options: sources.map((source) => ({
                id: sourceTileField(source.id),
                label: source.name
            }))
        },
        {
            label: 'Metadata',
            options: metadataKeys.map((key) => ({ id: metadataTileField(key), label: key }))
        }
    ];
    return groups.filter((group) => group.options.length > 0);
};

/** Keeps the options whose name contains the query, ignoring case, and drops emptied groups. */
export const filterTileFieldGroups = (
    groups: TileFieldGroup[],
    query: string
): TileFieldGroup[] => {
    const needle = query.trim().toLowerCase();
    if (needle === '') return groups;
    return groups
        .map((group) => ({
            ...group,
            options: group.options.filter((option) => option.label.toLowerCase().includes(needle))
        }))
        .filter((group) => group.options.length > 0);
};
