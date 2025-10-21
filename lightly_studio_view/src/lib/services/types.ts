import type {
    DatasetTable,
    ImageView,
    TagView as TagViewType,
    TagCreateBody,
    ExportFilter as ExportFilterType,
    SampleIdsBody as SampleIdsBodyType,
    AnnotationIdsBody as AnnotationIdsBodyType,
    AnnotationView,
    AnnotationWithImageView,
    ObjectDetectionAnnotationView as ObjectDetectionAnnotationViewType,
    InstanceSegmentationAnnotationView as InstanceSegmentationAnnotationViewType,
    SemanticSegmentationAnnotationView as SemanticSegmentationAnnotationViewType,
    AnnotationLabelTable,
    EmbeddingClassifier,
    UpdateAnnotationsRequest,
    SaveClassifierToFileData,
    MetadataInfoView
} from '$lib/api/lightly_studio_local/types.gen';
import type { Readable } from 'svelte/store';

export type Dataset = DatasetTable;
export type Sample = ImageView;
export type TagView = TagViewType;
export type TagInputBody = TagCreateBody;
export type ExportFilter = ExportFilterType;
export type TagKind = TagCreateBody['kind'];
export type SampleIdsBody = SampleIdsBodyType;
export type AnnotationIdsBody = AnnotationIdsBodyType;
export type Annotation = AnnotationView;
export type AnnotationWithSample = AnnotationWithImageView;

export type ObjectDetectionAnnotationView = ObjectDetectionAnnotationViewType;
export type InstanceSegmentationAnnotationView = InstanceSegmentationAnnotationViewType;
export type SemanticSegmentationAnnotationView = SemanticSegmentationAnnotationViewType;

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
    instance_segmentation_details: undefined;
    semantic_segmentation_details: undefined;
};

type AnnotationInstanceSegmentation = Annotation & {
    instance_segmentation_details: InstanceSegmentationAnnotationView;
    object_detection_details: undefined;
    semantic_segmentation_details: undefined;
};

type SemanticSegmentationAnnotation = Annotation & {
    semantic_segmentation_details: SemanticSegmentationAnnotationView;
    object_detection_details: undefined;
    instance_segmentation_details: undefined;
};

type ClassificationAnnotation = Annotation & {
    object_detection_details: undefined;
    instance_segmentation_details: undefined;
    semantic_segmentation_details: undefined;
};

// use type guards to narrow down the type of annotation
export function isObjectDetectionAnnotation(
    annotation: Annotation | AnnotationObjectDetection
): annotation is AnnotationObjectDetection {
    return annotation.annotation_type === 'object_detection';
}

export function isInstanceSegmentationAnnotation(
    annotation: Annotation | AnnotationInstanceSegmentation
): annotation is AnnotationInstanceSegmentation {
    return annotation.annotation_type === 'instance_segmentation';
}

export function isSemanticSegmentationAnnotation(
    annotation: Annotation | SemanticSegmentationAnnotation
): annotation is SemanticSegmentationAnnotation {
    return annotation.annotation_type === 'semantic_segmentation';
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
