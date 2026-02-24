import type {
    CollectionTable,
    ImageView,
    TagView as TagViewType,
    TagCreateBody,
    ExportFilter as ExportFilterType,
    SampleIdsBody as SampleIdsBodyType,
    AnnotationView,
    ObjectDetectionAnnotationView as ObjectDetectionAnnotationViewType,
    SegmentationAnnotationView as SegmentationAnnotationViewType,
    AnnotationLabelTable,
    EmbeddingClassifier,
    UpdateAnnotationsRequest,
    SaveClassifierToFileData,
    MetadataInfoView
} from '$lib/api/lightly_studio_local/types.gen';
import type { Readable } from 'svelte/store';

export type Collection = CollectionTable;
export type ImageSample = ImageView;
export type TagView = TagViewType;
export type TagInputBody = TagCreateBody;
export type ExportFilter = ExportFilterType;
export type TagKind = TagCreateBody['kind'];
export type SampleIdsBody = SampleIdsBodyType;
export type Annotation = AnnotationView;

export type ObjectDetectionAnnotationView = ObjectDetectionAnnotationViewType;
export type SegmentationAnnotationView = SegmentationAnnotationViewType;

export type AnnotationLabel = AnnotationLabelTable;

export type LoadResult<T> = {
    data: T;
    error: string | undefined;
};
export type ClassifierInfo = EmbeddingClassifier;
export type AnnotatedSamples = UpdateAnnotationsRequest;
export type RefineMode = 'temp' | 'existing';
export type ClassifierExportType = SaveClassifierToFileData['path']['export_type'];

type AnnotationObjectDetection = Annotation & {
    object_detection_details: ObjectDetectionAnnotationView;
    segmentation_details: undefined;
};

type AnnotationSegmentation = Annotation & {
    segmentation_details: SegmentationAnnotationView;
    object_detection_details: undefined;
};

type ClassificationAnnotation = Annotation & {
    object_detection_details: undefined;
    segmentation_details: undefined;
};

// use type guards to narrow down the type of annotation
export function isObjectDetectionAnnotation(
    annotation: Annotation | AnnotationObjectDetection
): annotation is AnnotationObjectDetection {
    return annotation.annotation_type === 'object_detection';
}

export function isInstanceSegmentationAnnotation(
    annotation: Annotation | AnnotationSegmentation
): annotation is AnnotationSegmentation {
    return annotation.annotation_type === 'instance_segmentation';
}

export function isSegmentationAnnotation(
    annotation: Annotation | AnnotationSegmentation
): annotation is AnnotationSegmentation {
    return (
        annotation.annotation_type === 'instance_segmentation' ||
        annotation.annotation_type === 'semantic_segmentation'
    );
}

export function isClassificationAnnotation(
    annotation: Annotation | ClassificationAnnotation
): annotation is ClassificationAnnotation {
    return annotation.annotation_type === 'classification';
}

// define generic result for the hook
export type SideEffectHookData<T> = {
    isLoading: boolean;
    error?: string;
    data?: T;
};
export type SideEffectHookResult<T> = Readable<SideEffectHookData<T>>;

// define generic interface for the hook
export type SideEffectHook<T, I = unknown> = (params: I) => SideEffectHookResult<T>;

export type MetadataInfo = MetadataInfoView;
export type MetadataBounds = Record<string, { min: number; max: number }>;
export type MetadataValues = Record<string, { min: number; max: number }>;
