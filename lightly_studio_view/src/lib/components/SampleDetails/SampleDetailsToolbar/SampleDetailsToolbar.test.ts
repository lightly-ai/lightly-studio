import { render, fireEvent, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import SampleDetailsToolbar from './SampleDetailsToolbar.svelte';
import { AnnotationType } from '$lib/api/lightly_studio_local';
import { BrushMode, ToolbarStatus } from '$lib/contexts/SampleDetailsToolbar.svelte';

const { initializeSlic } = vi.hoisted(() => ({ initializeSlic: vi.fn(async () => ({})) }));
vi.mock('@lightly-ai/slic', () => ({ getSlicEngine: initializeSlic }));

const mockSampleDetailsToolbarContext = {
    status: 'cursor' as ToolbarStatus,
    brush: {
        mode: 'brush' as 'brush' | 'eraser'
    },
    slic: {
        level: 'medium' as 'coarse' | 'medium' | 'fine',
        status: 'idle' as 'idle' | 'computing' | 'ready' | 'error'
    }
};

const mockAnnotationLabelContext = {
    annotationType: null as AnnotationType | null,
    annotationLabel: null as string | null,
    annotationId: null as string | null,
    lastCreatedAnnotationId: null as string | null,
    isDrawing: false,
    isErasing: false,
    isOnAnnotationDetailsView: false,
    annotationSourceBlockedReason: null as string | null
};

const settingsStore = writable({
    key_toolbar_selection: 's',
    key_toolbar_drag: 'd',
    key_toolbar_bounding_box: 'b',
    key_toolbar_segmentation_mask: 'm',
    key_toolbar_slic: 'a'
});

vi.mock('$lib/hooks/useSettings', () => ({
    useSettings: () => ({
        settingsStore
    })
}));

const assistedLabelingStatus = { disabledReason: null as string | null };

vi.mock('$lib/hooks/useAssistedLabelingStatus', () => ({
    useAssistedLabelingStatus: () => assistedLabelingStatus
}));

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/contexts/SampleDetailsToolbar.svelte')>()),
    useSampleDetailsToolbarContext: () => ({
        context: mockSampleDetailsToolbarContext,
        setBrushMode(mode: BrushMode) {
            mockSampleDetailsToolbarContext.brush.mode = mode;
        },
        setStatus(status: ToolbarStatus) {
            mockSampleDetailsToolbarContext.status = status;
        }
    })
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: mockAnnotationLabelContext,
        setAnnotationId(id: string | null) {
            mockAnnotationLabelContext.annotationId = id;
        },
        setAnnotationLabel(label: string | null) {
            mockAnnotationLabelContext.annotationLabel = label;
        },
        setLastCreatedAnnotationId(id: string | null) {
            mockAnnotationLabelContext.lastCreatedAnnotationId = id;
        },
        setIsDrawing(value: boolean) {
            mockAnnotationLabelContext.isDrawing = value;
        },
        setIsErasing(value: boolean) {
            mockAnnotationLabelContext.isErasing = value;
        },
        setAnnotationType(value: AnnotationType) {
            mockAnnotationLabelContext.annotationType = value;
        }
    })
}));

