import { render } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import { createCuboidTransformState } from './cuboidTransformState';
import CuboidLayer from './CuboidLayer.svelte';

vi.mock('@threlte/core', () => ({
    T: { Group: () => {} },
    useThrelte: () => ({ renderer: { domElement: document.createElement('canvas') } })
}));
vi.mock('@threlte/extras', () => ({ interactivity: () => {} }));
const draftTarget = vi.hoisted(() => ({ props: null as Record<string, unknown> | null }));
vi.mock('../CuboidDraft', () => ({
    CuboidDraftTarget: (_anchor: unknown, props: Record<string, unknown>) => {
        draftTarget.props = props;
    }
}));

const annotation = createAnnotationFixture();
const defaultProps = {
    annotationClasses: [],
    groundPlaneBounds: { min: [0, 0, 0], max: [1, 1, 1] } as const,
    hoveredAnnotationId: annotation.id
};

describe('CuboidLayer hover', () => {
    it('preserves hover through optimistic saves and clears it when annotations change', async () => {
        let finishSave = () => {};
        const transforms = createCuboidTransformState({
            onTransform: () => new Promise<boolean>((resolve) => (finishSave = () => resolve(true)))
        });
        transforms.reconcile([annotation]);
        const onhover = vi.fn();
        const { rerender } = render(CuboidLayer, {
            props: { ...defaultProps, transforms, cuboids: get(transforms.annotations), onhover }
        });
        onhover.mockClear();

        const saving = transforms.commit({
            annotationId: annotation.id,
            frameId: annotation.frameId,
            center: [20, 0, 0],
            size: annotation.size,
            rotation: annotation.rotation
        });
        await rerender({ cuboids: get(transforms.annotations) });
        expect(onhover).not.toHaveBeenCalled();

        finishSave();
        await saving;
        await rerender({ cuboids: get(transforms.annotations) });
        expect(onhover).not.toHaveBeenCalled();

        transforms.reconcile([]);
        await rerender({ cuboids: get(transforms.annotations) });
        expect(onhover).toHaveBeenCalledExactlyOnceWith(null, null);
    });
});

describe('CuboidLayer draft target', () => {
    const transforms = createCuboidTransformState({ onTransform: async () => true });
    const pointBatch = { positions: new Float32Array([0, 0, 0]) } as unknown as PointBatch;

    it('mounts the draft target only for the create-cuboid tool', async () => {
        draftTarget.props = null;
        const props = { ...defaultProps, transforms, cuboids: [], pointBatch };
        const { rerender } = render(CuboidLayer, { props: { ...props, activeTool: 'select' } });
        expect(draftTarget.props).toBeNull();

        await rerender({ activeTool: 'create-cuboid', cameraMode: 'top' });
        expect(draftTarget.props).toMatchObject({
            bounds: defaultProps.groundPlaneBounds,
            cameraMode: 'top',
            batch: pointBatch
        });
    });

    it('forwards created placements to onCreateCuboid', () => {
        draftTarget.props = null;
        const onCreateCuboid = vi.fn();
        render(CuboidLayer, {
            props: {
                ...defaultProps,
                transforms,
                cuboids: [],
                pointBatch,
                activeTool: 'create-cuboid',
                onCreateCuboid
            }
        });
        const placement = { kind: 'drop', position: [1, 2, 3] } as const;
        const { onCreateCuboid: forward } = draftTarget.props as unknown as {
            onCreateCuboid: (p: typeof placement) => void;
        };
        forward(placement);
        expect(onCreateCuboid).toHaveBeenCalledExactlyOnceWith(placement);
    });
});
