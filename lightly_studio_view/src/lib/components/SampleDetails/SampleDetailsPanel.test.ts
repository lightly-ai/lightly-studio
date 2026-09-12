import { fireEvent, render } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock factories are hoisted, so they read these only inside a function body.
const mockToolbarContext: {
    status: string | undefined;
    brush: { mode: string; size: number };
} = { status: 'cursor', brush: { mode: 'brush', size: 50 } };

const mockAnnotationLabelContext: Record<string, unknown> = {};

const isEditingMode = writable(false);
const toggleSampleSelection = vi.fn();
const toggleSampleAnnotationCropSelection = vi.fn();
const handleEscape = vi.fn();

// The panel creates both contexts, so mock the creators too.
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
        toggleSampleAnnotationCropSelection,
        isEditingMode,
        clearReversibleActions: vi.fn(),
        lastAnnotationBrushSize: writable({}),
        imageBrightness: writable(0),
        imageContrast: writable(0),
        lastAnnotationLabel: writable({}),
        lastAnnotationSource: writable({})
    })
}));

// initSettings() fetches on first use; only key_go_back matters here.
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

// Stub the children that need d3-zoom or a QueryClientProvider.
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
    // Neither snippet is under test.
    selectableBox: emptySnippet,
    sidePanelItem: emptySnippet
};

const appendInput = (insideDialog = false): HTMLElement => {
    const input = document.createElement('input');

    if (!insideDialog) {
        document.body.appendChild(input);
        return input;
    }

    const dialog = document.createElement('div');
    dialog.setAttribute('role', 'dialog');
    dialog.appendChild(input);
    document.body.appendChild(dialog);

    return input;
};

describe('SampleDetailsPanel keyboard shortcuts', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockToolbarContext.status = 'cursor';
        mockToolbarContext.brush = { mode: 'brush', size: 50 };
        mockAnnotationLabelContext.annotationType = null;
        isEditingMode.set(false);
    });

    it('toggles the sample selection on space', async () => {
        render(SampleDetailsPanel, { props: defaultProps });

        await fireEvent.keyDown(window, { key: ' ', code: 'Space' });

        expect(toggleSampleSelection).toHaveBeenCalledWith('sample-1', 'collection-1');
    });

    it.each([
        ['a text input', false],
        ['a dialog', true]
    ])('keeps the toolbar status when space is typed in %s', async (_name, insideDialog) => {
        render(SampleDetailsPanel, { props: defaultProps });
        const input = appendInput(insideDialog);

        await fireEvent.keyDown(input, { key: ' ', code: 'Space' });
        await fireEvent.keyUp(input, { key: ' ', code: 'Space' });

        expect(toggleSampleSelection).not.toHaveBeenCalled();
        expect(mockToolbarContext.status).toBe('cursor');
    });

    it('goes back on escape, but not from inside a dialog', async () => {
        render(SampleDetailsPanel, { props: defaultProps });
        const input = appendInput(true);

        await fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });
        expect(handleEscape).not.toHaveBeenCalled();

        await fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
        expect(handleEscape).toHaveBeenCalled();
    });

    it('enters pan mode while space is held in edit mode and restores the status', async () => {
        isEditingMode.set(true);
        render(SampleDetailsPanel, { props: defaultProps });
        mockToolbarContext.status = 'bounding-box';

        await fireEvent.keyDown(window, { key: ' ', code: 'Space' });
        expect(mockToolbarContext.status).toBe('drag');

        await fireEvent.keyUp(window, { key: ' ', code: 'Space' });
        expect(mockToolbarContext.status).toBe('bounding-box');
    });

    it.each([
        ['a text input', false],
        ['a dialog', true]
    ])(
        'keeps the active annotation tool when space is typed in %s during editing',
        async (_name, insideDialog) => {
            isEditingMode.set(true);
            render(SampleDetailsPanel, { props: defaultProps });
            const input = appendInput(insideDialog);
            mockToolbarContext.status = 'bounding-box';
            mockAnnotationLabelContext.annotationType = 'BOUNDING_BOX';

            await fireEvent.keyDown(input, { key: ' ', code: 'Space' });
            await fireEvent.keyUp(input, { key: ' ', code: 'Space' });

            // The keyup must not restore a status that no keydown ever saved.
            expect(mockToolbarContext.status).toBe('bounding-box');
            expect(mockAnnotationLabelContext.annotationType).toBe('BOUNDING_BOX');
        }
    );
});
