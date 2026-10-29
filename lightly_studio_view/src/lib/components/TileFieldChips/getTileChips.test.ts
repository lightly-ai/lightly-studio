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
    tags: [
        { tag_id: 't-train', name: 'train' },
        { tag_id: 't-reviewed', name: 'reviewed' }
    ],
    metadata_dict: { data: { location: 'site 12', night: true } }
} as unknown as ImageSample;

const annotation = {
    annotation: {
        annotation_label: { annotation_label_name: 'deer' },
        tags: [{ tag_id: 't-hard', name: 'hard' }]
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
        expect(
            getImageTileChips({ fields: [], sample, isSourceVisible: () => true, sourceNames: {} })
        ).toEqual([]);
    });

    it('builds one chip per ticked field in tick order', () => {
        const chips = getImageTileChips({
            fields: ['metadata:location', 'classes', 'tags'],
            sample,
            isSourceVisible: () => true,
            sourceNames: {}
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
            isSourceVisible: (id) => id === 'gt',
            sourceNames: {}
        });
        expect(chips[0].text).toBe('1 deer');
    });

    it('shows one tag by name only on images that carry it', () => {
        const params = { fields: ['tag:t-reviewed'], isSourceVisible: () => true, sourceNames: {} };
        expect(getImageTileChips({ ...params, sample })).toEqual([
            { id: 'tag:t-reviewed', text: 'reviewed', title: 'Tag: reviewed' }
        ]);
        expect(getImageTileChips({ ...params, sample: { ...sample, tags: [] } })).toEqual([]);
    });

    it('shows the class counts of one source per ticked source, even when it is hidden', () => {
        const mixed = {
            ...sample,
            annotations: [
                annotationOf('deer', 'gt'),
                annotationOf('deer', 'model'),
                annotationOf('deer', 'model'),
                annotationOf('cat', 'model')
            ]
        };
        const chips = getImageTileChips({
            fields: ['source:model', 'source:gt', 'source:empty'],
            sample: mixed,
            isSourceVisible: (id) => id === 'gt',
            sourceNames: { gt: 'ground_truth', model: 'model_v1', empty: 'model_v2' }
        });
        expect(chips.map((chip) => chip.text)).toEqual([
            'model_v1: 2 deer, 1 cat',
            'ground_truth: 1 deer'
        ]);
    });

    it('skips fields the image has no value for', () => {
        const bare = { annotations: [], tags: [], metadata_dict: null };
        const chips = getImageTileChips({
            fields: ['classes', 'tags', 'tag:t-train', 'source:gt', 'metadata:location'],
            sample: bare,
            isSourceVisible: () => true,
            sourceNames: {}
        });
        expect(chips).toEqual([]);
    });
});

describe('getAnnotationTileChips', () => {
    it('shows the class, tags, source, and metadata of the annotation', () => {
        const chips = getAnnotationTileChips({
            fields: ['classes', 'tags', 'source', 'metadata:occluded', 'tag:t-hard', 'tag:t-x'],
            annotation,
            sourceName: 'ground_truth'
        });
        expect(chips.map((chip) => chip.text)).toEqual([
            'deer',
            'hard',
            'ground_truth',
            'occluded: false',
            'hard'
        ]);
    });
});
