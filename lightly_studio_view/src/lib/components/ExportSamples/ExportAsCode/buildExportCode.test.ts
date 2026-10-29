import { describe, expect, it } from 'vitest';
import type { ImageFilter } from '$lib/api/lightly_studio_local';
import {
    buildExportCode,
    FORMAT_NOT_SUPPORTED_REASON,
    SCOPE_NOT_SUPPORTED_REASON
} from './buildExportCode';

type Params = Parameters<typeof buildExportCode>[0];

const defaultParams: Params = {
    datasetName: 'caltech',
    imageFilter: null,
    tags: [
        { tag_id: 'tag-train', name: 'train' },
        { tag_id: 'tag-val', name: 'val' }
    ],
    exportType: 'object_detections_coco',
    includeImages: false,
    annotationSources: [{ id: 'source-gt', name: 'ground_truth' }],
    selectedAnnotationSourceId: undefined
};

const tagFilter = (tagIds: string[]): ImageFilter => ({
    filter_type: 'image',
    sample_filter: { tag_ids: tagIds }
});

describe('buildExportCode', () => {
    it('exports the whole dataset when no filter is active', () => {
        const { code, reason } = buildExportCode(defaultParams);

        expect(reason).toBeUndefined();
        expect(code).toBe(
            [
                'import lightly_studio as ls',
                '',
                '# Use the database file that the LightlyStudio GUI runs on.',
                '# For a hosted workspace, call ls.connect() instead.',
                'ls.db_manager.connect(db_file="lightly_studio.db")',
                'dataset = ls.ImageDataset.load("caltech")',
                'query = dataset.query()',
                '',
                'dataset.export(query).to_coco_object_detections("coco_export/annotations.json")',
                'print("Wrote coco_export/annotations.json")',
                ''
            ].join('\n')
        );
    });

    it('treats a filter with only the filter type as no filter', () => {
        const { code } = buildExportCode({
            ...defaultParams,
            imageFilter: { filter_type: 'image' }
        });

        expect(code).toContain('query = dataset.query()\n');
    });

    it('scopes the export to one tag', () => {
        const { code } = buildExportCode({ ...defaultParams, imageFilter: tagFilter(['tag-val']) });

        expect(code).toContain('from lightly_studio.core.dataset_query import ImageSampleField');
        expect(code).toContain(
            'query = dataset.query().match(ImageSampleField.tags.contains("val"))'
        );
    });

    it('treats the default selection of every annotation source as no filter', () => {
        // The source list ticks every source by default, and the image filter carries them.
        const { code, reason } = buildExportCode({
            ...defaultParams,
            annotationSources: [
                { id: 'source-gt', name: 'ground_truth' },
                { id: 'source-v1', name: 'model_v1' }
            ],
            imageFilter: {
                filter_type: 'image',
                sample_filter: {
                    tag_ids: ['tag-train'],
                    annotations_filter: {
                        filter_type: 'annotations',
                        collection_ids: ['source-gt', 'source-v1']
                    }
                }
            }
        });

        expect(reason).toBeUndefined();
        expect(code).toContain('ImageSampleField.tags.contains("train")');
    });

    it('gives no code when only some annotation sources are selected', () => {
        const { code } = buildExportCode({
            ...defaultParams,
            annotationSources: [
                { id: 'source-gt', name: 'ground_truth' },
                { id: 'source-v1', name: 'model_v1' }
            ],
            imageFilter: {
                filter_type: 'image',
                sample_filter: {
                    annotations_filter: {
                        filter_type: 'annotations',
                        collection_ids: ['source-v1']
                    }
                }
            }
        });

        expect(code).toBeUndefined();
    });

    it('gives no code for two tags', () => {
        const result = buildExportCode({
            ...defaultParams,
            imageFilter: tagFilter(['tag-train', 'tag-val'])
        });

        expect(result).toEqual({ code: undefined, reason: SCOPE_NOT_SUPPORTED_REASON });
    });

    it('gives no code for a metadata filter', () => {
        const result = buildExportCode({
            ...defaultParams,
            imageFilter: {
                filter_type: 'image',
                sample_filter: {
                    tag_ids: ['tag-train'],
                    metadata_filters: [{ key: 'location', op: '==', value: 'site_a' }]
                }
            }
        });

        expect(result).toEqual({ code: undefined, reason: SCOPE_NOT_SUPPORTED_REASON });
    });

    it('gives no code for a width or height filter', () => {
        const result = buildExportCode({
            ...defaultParams,
            imageFilter: { filter_type: 'image', width: { min: 100 } }
        });

        expect(result.reason).toBe(SCOPE_NOT_SUPPORTED_REASON);
    });

    it('gives no code when the tag is unknown', () => {
        const result = buildExportCode({
            ...defaultParams,
            imageFilter: tagFilter(['tag-missing'])
        });

        expect(result.reason).toBe(SCOPE_NOT_SUPPORTED_REASON);
    });

    it('downloads the images when include images is on', () => {
        const { code } = buildExportCode({ ...defaultParams, includeImages: true });

        expect(code).toContain(
            [
                'dataset.export(query).to_coco_object_detections(',
                '    "coco_export/annotations.json",',
                '    include_images=True,',
                ')',
                'print("Wrote coco_export/annotations.json and coco_export/images/")'
            ].join('\n')
        );
    });

    it('ignores include images for formats other than COCO object detections', () => {
        const { code } = buildExportCode({
            ...defaultParams,
            exportType: 'object_detections_yolo',
            includeImages: true
        });

        expect(code).not.toContain('include_images');
    });

    it('names the selected annotation source when there are several', () => {
        const { code } = buildExportCode({
            ...defaultParams,
            annotationSources: [
                { id: 'source-gt', name: 'ground_truth' },
                { id: 'source-model', name: 'model_v1' }
            ],
            selectedAnnotationSourceId: 'source-model'
        });

        expect(code).toMatch(/^from uuid import UUID\n\nimport lightly_studio as ls\n/);
        expect(code).toContain(
            '    annotation_collection_id=UUID("source-model"),  # annotation source "model_v1"'
        );
    });

    it('writes the file paths for the image filenames format', () => {
        const { code } = buildExportCode({ ...defaultParams, exportType: 'samples' });

        expect(code).toContain(
            [
                'with open("samples.txt", "w") as f:',
                '    for sample in query:',
                '        f.write(f"{sample.file_path_abs}\\n")',
                'print("Wrote samples.txt")'
            ].join('\n')
        );
    });

    it.each([
        ['classifications', 'dataset.export(query).to_csv_classifications("classifications.csv")'],
        [
            'object_detections_yolo',
            'dataset.export(query).to_yolo_object_detections("yolo_export")'
        ],
        ['segmentation', 'dataset.export(query).to_coco_segmentation_masks("segmentations.json")'],
        [
            'semantic_segmentations',
            'dataset.export(query).to_pascalvoc_segmentation_mask("pascalvoc_export")'
        ],
        ['captions', 'dataset.export(query).to_coco_captions("captions.json")']
    ] as const)('calls the SDK export for %s', (exportType, expectedCall) => {
        const { code } = buildExportCode({ ...defaultParams, exportType });

        expect(code).toContain(`${expectedCall}\n`);
    });

    it('gives no code for video formats', () => {
        const result = buildExportCode({
            ...defaultParams,
            exportType: 'youtube_vis_segmentation'
        });

        expect(result).toEqual({ code: undefined, reason: FORMAT_NOT_SUPPORTED_REASON });
    });
});
