import { Color } from 'three';
import type { AnnotationClass } from '$lib/components/PointCloudLabelingWorkspace/domain';

const WHITE = new Color(0xffffff);

/**
 * Resolves the display color assigned to a cuboid's annotation class.
 *
 * @param annotationClasses - Classes available in the current workspace.
 * @param annotationClassId - Class assigned to the cuboid.
 * @returns The matching CSS color, or white when the class is unavailable.
 */
export function resolveCuboidColor(
    annotationClasses: readonly AnnotationClass[],
    annotationClassId: string
): string {
    return annotationClasses.find(({ id }) => id === annotationClassId)?.color ?? '#ffffff';
}

/**
 * Creates the display color for a cuboid edge, including its interaction state.
 *
 * @param base - The cuboid's unmodified annotation-class color.
 * @param isSelected - Whether the cuboid is selected.
 * @param isHovered - Whether the cuboid is hovered.
 * @returns A Three.js color with the applicable highlight applied.
 */
export function highlightCuboidColor(base: string, isSelected: boolean, isHovered: boolean): Color {
    const color = new Color(base);
    if (isSelected) return color.lerp(WHITE, 0.5);
    if (isHovered) return color.lerp(WHITE, 0.2);
    return color;
}
