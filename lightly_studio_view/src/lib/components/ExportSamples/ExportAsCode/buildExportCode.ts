import type { AnnotationsFilter, ImageFilter } from '$lib/api/lightly_studio_local';
import type { ExportType } from '../exportOptions';

interface BuildExportCodeParams {
    /** Name of the dataset, as passed to `ls.ImageDataset.load()`. */
    datasetName: string;
    /** The filter that the export dialog applies. Null when no filter is active. */
    imageFilter: ImageFilter | null;
    /** Tags of the collection, used to name the tag in the tag filter. */
    tags: { tag_id: string; name: string }[];
    /** The export format selected in the dialog. */
    exportType: ExportType;
    /** Whether the images are bundled with the COCO object detections. */
    includeImages: boolean;
    /** Annotation sources of the collection. */
    annotationSources: { id: string; name: string }[];
    /** The annotation source selected in the dialog. Undefined means the first source. */
    selectedAnnotationSourceId: string | undefined;
}

interface BuildExportCodeReturn {
    /** The Python script, or undefined when the scope does not map to simple code. */
    code: string | undefined;
    /** Why there is no code. Undefined when there is code. */
    reason: string | undefined;
}

interface ExportCall {
    /** The `DatasetExport` method, or undefined for the file name list. */
    method: string | undefined;
    path: string;
    usesAnnotationSource: boolean;
    printed: string;
}

export const SCOPE_NOT_SUPPORTED_REASON =
    'Code export covers the whole dataset or one tag. Clear the other filters to get code.';
export const FORMAT_NOT_SUPPORTED_REASON = 'Code export is not available for this format.';

const EXPORT_CALLS: Partial<Record<ExportType, ExportCall>> = {
    samples: {
        method: undefined,
        path: 'samples.txt',
        usesAnnotationSource: false,
        printed: 'samples.txt'
    },
    classifications: {
        method: 'to_csv_classifications',
        path: 'classifications.csv',
        usesAnnotationSource: true,
        printed: 'classifications.csv'
    },
    object_detections_coco: {
        method: 'to_coco_object_detections',
        path: 'coco_export/annotations.json',
        usesAnnotationSource: true,
        printed: 'coco_export/annotations.json'
    },
    object_detections_yolo: {
        method: 'to_yolo_object_detections',
        path: 'yolo_export',
        usesAnnotationSource: true,
        printed: 'yolo_export/data.yaml and yolo_export/labels/'
    },
    segmentation: {
        method: 'to_coco_segmentation_masks',
        path: 'segmentations.json',
        usesAnnotationSource: true,
        printed: 'segmentations.json'
    },
    semantic_segmentations: {
        method: 'to_pascalvoc_segmentation_mask',
        path: 'pascalvoc_export',
        usesAnnotationSource: true,
        printed: 'pascalvoc_export/'
    },
    captions: {
        method: 'to_coco_captions',
        path: 'captions.json',
        usesAnnotationSource: false,
        printed: 'captions.json'
    }
};

/**
 * Builds a short LightlyStudio SDK script that runs the same export as the dialog.
 *
 * Code is generated only when the scope is the whole dataset or one tag, so the script stays
 * a few readable lines. Any other filter returns a reason instead.
 */
export function buildExportCode(params: BuildExportCodeParams): BuildExportCodeReturn {
    const call = EXPORT_CALLS[params.exportType];
    if (!call) return { code: undefined, reason: FORMAT_NOT_SUPPORTED_REASON };

    const tagName = getSimpleTagScope(
        params.imageFilter,
        params.tags,
        params.annotationSources.map((source) => source.id)
    );
    if (tagName === null) return { code: undefined, reason: SCOPE_NOT_SUPPORTED_REASON };

    const source = call.usesAnnotationSource ? getExplicitSource(params) : undefined;
    const withImages = params.exportType === 'object_detections_coco' && params.includeImages;
    const lines = [
        ...importLines({ hasTag: tagName !== undefined, hasSource: source !== undefined }),
        '',
        '# Use the database file that the LightlyStudio GUI runs on.',
        '# For a hosted workspace, call ls.connect() instead.',
        'ls.db_manager.connect(db_file="lightly_studio.db")',
        `dataset = ls.ImageDataset.load(${py(params.datasetName)})`,
        queryLine(tagName),
        '',
        ...exportLines(call, source, withImages)
    ];
    return { code: `${lines.join('\n')}\n`, reason: undefined };
}