describe('SampleDetailsToolbar', () => {
    beforeEach(() => {
        mockSampleDetailsToolbarContext.status = 'cursor';
        mockSampleDetailsToolbarContext.brush.mode = 'brush';

        mockAnnotationLabelContext.annotationType = null;
        mockAnnotationLabelContext.annotationLabel = null;
        mockAnnotationLabelContext.annotationId = null;
        mockAnnotationLabelContext.lastCreatedAnnotationId = null;
        mockAnnotationLabelContext.isDrawing = false;
        mockAnnotationLabelContext.isErasing = false;
        mockAnnotationLabelContext.isOnAnnotationDetailsView = false;
        mockAnnotationLabelContext.annotationSourceBlockedReason = null;
        assistedLabelingStatus.disabledReason = null;
    });

    describe('while new annotations are blocked', () => {
        beforeEach(() => {
            mockAnnotationLabelContext.annotationSourceBlockedReason = 'Pick a source.';
        });

        it('disables the create tools and explains why', async () => {
            const { getByLabelText, getByRole } = render(SampleDetailsToolbar);

            for (const label of [
                'Bounding Box Tool',
                'Mask brush',
                'Smart select',
                'Find all instances'
            ]) {
                expect(getByLabelText(label)).toBeDisabled();
            }
            expect(getByLabelText('Selection')).toBeEnabled();
            expect(getByLabelText('Drag')).toBeEnabled();

            await fireEvent.keyDown(window, { key: 'b' });
            expect(mockSampleDetailsToolbarContext.status).toBe('cursor');

            await fireEvent.pointerEnter(getByLabelText('Bounding Box Tool').parentElement!);
            expect(getByRole('tooltip')).toHaveTextContent('Pick a source.');
        });

        it('switches an active create tool to the cursor', () => {
            mockSampleDetailsToolbarContext.status = 'bounding-box';

            render(SampleDetailsToolbar);

            expect(mockSampleDetailsToolbarContext.status).toBe('cursor');
        });

        it('keeps the brush in the annotation details view, which only edits', () => {
            mockAnnotationLabelContext.isOnAnnotationDetailsView = true;
            mockSampleDetailsToolbarContext.status = 'brush';

            const { getByLabelText } = render(SampleDetailsToolbar);

            expect(getByLabelText('Mask brush')).toBeEnabled();
            expect(mockSampleDetailsToolbarContext.status).toBe('brush');
        });
    });

    it('starts in cursor mode and resets annotation state on mount', () => {
        mockAnnotationLabelContext.annotationLabel = 'car';
        mockAnnotationLabelContext.annotationId = 'id-1';
        mockAnnotationLabelContext.lastCreatedAnnotationId = 'id-2';

        render(SampleDetailsToolbar);

        expect(mockSampleDetailsToolbarContext.status).toBe('cursor');
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
        expect(mockAnnotationLabelContext.annotationId).toBeNull();
        expect(mockAnnotationLabelContext.lastCreatedAnnotationId).toBeNull();
        expect(mockAnnotationLabelContext.annotationType).toBeNull();
    });

    it.each([
        ['bounding-box', AnnotationType.OBJECT_DETECTION],
        ['brush', AnnotationType.SEGMENTATION_MASK],
        ['slic', AnnotationType.SEGMENTATION_MASK]
    ] as const)('sets the annotation type of an active %s tool on mount', (status, type) => {
        mockSampleDetailsToolbarContext.status = status;
        mockAnnotationLabelContext.lastCreatedAnnotationId = 'id-2';

        render(SampleDetailsToolbar);

        expect(mockAnnotationLabelContext.annotationType).toBe(type);
        expect(mockAnnotationLabelContext.lastCreatedAnnotationId).toBeNull();
    });

    it('activates bounding box tool and sets annotation type', async () => {
        mockAnnotationLabelContext.annotationLabel = 'car';
        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Bounding Box Tool'));

        expect(mockSampleDetailsToolbarContext.status).toBe('bounding-box');
        expect(mockAnnotationLabelContext.annotationType).toBe(AnnotationType.OBJECT_DETECTION);
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
        expect(mockAnnotationLabelContext.annotationId).toBeNull();
    });

    it('activates brush tool and defaults to segmentation mask', async () => {
        mockAnnotationLabelContext.annotationLabel = 'car';
        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Mask brush'));

        expect(mockSampleDetailsToolbarContext.status).toBe('brush');
        expect(mockAnnotationLabelContext.annotationType).toBe(AnnotationType.SEGMENTATION_MASK);
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
        expect(mockAnnotationLabelContext.annotationId).toBeNull();
    });

    it('hides Superpixel brush until WASM initialization succeeds', async () => {
        let ready: (value: object) => void = () => {};
        initializeSlic.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    ready = resolve;
                })
        );
        const view = render(SampleDetailsToolbar);
        expect(view.queryByLabelText('Superpixel brush')).not.toBeInTheDocument();
        ready({});
        expect(await view.findByLabelText('Superpixel brush')).toBeInTheDocument();
    });

    it('keeps Superpixel brush hidden when WASM initialization fails', async () => {
        const error = new Error('WASM unavailable');
        const log = vi.spyOn(console, 'error').mockImplementation(() => {});
        initializeSlic.mockRejectedValueOnce(error);
        const view = render(SampleDetailsToolbar);
        await waitFor(() => expect(initializeSlic).toHaveBeenCalled());
        expect(view.queryByLabelText('Superpixel brush')).not.toBeInTheDocument();
        expect(log).toHaveBeenCalledWith('AI-assisted labeling initialization failed', error);
        log.mockRestore();
    });

    it('activates the SLIC tool and sets segmentation mask type', async () => {
        const { findByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(await findByLabelText('Superpixel brush'));

        expect(mockSampleDetailsToolbarContext.status).toBe('slic');
        expect(mockAnnotationLabelContext.annotationType).toBe(AnnotationType.SEGMENTATION_MASK);
    });

    it('keeps the selected segmentation annotation when activating the SLIC tool', async () => {
        mockSampleDetailsToolbarContext.status = 'brush';
        mockAnnotationLabelContext.annotationId = 'ann-1';
        mockAnnotationLabelContext.annotationType = AnnotationType.SEGMENTATION_MASK;

        const { findByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(await findByLabelText('Superpixel brush'));

        expect(mockSampleDetailsToolbarContext.status).toBe('slic');
        expect(mockAnnotationLabelContext.annotationId).toBe('ann-1');
        expect(mockAnnotationLabelContext.annotationType).toBe(AnnotationType.SEGMENTATION_MASK);
    });

    it('uses the configured AI-assisted shortcut and shows it in the tooltip', async () => {
        settingsStore.update((settings) => ({ ...settings, key_toolbar_slic: 'q' }));
        const view = render(SampleDetailsToolbar);
        const button = await view.findByLabelText('Superpixel brush');
        await fireEvent.pointerEnter(button.parentElement!);
        expect(view.getByRole('tooltip')).toHaveTextContent('Press Q to activate');
        expect(view.getByRole('tooltip')).not.toHaveTextContent('SLIC');
        await fireEvent.keyDown(window, { key: 'q' });
        expect(mockSampleDetailsToolbarContext.status).toBe('slic');
        mockAnnotationLabelContext.annotationId = 'ann-1';
        mockAnnotationLabelContext.isDrawing = true;
        await fireEvent.keyDown(window, { key: 'q' });
        expect(mockAnnotationLabelContext.annotationId).toBe('ann-1');
        mockAnnotationLabelContext.isDrawing = false;
        await fireEvent.keyDown(window, { key: 'q' });
        expect(mockAnnotationLabelContext.annotationId).toBeNull();
        expect(mockSampleDetailsToolbarContext.status).toBe('slic');
        settingsStore.update((settings) => ({ ...settings, key_toolbar_slic: 'a' }));
    });

    it('activates the smart select tool', async () => {
        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Smart select'));

        expect(mockSampleDetailsToolbarContext.status).toBe('smart-select');
    });

    it('explains how smart select works', async () => {
        const view = render(SampleDetailsToolbar);

        await fireEvent.pointerEnter(view.getByLabelText('Smart select').parentElement!);

        expect(view.getByRole('tooltip')).toHaveTextContent(
            'Segments the object that you click or box.'
        );
    });

    it('activates the find all instances tool', async () => {
        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Find all instances'));

        expect(mockSampleDetailsToolbarContext.status).toBe('find-instances');
    });

    it('explains how find all instances works', async () => {
        const view = render(SampleDetailsToolbar);

        await fireEvent.pointerEnter(view.getByLabelText('Find all instances').parentElement!);

        expect(view.getByRole('tooltip')).toHaveTextContent(
            'Finds all objects that match a text prompt.'
        );
    });

    it('resets the annotation type of the previous tool in smart select', () => {
        mockSampleDetailsToolbarContext.status = 'smart-select';
        mockAnnotationLabelContext.annotationType = AnnotationType.OBJECT_DETECTION;

        render(SampleDetailsToolbar);

        expect(mockAnnotationLabelContext.annotationType).toBeNull();
    });

    it('hides the assisted labeling tools while they are unavailable', () => {
        assistedLabelingStatus.disabledReason = 'Set the FAL_KEY environment variable.';
        const view = render(SampleDetailsToolbar);

        expect(view.queryByLabelText('Smart select')).not.toBeInTheDocument();
        expect(view.queryByLabelText('Find all instances')).not.toBeInTheDocument();
    });

    it('activates drag tool', async () => {
        mockAnnotationLabelContext.annotationLabel = 'car';
        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Drag'));

        expect(mockSampleDetailsToolbarContext.status).toBe('drag');
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
        expect(mockAnnotationLabelContext.annotationId).toBeNull();
    });

    it('switching to cursor resets drawing and erasing flags', async () => {
        mockSampleDetailsToolbarContext.status = 'brush';
        mockAnnotationLabelContext.isDrawing = true;
        mockAnnotationLabelContext.isErasing = true;
        mockAnnotationLabelContext.annotationLabel = 'car';

        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Selection'));

        // Force reload
        render(SampleDetailsToolbar);

        expect(mockSampleDetailsToolbarContext.status).toBe('cursor');
        expect(mockAnnotationLabelContext.isDrawing).toBe(false);
        expect(mockAnnotationLabelContext.isErasing).toBe(false);
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
    });

    it('activates selection tool and keep the annotation id when is annotation details', async () => {
        mockAnnotationLabelContext.annotationLabel = 'car';
        mockAnnotationLabelContext.annotationId = 'ann-1';
        mockAnnotationLabelContext.isOnAnnotationDetailsView = true;

        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Selection'));

        expect(mockSampleDetailsToolbarContext.status).toBe('cursor');
        expect(mockAnnotationLabelContext.annotationType).toBeNull();
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
        expect(mockAnnotationLabelContext.annotationId).toBe('ann-1');
    });

    it('activates drag tool and keep the annotation id when is annotation details', async () => {
        mockAnnotationLabelContext.annotationLabel = 'car';
        mockAnnotationLabelContext.annotationId = 'ann-1';
        mockAnnotationLabelContext.isOnAnnotationDetailsView = true;

        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Drag'));

        expect(mockSampleDetailsToolbarContext.status).toBe('drag');
        expect(mockAnnotationLabelContext.annotationType).toBeNull();
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
        expect(mockAnnotationLabelContext.annotationId).toBe('ann-1');
    });

    it('activates brush tool, sets segmentation mask and keep the annotation id when is annotation details', async () => {
        mockAnnotationLabelContext.annotationLabel = 'car';
        mockAnnotationLabelContext.annotationId = 'ann-1';
        mockAnnotationLabelContext.isOnAnnotationDetailsView = true;
        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Mask brush'));

        expect(mockSampleDetailsToolbarContext.status).toBe('brush');
        expect(mockAnnotationLabelContext.annotationType).toBe(AnnotationType.SEGMENTATION_MASK);
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
        expect(mockAnnotationLabelContext.annotationId).toBe('ann-1');
    });

    it('hides segmentation brush tool when disabled via props', () => {
        const { queryByLabelText } = render(SampleDetailsToolbar, {
            props: {
                showSegmentationTool: false
            }
        });

        expect(queryByLabelText('Mask brush')).not.toBeInTheDocument();
    });

    it('keeps eraser mode when switching from drag back to brush', async () => {
        const { getByLabelText } = render(SampleDetailsToolbar);
        mockSampleDetailsToolbarContext.status = 'brush';
        mockSampleDetailsToolbarContext.brush.mode = 'eraser';

        await fireEvent.click(getByLabelText('Drag'));
        await fireEvent.click(getByLabelText('Mask brush'));

        expect(mockSampleDetailsToolbarContext.status).toBe('brush');
        expect(mockSampleDetailsToolbarContext.brush.mode).toBe('eraser');
    });

    it('keeps brush tool active when toolbar remounts', () => {
        mockSampleDetailsToolbarContext.status = 'brush';
        mockAnnotationLabelContext.annotationType = AnnotationType.SEGMENTATION_MASK;

        render(SampleDetailsToolbar);

        expect(mockSampleDetailsToolbarContext.status).toBe('brush');
        expect(mockAnnotationLabelContext.annotationType).toBe(AnnotationType.SEGMENTATION_MASK);
    });

    it('normalizes non-instance annotation type to segmentation mask when remounting in brush mode', () => {
        mockSampleDetailsToolbarContext.status = 'brush';
        mockAnnotationLabelContext.annotationType = AnnotationType.OBJECT_DETECTION;

        render(SampleDetailsToolbar);

        expect(mockAnnotationLabelContext.annotationType).toBe(AnnotationType.SEGMENTATION_MASK);
    });

    it('syncs annotation type to segmentation mask when mounted in brush mode', () => {
        mockSampleDetailsToolbarContext.status = 'brush';
        mockAnnotationLabelContext.annotationType = null;

        render(SampleDetailsToolbar);

        expect(mockAnnotationLabelContext.annotationType).toBe(AnnotationType.SEGMENTATION_MASK);
    });

    it.each(['<input />', '<div role="dialog"><button>Run</button></div>'])(
        'ignores shortcuts and space tracking inside %s',
        async (html) => {
            const { container } = render(SampleDetailsToolbar);
            const wrapper = container.appendChild(document.createElement('div'));
            wrapper.innerHTML = html;
            const target = wrapper.querySelector('input, button')!;
            await fireEvent.keyDown(target, { key: 'd', code: 'KeyD' });
            expect(mockSampleDetailsToolbarContext.status).toBe('cursor');
            await fireEvent.keyDown(target, { key: ' ', code: 'Space' });
            await fireEvent.keyDown(window, { key: 'd', code: 'KeyD' });
            expect(mockSampleDetailsToolbarContext.status).toBe('drag');
        }
    );

    it('does not trigger toolbar shortcuts while space is held', async () => {
        render(SampleDetailsToolbar);

        await fireEvent.keyDown(window, { key: ' ', code: 'Space' });
        await fireEvent.keyDown(window, { key: 'd', code: 'KeyD' });
        expect(mockSampleDetailsToolbarContext.status).toBe('cursor');

        await fireEvent.keyUp(window, { key: ' ', code: 'Space' });
        await fireEvent.keyDown(window, { key: 'd', code: 'KeyD' });
        expect(mockSampleDetailsToolbarContext.status).toBe('drag');
    });
});
