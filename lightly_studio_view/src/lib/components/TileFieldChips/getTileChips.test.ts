import { describe, expect, it } from 'vitest';
import { formatClassCounts, getAnnotationTileChips, getImageTileChips } from './getTileChips';

type ImageSample = Parameters<typeof getImageTileChips>[0]['sample'];
type ImageAnnotation = ImageSample['annotations'][number];

const annotationOf = (name: string, sourceId = 'gt') =>
    ({
        annotation_collection_id: sourceId,
        annotation_label: { annotation_label_name: name }
    }) as unknown as ImageAnnotation;

const sample = {
    annotations: [annotationOf('deer'), annotationOf('cat'), annotationOf('deer')],
    tags: [{ name: 'train' }, { name: 'reviewed' }],
    metadata_dict: { data: { location: 'site 12', night: true } }
} as unknown as ImageSample;

const annotation = {
    annotation: {
        annotation_label: { annotation_label_name: 'deer' },
        tags: [{ name: 'hard' }]
    },
    metadata_dict: { data: { occluded: false } }
} as unknown as Parameters<typeof getAnnotationTileChips>[0]['annotation'];

describe('formatClassCounts', () => {
    it('counts distinct classes, most frequent first', () => {
        expect(formatClassCounts(['cat', 'deer', 'deer'])).toBe('2 deer, 1 cat');
        expect(formatClassCounts([])).toBe('');
    });
});

describe('getImageTileChips', () => {
    it('shows nothing when no field is ticked', () => {
        expect(getImageTileChips({ fields: [], sample, isSourceVisible: () => true })).toEqual([]);
    });

    it('builds one chip per ticked field in tick order', () => {
        const chips = getImageTileChips({
            fields: ['metadata:location', 'classes', 'tags'],
            sample,
            isSourceVisible: () => true
        });
        expect(chips).toEqual([
            { id: 'metadata:location', text: 'location: site 12', title: 'location: site 12' },
            { id: 'classes', text: '2 deer, 1 cat', title: 'Annotation classes: 2 deer, 1 cat' },
            { id: 'tags', text: 'train, reviewed', title: 'Tags: train, reviewed' }
        ]);
    });

    it('counts only annotations from visible sources', () => {
        const mixed = {
            ...sample,
            annotations: [annotationOf('deer', 'gt'), annotationOf('cat', 'pred')]
        };
        const chips = getImageTileChips({
            fields: ['classes'],
            sample: mixed,
            isSourceVisible: (id) => id === 'gt'
        });
        expect(chips[0].text).toBe('1 deer');
    });

    it('skips fields the image has no value for', () => {
        const bare = { annotations: [], tags: [], metadata_dict: null };
        const chips = getImageTileChips({
            fields: ['classes', 'tags', 'metadata:location'],
            sample: bare,
            isSourceVisible: () => true
        });
        expect(chips).toEqual([]);
    });
});

describe('getAnnotationTileChips', () => {
    it('shows the class, tags, source, and metadata of the annotation', () => {
        const chips = getAnnotationTileChips({
            fields: ['classes', 'tags', 'source', 'metadata:occluded'],
            annotation,
            sourceName: 'ground_truth'
        });
        expect(chips.map((chip) => chip.text)).toEqual([
            'deer',
            'hard',
            'ground_truth',
            'occluded: false'
        ]);
    });
});
