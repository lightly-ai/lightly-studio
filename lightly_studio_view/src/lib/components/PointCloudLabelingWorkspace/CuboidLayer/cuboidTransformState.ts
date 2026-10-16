import { readonly, writable } from 'svelte/store';
import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
import type { useUpdateCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidAnnotation';

type Transform = Parameters<
    ReturnType<typeof useUpdateCuboidAnnotation>['handleCuboidTransform']
>[0];

interface Params {
    onTransform: (transform: Transform) => Promise<boolean> | undefined;
}

interface WorkingTransform {
    annotation: Domain.CuboidAnnotation;
    active: boolean;
    status: 'unchanged' | 'saving' | 'saved' | 'failed';
}

interface CuboidTransformState {
    annotations: ReturnType<typeof readonly<readonly Domain.CuboidAnnotation[]>>;
    reconcile(annotations: readonly Domain.CuboidAnnotation[]): void;
    begin(annotation: Domain.CuboidAnnotation): void;
    cancel(annotationId: string): void;
    commit(transform: Transform): Promise<void>;
}

/** Keeps displayed transforms stable while edits and server refreshes overlap. */
export function createCuboidTransformState({ onTransform }: Params): CuboidTransformState {
    const displayed = writable<readonly Domain.CuboidAnnotation[]>([]);
    let source: readonly Domain.CuboidAnnotation[] = [];
    const working = new Map<string, WorkingTransform>();

    function prune(): void {
        for (const [id, entry] of working) {
            const sourceAnnotation = source.find((annotation) => annotation.id === id);
            const settled = !entry.active && entry.status !== 'saving';
            if (
                !sourceAnnotation ||
                (settled &&
                    (entry.status !== 'saved' || sameTransform(sourceAnnotation, entry.annotation)))
            ) {
                working.delete(id);
            }
        }
    }

    function publish(): void {
        prune();
        displayed.set(
            source.map((annotation) => {
                const current = working.get(annotation.id)?.annotation;
                return current
                    ? {
                          ...annotation,
                          center: current.center,
                          rotation: current.rotation,
                          size: current.size
                      }
                    : annotation;
            })
        );
    }

    return {
        annotations: readonly(displayed),

        reconcile(annotations) {
            source = annotations;
            publish();
        },

        begin(annotation) {
            const existing = working.get(annotation.id);
            if (existing) {
                existing.active = true;
                return;
            }
            working.set(annotation.id, {
                annotation,
                active: true,
                status: 'unchanged'
            });
        },

        cancel(annotationId) {
            const entry = working.get(annotationId);
            if (!entry) return;
            entry.active = false;
            publish();
        },

        async commit(transform) {
            const annotation = source.find(({ id }) => id === transform.annotationId);
            if (!annotation) return;
            const entry = createPendingTransform(annotation, transform);
            working.set(annotation.id, entry);
            publish();
            try {
                entry.status =
                    (await onTransform(transform)) === false ? 'failed' : 'saved';
            } catch {
                entry.status = 'failed';
            }
            if (working.get(annotation.id) === entry) publish();
        }
    };
}

function createPendingTransform(
    annotation: Domain.CuboidAnnotation,
    { center, rotation, size }: Transform
): WorkingTransform {
    return {
        annotation: { ...annotation, center, rotation, size },
        active: false,
        status: 'saving'
    };
}

function sameTransform(a: Domain.CuboidAnnotation, b: Domain.CuboidAnnotation): boolean {
    return (
        a.center.every((value, axis) => value === b.center[axis]) &&
        a.rotation.every((value, axis) => value === b.rotation[axis]) &&
        a.size.every((value, axis) => value === b.size[axis])
    );
}
