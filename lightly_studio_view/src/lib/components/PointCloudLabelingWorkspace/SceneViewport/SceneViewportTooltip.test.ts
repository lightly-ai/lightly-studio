import { render, screen } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import { createAnnotationFixture } from '../domain/fixtures';
import { createCuboidTransformState } from '../CuboidLayer/cuboidTransformState';
import SceneViewport from './SceneViewport.svelte';

vi.mock('./SceneViewportCanvas/SceneViewportCanvas.svelte', () => ({ default: () => {} }));
vi.mock('./RotationCursor/RotationCursor.svelte', () => ({ default: () => {} }));
vi.mock('./SceneNavigationControls.svelte', () => ({ default: () => {} }));

afterEach(() => vi.useRealTimers());

it.each(['perspective', 'top', 'side', 'front'] as const)(
    'hides an existing annotation tooltip in the %s view and restores it without changing hover',
    async (cameraMode) => {
        vi.useFakeTimers();
        const annotation = createAnnotationFixture();
        const { rerender } = render(SceneViewport, {
            props: {
                cameraMode,
                transforms: createCuboidTransformState({ onTransform: async () => true }),
                cuboids: [annotation],
                hoveredAnnotationId: annotation.id
            }
        });
        await vi.advanceTimersByTimeAsync(100);
        expect(screen.getByTestId('cuboid-tooltip')).toBeVisible();

        await rerender({ showAnnotationTooltips: false });
        expect(screen.queryByTestId('cuboid-tooltip')).not.toBeInTheDocument();
        await rerender({ showAnnotationTooltips: true });
        await vi.advanceTimersByTimeAsync(100);
        expect(screen.getByTestId('cuboid-tooltip')).toBeVisible();
    }
);
