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
    // Accumulates uncommitted field edits so that a second commit does not
    // rebuild geometry from the stale prop while a previous save is in-flight.
    let pendingAnnotation: AnnotationInput | null = null;
    // Used to detect when the annotation prop itself has changed (i.e. a
    // refetch returned new data), at which point pendingAnnotation is cleared.
    let lastAnnotationRef: AnnotationInput | null = null;
    let valueOnFocus = '';

    $effect(() => {
        const annotation = getAnnotation();

        if (annotation !== lastAnnotationRef) {
            lastAnnotationRef = annotation;
            pendingAnnotation = null;
        }

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
        valueOnFocus = inputValues[field];
    }

    function handleCommit(field: FieldName): void {
        const raw = inputValues[field];
        const value = Number.parseFloat(raw);
        if (
            raw !== valueOnFocus &&
            raw !== '' &&
            Number.isFinite(value) &&
            isValidFieldValue(field, value)
        ) {
            const base = pendingAnnotation ?? getAnnotation();
            const updated = updateAnnotationGeometry(base, field, value, inputValues);
            if (field === 'rx' || field === 'ry' || field === 'rz') {
                lastEmittedRotation = updated.rotation;
            }
            pendingAnnotation = updated;
            onAnnotationChange(updated);
        }
        focusedField = null;
    }

    function handleKeyDown(event: KeyboardEvent): void {
        if (event.key === 'Enter') (event.currentTarget as HTMLInputElement).blur();
    }

    return { inputValues, handleInput, handleFocus, handleCommit, handleKeyDown };
}
