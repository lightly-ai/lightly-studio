/** Schema describing the LightlyQuery language surface area.
 *
 * The Langium grammar in `lightly-query.langium` accepts unqualified field
 * names. Their meaning depends on the surrounding scope:
 *  - top-level: image fields, or video fields when the query starts with `video:`
 *  - inside `object_detection(...)`: object detection fields
 *  - inside `classification(...)`: classification fields
 *
 * Mirroring the field tables here lets the Monaco hover and completion
 * providers attach human-friendly documentation without re-parsing the
 * grammar at runtime. Keep both in sync when the grammar changes. */

export type Scope = 'image' | 'video' | 'object_detection' | 'classification';

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

export const SCOPES: Record<Scope, ScopeDoc> = {
    image: {
        scope: 'image',
        title: 'Image',
        description: 'Top-level image scope. Unqualified field names refer to image fields.',
        fields: [
            { name: 'width', type: 'int', description: 'Image width in pixels.' },
            { name: 'height', type: 'int', description: 'Image height in pixels.' },
            { name: 'file_name', type: 'string', description: 'Image file name.' },
            {
                name: 'file_path_abs',
                type: 'string',
                description: 'Absolute path to the image on disk.'
            },
            {
                name: 'created_at',
                type: 'datetime',
                description: 'When the image was created (ISO-8601 string).'
            }
        ]
    },
    video: {
        scope: 'video',
        title: 'Video',
        description: 'Video scope. Reached by prefixing the query with `video:`.',
        fields: [
            { name: 'width', type: 'int', description: 'Video frame width in pixels.' },
            { name: 'height', type: 'int', description: 'Video frame height in pixels.' },
            {
                name: 'fps',
                type: 'float',
                description: 'Frames per second. Equality only (`==`, `!=`).'
            },
            { name: 'duration_s', type: 'float', description: 'Duration in seconds.' },
            { name: 'file_name', type: 'string', description: 'Video file name.' },
            {
                name: 'file_path_abs',
                type: 'string',
                description: 'Absolute path to the video on disk.'
            }
        ]
    },
    object_detection: {
        scope: 'object_detection',
        title: 'ObjectDetection',
        description: 'Detected object inside an image. Used inside `object_detection(...)`.',
        fields: [
            { name: 'label', type: 'string', description: 'Class label of the detection.' },
            { name: 'x', type: 'int', description: 'Top-left X coordinate of the bounding box.' },
            { name: 'y', type: 'int', description: 'Top-left Y coordinate of the bounding box.' },
            { name: 'width', type: 'int', description: 'Bounding box width in pixels.' },
            { name: 'height', type: 'int', description: 'Bounding box height in pixels.' }
        ]
    },
    classification: {
        scope: 'classification',
        title: 'Classification',
        description: 'Classification annotation on an image. Used inside `classification(...)`.',
        fields: [
            { name: 'label', type: 'string', description: 'Class label of the classification.' }
        ]
    }
};

export interface KeywordDoc {
    name: string;
    description: string;
    insertText?: string;
}

export const TOP_LEVEL_KEYWORDS: KeywordDoc[] = [
    { name: 'AND', description: 'Boolean AND. Combines two conditions.' },
    { name: 'OR', description: 'Boolean OR.' },
    { name: 'NOT', description: 'Boolean NOT.' },
    { name: 'IN', description: 'Membership operator. Used as `"tag" IN tags`.' },
    {
        name: 'tags',
        description: 'The set of tags attached to the current sample. Use with `IN`.'
    },
    {
        name: 'video:',
        description:
            'Switch the top-level scope from image to video. Must appear at the start of the query.',
        insertText: 'video:'
    },
    {
        name: 'object_detection',
        description: 'Filter on detections inside an image.',
        insertText: 'object_detection(${1:condition})'
    },
    {
        name: 'classification',
        description: 'Filter on the image classification annotation.',
        insertText: 'classification(${1:label == "..."})'
    }
];

export function findFieldInScope(scope: Scope, name: string): FieldDoc | undefined {
    return SCOPES[scope].fields.find((f) => f.name === name);
}

export function findKeyword(name: string): KeywordDoc | undefined {
    return TOP_LEVEL_KEYWORDS.find((k) => k.name.toLowerCase() === name.toLowerCase());
}
export { detectScopeAt } from './detectScopeAt';
