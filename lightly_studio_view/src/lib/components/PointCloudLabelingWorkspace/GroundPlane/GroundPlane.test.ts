import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { flushSync, type ComponentProps } from 'svelte';
import GroundPlane from './GroundPlane.svelte';

const { camera, task } = vi.hoisted(() => ({
    camera: { current: { position: { x: 0, y: 0, z: 20 } } },
    task: { run: () => {} }
}));

vi.mock('@threlte/core', () => ({
    useThrelte: () => ({ camera }),
    useTask: (callback: () => void) => {
        task.run = callback;
    }
}));

vi.mock('@threlte/extras', async () => ({
    Grid: (await import('./GridStub.svelte')).default
}));

const defaultProps: ComponentProps<typeof GroundPlane> = {
    pointCloudBounds: { min: [-1, -1, 0], max: [1, 1, 1] }
};

describe('GroundPlane', () => {
    it('updates the grid when bounds change and hides it for an empty footprint', async () => {
        const { rerender } = render(GroundPlane, { props: defaultProps });
        const initialFade = screen.getByTestId('ground-grid').getAttribute('data-fade-distance');

        await rerender({ pointCloudBounds: { min: [100, 200, 10], max: [120, 240, 20] } });
        expect(screen.getByTestId('ground-grid')).toHaveAttribute('data-position', '110,220,9.96');
        expect(screen.getByTestId('ground-grid').getAttribute('data-fade-distance')).not.toBe(
            initialFade
        );

        await rerender({ pointCloudBounds: { min: [0, 0, 0], max: [0, 0, 0] } });
        expect(screen.queryByTestId('ground-grid')).not.toBeInTheDocument();
    });

    it('updates the cell size as the camera moves', () => {
        render(GroundPlane, { props: defaultProps });
        camera.current.position.z = 200;
        flushSync(() => task.run());
        expect(screen.getByTestId('ground-grid')).toHaveAttribute('data-cell-size', '10');

        camera.current.position.z = 2;
        flushSync(() => task.run());
        expect(screen.getByTestId('ground-grid')).toHaveAttribute('data-cell-size', '0.1');
    });
});