/**
 * Returns the tag name of a one-tag filter, undefined for no filter, and null for any other
 * filter, which does not map to simple code.
 */
function getSimpleTagScope(
    imageFilter: ImageFilter | null,
    tags: { tag_id: string; name: string }[],
    annotationSourceIds: string[]
): string | undefined | null {
    if (!imageFilter) return undefined;
    if (imageFilter.width || imageFilter.height) return null;
    const {
        tag_ids: tagIds,
        annotations_filter: annotationsFilter,
        ...otherSampleFilters
    } = imageFilter.sample_filter ?? {};
    if (
        annotationsFilter &&
        !selectsEveryAnnotationSource(annotationsFilter, annotationSourceIds)
    ) {
        return null;
    }
    const hasOtherFilters = Object.values(otherSampleFilters).some((v) => v != null);
    if (hasOtherFilters || (tagIds?.length ?? 0) > 1) return null;
    if (!tagIds || tagIds.length === 0) return undefined;
    return tags.find((tag) => tag.tag_id === tagIds[0])?.name ?? null;
}

/**
 * Whether an annotation filter only carries the source list's default of every source ticked.
 * That filter restricts no image here, so it maps to no filter in code.
 */
function selectsEveryAnnotationSource(
    filter: AnnotationsFilter,
    annotationSourceIds: string[]
): boolean {
    const hasOtherCriteria = Object.entries(filter).some(
        ([key, value]) =>
            key !== 'filter_type' && key !== 'collection_ids' && value != null && value !== false
    );
    const selected = filter.collection_ids ?? [];
    return !hasOtherCriteria && annotationSourceIds.every((id) => selected.includes(id));
}

/** The dialog exports one source. With one source, the SDK default (all sources) matches it. */
function getExplicitSource({
    annotationSources,
    selectedAnnotationSourceId
}: BuildExportCodeParams): { id: string; name: string } | undefined {
    if (annotationSources.length < 2) return undefined;
    const id = selectedAnnotationSourceId ?? annotationSources[0].id;
    return annotationSources.find((source) => source.id === id);
}

function importLines({ hasTag, hasSource }: { hasTag: boolean; hasSource: boolean }): string[] {
    return [
        ...(hasSource ? ['from uuid import UUID', ''] : []),
        'import lightly_studio as ls',
        ...(hasTag ? ['from lightly_studio.core.dataset_query import ImageSampleField'] : [])
    ];
}

function queryLine(tagName: string | undefined): string {
    if (tagName === undefined) return 'query = dataset.query()';
    return `query = dataset.query().match(ImageSampleField.tags.contains(${py(tagName)}))`;
}

function exportLines(
    call: ExportCall,
    source: { id: string; name: string } | undefined,
    withImages: boolean
): string[] {
    if (!call.method) {
        return [
            `with open(${py(call.path)}, "w") as f:`,
            '    for sample in query:',
            '        f.write(f"{sample.file_path_abs}\\n")',
            `print("Wrote ${call.printed}")`
        ];
    }
    const args = [
        ...(source
            ? [
                  `annotation_collection_id=UUID(${py(source.id)}),  # annotation source ${py(source.name)}`
              ]
            : []),
        ...(withImages ? ['include_images=True,'] : [])
    ];
    const target = `dataset.export(query).${call.method}`;
    const callLines =
        args.length === 0
            ? [`${target}(${py(call.path)})`]
            : [`${target}(`, `    ${py(call.path)},`, ...args.map((arg) => `    ${arg}`), ')'];
    const printed = withImages ? `${call.printed} and coco_export/images/` : call.printed;
    return [...callLines, `print("Wrote ${printed}")`];
}

/** Formats a string as a Python string literal. JSON escapes are valid in Python. */
function py(value: string): string {
    return JSON.stringify(value);
}
