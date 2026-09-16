import type { Component } from 'svelte';
import type { IconProps } from '@lucide/svelte';
import { Brush, ScanLine, SquareDashed } from '@lucide/svelte';
import { AnnotationType } from '$lib/api/lightly_studio_local/types.gen';

interface AnnotationTypeGlyph {
    icon: Component<IconProps>;
    /** Full type name, used as the tooltip and the sidebar filter row's label. */
    label: string;
}

/**
 * One glyph per annotation type, reusing the icon of the tool that creates it: the bounding-box
 * tool's dashed square, the mask brush, and frame brackets for a whole-image classification.
 */
const ANNOTATION_TYPE_GLYPHS: Record<AnnotationType, AnnotationTypeGlyph> = {
    [AnnotationType.OBJECT_DETECTION]: { icon: SquareDashed, label: 'Object detection' },
    [AnnotationType.SEGMENTATION_MASK]: { icon: Brush, label: 'Segmentation mask' },
    [AnnotationType.CLASSIFICATION]: { icon: ScanLine, label: 'Classification' }
};

export function getAnnotationTypeGlyph(type: AnnotationType): AnnotationTypeGlyph {
    return ANNOTATION_TYPE_GLYPHS[type];
}

/** Every annotation type, in the order the sidebar filter lists them. */
export const ANNOTATION_TYPES: AnnotationType[] = [
    AnnotationType.OBJECT_DETECTION,
    AnnotationType.SEGMENTATION_MASK,
    AnnotationType.CLASSIFICATION
];
