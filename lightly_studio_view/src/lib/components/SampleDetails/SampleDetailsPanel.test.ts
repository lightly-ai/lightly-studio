import { fireEvent, render } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockToolbarContext = { status: 'cursor', brush: { mode: 'brush', size: 50 } };

const mockAnnotationLabelContext: Record<string, unknown> = {};
const isEditingMode = writable(false);
const toggleSampleSelection = vi.fn();
const handleEscape = vi.fn();
const deleteWithUndo = vi.fn().mockResolvedValue(true);

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/contexts/SampleDetailsToolbar.svelte')>()),
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

let userRole: string | undefined = 'labeler';

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        toggleSampleSelection,
        toggleSampleAnnotationCropSelection: vi.fn(),
        isEditingMode,
        clearReversibleActions: vi.fn(),
        lastAnnotationBrushSize: writable({}),
        imageBrightness: writable(0),
        imageContrast: writable(0),
        maskOpacity: writable(0),
        lastAnnotationLabel: writable({}),
        lastAnnotationSource: writable({})
    })
}));

vi.mock('$lib/hooks/useHideAnnotations', () => ({
    useHideAnnotations: () => ({ handleKeyEvent: vi.fn() })
}));

vi.mock('$lib/hooks/useAnnotationSelection/useAnnotationSelection', () => ({
    useAnnotationSelection: () => ({ selectAnnotation: vi.fn() })
}));

vi.mock('$lib/hooks', () => ({
    useDeleteAnnotationWithUndo: () => ({ deleteWithUndo })
}));

vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: userRole ? { role: userRole } : undefined })
}));

vi.mock('$lib/hooks/useAuth/hasMinimumRole', () => ({
    hasMinimumRole: (role: string | undefined, minimum: string) => {
        const order = ['viewer', 'labeler', 'admin'];
        return order.indexOf(role ?? '') >= order.indexOf(minimum);
    }
}));

vi.mock('svelte-sonner', () => ({
    toast: { success: vi.fn(), error: vi.fn() }
}));

vi.mock('$app/navigation', () => ({ afterNavigate: vi.fn() }));
vi.mock('$app/state', () => ({ page: { data: {} } }));

