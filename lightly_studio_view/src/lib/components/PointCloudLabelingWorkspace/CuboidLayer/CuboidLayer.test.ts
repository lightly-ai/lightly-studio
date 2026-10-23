import { render } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import { createCuboidTransformState } from './cuboidTransformState';
import CuboidLayer from './CuboidLayer.svelte';

vi.mock('@threlte/core', () => ({
    T: { Group: () => {} },
    useThrelte: () => ({ renderer: { domElement: document.createElement('canvas') } })
}));
vi.mock('@threlte/extras', () => ({ interactivity: () => {} }));

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
