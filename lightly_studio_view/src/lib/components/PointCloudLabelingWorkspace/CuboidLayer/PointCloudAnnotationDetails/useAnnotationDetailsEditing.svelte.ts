import { rotationToEulerDegrees } from './pointCloudAnnotationDetails';
import { updateAnnotationGeometry } from './updateAnnotationGeometry';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

type AnnotationInput = Pick<CuboidAnnotation, 'center' | 'size' | 'rotation' | 'trackNumber'>;
type FieldName = Parameters<typeof updateAnnotationGeometry>[1];

function isValidFieldValue(field: FieldName, value: number): boolean {
    if (field === 'l' || field === 'w' || field === 'h') return value >= 0.01;
    return true;
}

/** Keeps editable geometry inputs in sync with the selected annotation. */
export function useAnnotationDetailsEditing(
    getAnnotation: () => AnnotationInput,
    onAnnotationChange: (annotation: AnnotationInput) => void
) {
    let focusedField = $state<FieldName | null>(null);
    const inputValues = $state<Record<FieldName, string>>({
        x: '',
        y: '',
        z: '',
        l: '',
        w: '',
        h: '',
        rx: '',
        ry: '',
        rz: ''
    });
    let lastEmittedRotation: AnnotationInput['rotation'] | null = null;

    $effect(() => {
        const annotation = getAnnotation();
        for (const [index, field] of ['x', 'y', 'z'].entries()) {
            const name = field as FieldName;
            if (focusedField !== name) inputValues[name] = String(annotation.center[index]);
        }
        for (const [index, field] of ['l', 'w', 'h'].entries()) {
            const name = field as FieldName;
            if (focusedField !== name) inputValues[name] = String(annotation.size[index]);
        }

        const rotation = annotation.rotation;
        const isLocalChange =
            lastEmittedRotation !== null &&
            rotation.every((component, index) => component === lastEmittedRotation?.[index]);
        lastEmittedRotation = null;
        if (isLocalChange) return;

        const angles = rotationToEulerDegrees(rotation);
        for (const [index, field] of ['rx', 'ry', 'rz'].entries()) {
            const name = field as FieldName;
            if (focusedField !== name) inputValues[name] = String(Number(angles[index].toFixed(6)));
        }
    });

    function handleInput(field: FieldName, value: string): void {
        inputValues[field] = value;
    }

    function handleFocus(field: FieldName): void {
        focusedField = field;
    }

    function handleCommit(field: FieldName): void {
        const raw = inputValues[field];
        const value = Number.parseFloat(raw);
        if (raw !== '' && !Number.isNaN(value) && isValidFieldValue(field, value)) {
            const updated = updateAnnotationGeometry(getAnnotation(), field, value, inputValues);
            if (field === 'rx' || field === 'ry' || field === 'rz') {
                lastEmittedRotation = updated.rotation;
            }
            onAnnotationChange(updated);
        }
        focusedField = null;
    }

    function handleKeyDown(event: KeyboardEvent): void {
        if (event.key === 'Enter') (event.currentTarget as HTMLInputElement).blur();
    }

    return { inputValues, handleInput, handleFocus, handleCommit, handleKeyDown };
}