vi.mock('$lib/components', async () => {
    const stub = (await import('./SampleDetailsPanel.stub.svelte')).default;
    return {
        Card: stub,
        CardContent: stub,
        SampleDetailsSidePanel: stub,
        SidePanelToggleButton: stub
    };
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
        mockAnnotationLabelContext.annotationId = null;
        mockAnnotationLabelContext.isOnAnnotationDetailsView = false;
        isEditingMode.set(false);
        userRole = 'labeler';
    });

    it('selects on space and goes back on escape', async () => {
        render(SampleDetailsPanel, { props: defaultProps });
        await fireEvent.keyDown(window, { key: ' ' });
        expect(toggleSampleSelection).toHaveBeenCalledWith('sample-1', 'collection-1');
        await fireEvent.keyDown(window, { key: 'Escape' });
        expect(handleEscape).toHaveBeenCalledOnce();
    });

    it.each(['smart-select', 'find-instances'] as const)(
        'exits %s on escape in editing mode',
        async (status) => {
            isEditingMode.set(true);
            mockToolbarContext.status = status;
            render(SampleDetailsPanel, { props: defaultProps });
            await fireEvent.keyDown(window, { key: 'Escape' });
            expect(mockToolbarContext.status).toBe('cursor');
            expect(handleEscape).not.toHaveBeenCalled();
        }
    );

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

    describe('delete shortcut', () => {
        const annotationA1 = {
            sample_id: 'a1',
            parent_sample_id: 'sample-1',
            annotation_collection_id: 'col-1',
            created_at: new Date('2024-01-01T00:00:00Z'),
            annotation_type: 'object_detection' as const,
            annotation_label: { annotation_label_name: 'cat' }
        };

        const renderWithSelectedAnnotation = () => {
            isEditingMode.set(true);
            render(SampleDetailsPanel, {
                props: {
                    ...defaultProps,
                    sample: {
                        ...defaultProps.sample,
                        annotations: [annotationA1]
                    }
                }
            });
            mockAnnotationLabelContext.annotationId = 'a1';
        };

        it('deletes the selected annotation on Delete key', async () => {
            renderWithSelectedAnnotation();

            await fireEvent.keyDown(window, { key: 'Delete' });
            await vi.waitFor(() => {
                expect(mockAnnotationLabelContext.annotationId).toBeNull();
            });
        });

        it('deletes the selected annotation on Backspace key', async () => {
            renderWithSelectedAnnotation();

            await fireEvent.keyDown(window, { key: 'Backspace' });
            await vi.waitFor(() => {
                expect(mockAnnotationLabelContext.annotationId).toBeNull();
            });
        });

        it('does nothing in view mode', async () => {
            render(SampleDetailsPanel, {
                props: {
                    ...defaultProps,
                    sample: {
                        ...defaultProps.sample,
                        annotations: [annotationA1]
                    }
                }
            });
            mockAnnotationLabelContext.annotationId = 'a1';

            await fireEvent.keyDown(window, { key: 'Delete' });

            expect(mockAnnotationLabelContext.annotationId).toBe('a1');
        });

        it('does nothing without labeler role', async () => {
            userRole = 'viewer';
            renderWithSelectedAnnotation();

            await fireEvent.keyDown(window, { key: 'Delete' });

            expect(mockAnnotationLabelContext.annotationId).toBe('a1');
        });

        it('does nothing when no annotation is selected', async () => {
            isEditingMode.set(true);
            mockAnnotationLabelContext.annotationId = null;
            render(SampleDetailsPanel, {
                props: {
                    ...defaultProps,
                    sample: {
                        ...defaultProps.sample,
                        annotations: [annotationA1]
                    }
                }
            });

            await fireEvent.keyDown(window, { key: 'Delete' });

            expect(mockAnnotationLabelContext.annotationId).toBeNull();
        });

        it('does nothing when typing in a text input', async () => {
            renderWithSelectedAnnotation();
            const input = document.createElement('input');
            document.body.appendChild(input);

            await fireEvent.keyDown(input, { key: 'Delete' });

            expect(mockAnnotationLabelContext.annotationId).toBe('a1');
            input.remove();
        });

        it('does nothing when an overlay is open', async () => {
            renderWithSelectedAnnotation();
            const dialog = document.createElement('div');
            dialog.setAttribute('role', 'dialog');
            const button = document.createElement('button');
            dialog.appendChild(button);
            document.body.appendChild(dialog);

            await fireEvent.keyDown(button, { key: 'Delete' });

            expect(mockAnnotationLabelContext.annotationId).toBe('a1');
            dialog.remove();
        });

        it.each(['bounding-box', 'brush', 'eraser', 'slic', 'smart-select', 'find-instances'])(
            'does nothing when toolbar is in %s state',
            async (status) => {
                mockToolbarContext.status = status;
                renderWithSelectedAnnotation();

                await fireEvent.keyDown(window, { key: 'Delete' });

                expect(mockAnnotationLabelContext.annotationId).toBe('a1');
            }
        );

        it('does nothing on annotation details view', async () => {
            renderWithSelectedAnnotation();
            mockAnnotationLabelContext.isOnAnnotationDetailsView = true;

            await fireEvent.keyDown(window, { key: 'Delete' });

            expect(mockAnnotationLabelContext.annotationId).toBe('a1');
        });

        it('deletes in drag toolbar state', async () => {
            mockToolbarContext.status = 'drag';
            renderWithSelectedAnnotation();

            await fireEvent.keyDown(window, { key: 'Delete' });
            await vi.waitFor(() => {
                expect(mockAnnotationLabelContext.annotationId).toBeNull();
            });
        });
    });
});
