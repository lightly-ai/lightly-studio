import type { Annotation } from './services/types';

export const GRID_PAGE_SIZE = 32;

export const ANNOTATION_TYPES: Record<Annotation['annotation_type'], string> = {
    object_detection: 'Object Detection',
    segmentation_mask: 'Segmentation Mask',
    classification: 'Classification'
} as const;

export const AUTHENTICATION_SESSION_STORAGE_KEY = 'lightlyEnterprise';
