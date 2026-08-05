import type { Annotation } from './services/types';

export const GRID_PAGE_SIZE = 32;

export const ANNOTATION_TYPES: Record<Annotation['annotation_type'], string> = {
    object_detection: 'Object Detection',
    segmentation_mask: 'Segmentation Mask',
    classification: 'Classification'
} as const;

export const AUTHENTICATION_SESSION_STORAGE_KEY = 'lightlyEnterprise';

// Metadata key holding the similarity between a caption and its video segment.
export const CAPTION_SEGMENT_MATCH_SCORE_KEY = 'caption_segment_match_score';
// Video-level aggregates written when scoring caption segments.
export const MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY = 'min_caption_segment_match_score';
export const AVG_CAPTION_SEGMENT_MATCH_SCORE_KEY = 'avg_caption_segment_match_score';

// Video quality screening metadata keys (written by compute_quality_scores).
export const BLUR_SCORE_KEY = 'blur_score';
export const LIGHTING_SCORE_KEY = 'lighting_score';
export const MOTION_SCORE_KEY = 'motion_score';
