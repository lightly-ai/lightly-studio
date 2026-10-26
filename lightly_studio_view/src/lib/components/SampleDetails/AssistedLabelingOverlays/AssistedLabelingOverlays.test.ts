import { render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { ComponentProps } from 'svelte';
import { writable } from 'svelte/store';
import AssistedLabelingOverlays from './AssistedLabelingOverlays.svelte';

type AssistedLabeling = ComponentProps<typeof AssistedLabelingOverlays>['assistedLabeling'];

vi.mock('$lib/hooks/useSettings', () => ({
    useSettings: () => ({ settingsStore: writable({ key_go_back: 'Escape' }) })
}));

const setup = (activeTool: string | null) =>
    render(AssistedLabelingOverlays, {
        props: {
            sample: { sampleId: 'sample-1', width: 100, height: 100 },
            visibleAnnotations: [],
            scale: 1,
            // Only the fields the overlays read.
            assistedLabeling: {
                activeTool,
                isPanning: false,
                state: { saveAs: 'box', isDrawingInstancesBox: true },
                instances: { predictions: [], boxes: [], isSaving: false },
                endInstancesBoxDrawing: vi.fn()
            } as unknown as AssistedLabeling
        }
    });

describe('AssistedLabelingOverlays', () => {
    it('renders the overlay of the active tool only', () => {
        expect(
            setup('find-instances').container.querySelector('rect[role="button"]')
        ).not.toBeNull();
        expect(setup(null).container.querySelector('rect[role="button"]')).toBeNull();
    });
});
