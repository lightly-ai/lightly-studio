import { eulerDegreesToQuaternion, rotationToEulerDegrees } from './pointCloudAnnotationDetails';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

type AnnotationInput = Pick<CuboidAnnotation, 'center' | 'size' | 'rotation' | 'trackNumber'>;
type FieldName = 'x' | 'y' | 'z' | 'l' | 'w' | 'h' | 'rx' | 'ry' | 'rz';

function replaceAxis(
    values: readonly [number, number, number],
    index: number,
    value: number
): readonly [number, number, number] {
    const updated: [number, number, number] = [...values];
    updated[index] = value;
    return updated;
}

function updateRotation(
    annotation: AnnotationInput,
    field: FieldName,
    value: number,
    inputValues: Record<FieldName, string>
): AnnotationInput {
    const current = rotationToEulerDegrees(annotation.rotation);
    const fields = ['rx', 'ry', 'rz'] as const;
    const angles = fields.map((name, index) => {
        if (name === field) return value;
        const entered = Number.parseFloat(inputValues[name]);
        return Number.isNaN(entered) ? current[index] : entered;
    });
    return { ...annotation, rotation: eulerDegreesToQuaternion(angles[0], angles[1], angles[2]) };
}

/** Applies a committed geometry field to a cuboid annotation. */
export function updateAnnotationGeometry(
    annotation: AnnotationInput,
    field: FieldName,
    value: number,
    inputValues: Record<FieldName, string>
): AnnotationInput {
    const centerAxis = ['x', 'y', 'z'].findIndex((name) => name === field);
    if (centerAxis >= 0) {
        return { ...annotation, center: replaceAxis(annotation.center, centerAxis, value) };
    }

    const sizeAxis = ['l', 'w', 'h'].findIndex((name) => name === field);
    if (sizeAxis >= 0) {
        return { ...annotation, size: replaceAxis(annotation.size, sizeAxis, value) };
    }

    return updateRotation(annotation, field, value, inputValues);
}
