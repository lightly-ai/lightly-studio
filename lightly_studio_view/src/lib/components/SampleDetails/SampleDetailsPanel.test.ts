import { fireEvent, render } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockToolbarContext = { status: 'cursor', brush: { mode: 'brush', size: 50 } };

const mockAnnotationLabelContext: Record<string, unknown> = {};
const isEditingMode = writable(false);
const toggleSampleSelection = vi.fn();
const handleEscape = vi.fn();
vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', () => ({
    createSampleDetailsToolbarContext: () => mockToolbarContext,
    useSampleDetailsToolbarContext: () => ({
        context: mockToolbarContext,
        setStatus: (status: string) => {
            mockToolbarContext.status = status;
        }
    })
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    createAnnotationLabelContext: (initial: Record<string, unknown>) =>
        Object.assign(mockAnnotationLabelContext, initial),
    useAnnotationLabelContext: () => ({ context: mockAnnotationLabelContext })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        toggleSampleSelection,
        toggleSampleAnnotationCropSelection: vi.fn(),
        isEditingMode,
        clearReversibleActions: vi.fn(),
        lastAnnotationBrushSize: writable({}),
        imageBrightness: writable(0),
        imageContrast: writable(0),
        lastAnnotationLabel: writable({}),
        lastAnnotationSource: writable({})
    })
}));

vi.mock('$lib/hooks/useSettings', () => ({
    useSettings: () => ({ settingsStore: writable({ key_go_back: 'Escape' }) })
}));

vi.mock('$lib/hooks/useHideAnnotations', () => ({
    useHideAnnotations: () => ({ handleKeyEvent: vi.fn() })
}));

vi.mock('$lib/hooks/useAnnotationSelection/useAnnotationSelection', () => ({
    useAnnotationSelection: () => ({ selectAnnotation: vi.fn() })
}));

vi.mock('$app/navigation', () => ({ afterNavigate: vi.fn() }));
vi.mock('$app/state', () => ({ page: { data: {} } }));

vi.mock('$lib/components', async () => {
    const stub = (await import('./SampleDetailsPanel.stub.svelte')).default;
    return { Card: stub, CardContent: stub, SampleDetailsSidePanel: stub };
});
vi.mock('$lib/components/ImageAdjustments', async () => ({
    ImageAdjustments: (await import('./SampleDetailsPanel.stub.svelte')).default
}));
vi.mock('./SampleDetailsImageContainer/SampleDetailsImageContainer.svelte', async () => ({
    default: (await import('./SampleDetailsPanel.stub.svelte')).default
}));

import SampleDetailsPanel from './SampleDetailsPanel.svelte';

const emptySnippet = createRawSnippet(() => ({ render: () => '<div></div>' }));
const defaultProps = {
    sampleId: 'sample-1',
    collectionId: 'collection-1',
    sampleURL: 'http://example.com/image.jpg',
    sample: { width: 100, height: 100, sample_id: 'sample-1' },
    refetch: vi.fn(),
    handleEscape,
    breadcrumb: emptySnippet,
    selectableBox: emptySnippet,
    sidePanelItem: emptySnippet
};

describe('SampleDetailsPanel keyboard shortcuts', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockToolbarContext.status = 'cursor';
        mockAnnotationLabelContext.annotationType = null;
        isEditingMode.set(false);
    });

    it('selects on space and goes back on escape', async () => {
        render(SampleDetailsPanel, { props: defaultProps });
        await fireEvent.keyDown(window, { key: ' ' });
        expect(toggleSampleSelection).toHaveBeenCalledWith('sample-1', 'collection-1');
        await fireEvent.keyDown(window, { key: 'Escape' });
        expect(handleEscape).toHaveBeenCalledOnce();
    });

    it.each([false, true])('ignores fields and dialog buttons with editing=%s', async (editing) => {
        isEditingMode.set(editing);
        const { container } = render(SampleDetailsPanel, { props: defaultProps });
        const targets = document.createElement('div');
        targets.innerHTML = '<input /><div role="dialog"><button>Run</button></div>';
        container.appendChild(targets);
        mockToolbarContext.status = 'bounding-box';
        mockAnnotationLabelContext.annotationType = 'object_detection';
        for (const target of targets.querySelectorAll('input, button')) {
            expect(await fireEvent.keyDown(target, { key: ' ' })).toBe(true);
            await fireEvent.keyUp(target, { key: ' ' });
            await fireEvent.keyDown(target, { key: 'Escape' });
            expect(mockToolbarContext.status).toBe('bounding-box');
            expect(mockAnnotationLabelContext.annotationType).toBe('object_detection');
        }
        expect(toggleSampleSelection).not.toHaveBeenCalled();
        expect(handleEscape).not.toHaveBeenCalled();
    });

    it('restores the active tool when space is released after focus moves to a field', async () => {
        isEditingMode.set(true);
        const { container } = render(SampleDetailsPanel, { props: defaultProps });
        const input = container.appendChild(document.createElement('input'));
        mockToolbarContext.status = 'bounding-box';
        mockAnnotationLabelContext.annotationType = 'object_detection';
        await fireEvent.keyDown(window, { key: ' ' });
        expect(mockToolbarContext.status).toBe('drag');
        await fireEvent.keyUp(input, { key: ' ' });
        expect(mockToolbarContext.status).toBe('bounding-box');
        expect(mockAnnotationLabelContext.annotationType).toBe('object_detection');
    });
});
