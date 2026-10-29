import {
    metadataTileField,
    TILE_FIELD_CLASSES,
    TILE_FIELD_SOURCE,
    TILE_FIELD_TAGS
} from '$lib/hooks/useTileFields/useTileFields';

interface TileFieldOption {
    id: string;
    label: string;
}

/** The fields the "Show on tiles" menu offers for the images or the annotations grid. */
export const getTileFieldOptions = ({
    isAnnotations,
    metadataKeys
}: {
    isAnnotations: boolean;
    metadataKeys: string[];
}): { fields: TileFieldOption[]; metadata: TileFieldOption[] } => ({
    fields: isAnnotations
        ? [
              { id: TILE_FIELD_CLASSES, label: 'Annotation class' },
              { id: TILE_FIELD_TAGS, label: 'Tags' },
              { id: TILE_FIELD_SOURCE, label: 'Annotation source' }
          ]
        : [
              { id: TILE_FIELD_CLASSES, label: 'Annotation classes' },
              { id: TILE_FIELD_TAGS, label: 'Tags' }
          ],
    metadata: metadataKeys.map((key) => ({ id: metadataTileField(key), label: key }))
});
