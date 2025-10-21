import type { Annotation } from './services/types';

export const ANNOTATION_TYPES: Record<Annotation['annotation_type'], string> = {
    object_detection: 'Object Detection',
    instance_segmentation: 'Instance Segmentation',
    semantic_segmentation: 'Semantic Segmentation',
    classification: 'Classification'
} as const;
