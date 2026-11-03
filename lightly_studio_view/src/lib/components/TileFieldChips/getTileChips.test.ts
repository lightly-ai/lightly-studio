import { describe, expect, it } from 'vitest';
import { getAnnotationTileChips, getImageTileChips } from './getTileChips';

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

const summarize = (chips: ReturnType<typeof getImageTileChips>) =>
    chips.map((chip) => [chip.kind, chip.title]);

describe('getImageTileChips', () => {
    it('shows nothing when no field is ticked', () => {
        expect(
            getImageTileChips({ fields: [], sample, isSourceVisible: () => true, sourceNames: {} })
        ).toEqual([]);
    });

    it('orders chips as classes, sources, tags, then metadata, whatever the tick order', () => {
        const chips = getImageTileChips({
            fields: ['metadata:location', 'tag:t-reviewed', 'source:gt', 'tags', 'classes'],
            sample,
            isSourceVisible: () => true,
            sourceNames: { gt: 'ground_truth' }
        });
        expect(summarize(chips)).toEqual([
            ['class', 'Classes: 2 deer, 1 cat'],
            ['source', 'Source ground_truth: 2 deer, 1 cat'],
            ['tag', 'Tag: reviewed'],
            ['tag', 'Tags: train, reviewed'],
            ['metadata', 'location: site 12']
        ]);
    });

    it('gives class chips one colored entry per class, most frequent first', () => {
        const [chip] = getImageTileChips({
            fields: ['classes'],
            sample,
            isSourceVisible: () => true,
            sourceNames: {}
        });
        expect(chip.classes).toEqual([
            { name: 'deer', text: '2 deer' },
            { name: 'cat', text: '1 cat' }
        ]);
    });

    it('splits a metadata chip into a muted key and its value', () => {
        const [chip] = getImageTileChips({
            fields: ['metadata:night'],
            sample,
            isSourceVisible: () => true,
            sourceNames: {}
        });
        expect(chip).toMatchObject({ kind: 'metadata', label: 'night', value: 'true' });
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
        expect(chips[0].title).toBe('Classes: 1 deer');
    });

    it('shows one tag by name only on images that carry it', () => {
        const params = { fields: ['tag:t-reviewed'], isSourceVisible: () => true, sourceNames: {} };
        expect(getImageTileChips({ ...params, sample })).toEqual([
            { id: 'tag:t-reviewed', kind: 'tag', value: 'reviewed', title: 'Tag: reviewed' }
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
        expect(summarize(chips)).toEqual([
            ['source', 'Source model_v1: 2 deer, 1 cat'],
            ['source', 'Source ground_truth: 1 deer']
        ]);
        expect(chips[0]).toMatchObject({ label: 'model_v1', sourceName: 'model_v1' });
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
    it('shows the class, source, tags, and metadata of the annotation in that order', () => {
        const chips = getAnnotationTileChips({
            fields: ['metadata:occluded', 'tag:t-hard', 'tags', 'source', 'classes', 'tag:t-x'],
            annotation,
            sourceName: 'ground_truth'
        });
        expect(summarize(chips)).toEqual([
            ['class', 'Class: deer'],
            ['source', 'Source: ground_truth'],
            ['tag', 'Tag: hard'],
            ['tag', 'Tags: hard'],
            ['metadata', 'occluded: false']
        ]);
        expect(chips[0].classes).toEqual([{ name: 'deer', text: 'deer' }]);
    });
});
