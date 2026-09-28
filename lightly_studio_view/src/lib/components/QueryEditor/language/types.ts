/** Schema describing the LightlyQuery language surface area.
 *
 * The Langium grammar in `lightly-query.langium` accepts unqualified field
 * names. Their meaning depends on the surrounding scope:
 *  - top-level: image fields on the images grid, video fields on the videos grid
 *  - inside `object_detection(...)`: object detection fields
 *  - inside `classification(...)`: classification fields
 *  - inside `segmentation_mask(...)`: segmentation mask fields
 *
 * Mirroring the field tables here lets the Monaco hover and completion
 * providers attach human-friendly documentation without re-parsing the
 * grammar at runtime. Keep both in sync when the grammar changes. */

export type Scope = 'image' | 'video' | 'object_detection' | 'classification' | 'segmentation_mask';

/** Top-level scope of a query. It depends on the grid that the query filters. */
export type RootScope = Extract<Scope, 'image' | 'video'>;

export interface FieldDoc {
    name: string;
    type: 'int' | 'float' | 'string' | 'datetime';
    description: string;
}

export interface ScopeDoc {
    scope: Scope;
    title: string;
    description: string;
    fields: FieldDoc[];
}

export interface KeywordDoc {
    name: string;
    description: string;
    insertText?: string;
}
