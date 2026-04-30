/** Schema describing the LightlyQuery language surface area.
 *
 * The Langium grammar in `lightly-query.langium` enumerates the same field
 * names as keywords. Mirroring them here lets the Monaco completion and hover
 * providers attach human-friendly documentation without re-parsing the grammar
 * at runtime. Keep both in sync when the grammar changes. */

export interface FieldDoc {
    name: string;
    type: 'int' | 'float' | 'string' | 'datetime';
    description: string;
}

export interface ReceiverDoc {
    name: string;
    description: string;
    fields: FieldDoc[];
}

export const IMAGE_RECEIVER: ReceiverDoc = {
    name: 'Image',
    description: 'Image sample. Filter expressions on a single image.',
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
};

export const VIDEO_RECEIVER: ReceiverDoc = {
    name: 'Video',
    description: 'Video sample. Filter expressions on a single video.',
    fields: [
        { name: 'width', type: 'int', description: 'Video frame width in pixels.' },
        { name: 'height', type: 'int', description: 'Video frame height in pixels.' },
        { name: 'fps', type: 'float', description: 'Frames per second.' },
        { name: 'duration_s', type: 'float', description: 'Duration in seconds.' },
        { name: 'file_name', type: 'string', description: 'Video file name.' },
        {
            name: 'file_path_abs',
            type: 'string',
            description: 'Absolute path to the video on disk.'
        }
    ]
};

export const OBJECT_DETECTION_RECEIVER: ReceiverDoc = {
    name: 'ObjectDetection',
    description: 'Detected object inside an image. Used inside `object_detection(...)`.',
    fields: [
        { name: 'label', type: 'string', description: 'Class label of the detection.' },
        { name: 'x', type: 'int', description: 'Top-left X coordinate of the bounding box.' },
        { name: 'y', type: 'int', description: 'Top-left Y coordinate of the bounding box.' },
        { name: 'width', type: 'int', description: 'Bounding box width in pixels.' },
        { name: 'height', type: 'int', description: 'Bounding box height in pixels.' }
    ]
};

export const RECEIVERS: ReceiverDoc[] = [IMAGE_RECEIVER, VIDEO_RECEIVER, OBJECT_DETECTION_RECEIVER];

export interface KeywordDoc {
    name: string;
    description: string;
    insertText?: string;
}

export const TOP_LEVEL_KEYWORDS: KeywordDoc[] = [
    { name: 'and', description: 'Boolean AND. Combines two conditions.' },
    { name: 'or', description: 'Boolean OR.' },
    { name: 'not', description: 'Boolean NOT.' },
    {
        name: 'object_detection',
        description: 'Filter on detections inside an image.',
        insertText: 'object_detection(${1:condition})'
    },
    {
        name: 'tags.contains',
        description: 'Match samples whose tag set contains the given tag.',
        insertText: 'tags.contains("${1:tag}")'
    }
];
