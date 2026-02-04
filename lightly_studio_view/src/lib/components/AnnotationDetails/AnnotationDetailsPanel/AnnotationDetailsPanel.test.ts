import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { QueryClient } from '@tanstack/svelte-query';
import TestAnnotationDetailsPanel from './AnnotationDetailsPanel.test.svelte';
import * as appState from '$app/state';
import { toast } from 'svelte-sonner';
import type { Page } from '@sveltejs/kit';
import type { AnnotationView } from '$lib/api/lightly_studio_local';

// Mock dependencies
vi.mock('svelte-sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn()
    }
}));

const mockRemoveTagFromSample = vi.fn();
vi.mock('$lib/hooks/useRemoveTagFromSample/useRemoveTagFromSample', () => ({
    useRemoveTagFromSample: () => ({
        removeTagFromSample: mockRemoveTagFromSample
    })
}));

vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: () => ({
        deleteAnnotation: vi.fn()
    })
}));

vi.mock('$lib/hooks/useAnnotationDeleteNavigation/useAnnotationDeleteNavigation', () => ({
    useAnnotationDeleteNavigation: () => ({
        gotoNextAnnotation: vi.fn()
    })
}));

describe('AnnotationDetailsPanel', () => {
    const mockAnnotation: AnnotationView = {
        sample_id: 'sample-123',
        parent_sample_id: 'parent-sample-123',
        annotation_type: 'object_detection',
        annotation_label: { annotation_label_name: 'Test Label' },
        created_at: new Date('2024-01-01'),
        tags: [{ tag_id: 'tag-1', name: 'Test Tag' }]
    };

    const setup = (props: { isEditingMode?: boolean } = {}) => {
        const onUpdateMock = vi.fn();
        const queryClient = new QueryClient({
            defaultOptions: {
                queries: {
                    retry: false
                }
            }
        });

        vi.spyOn(appState, 'page', 'get').mockReturnValue({
            params: { dataset_id: 'dataset-1', collection_type: 'annotations' },
            data: {
                globalStorage: { isEditingMode: writable(props.isEditingMode ?? false) },
                annotationIndex: 0,
                annotationAdjacents: { hasNext: false, hasPrevious: false }
            }
        } as unknown as Page);

        return { onUpdateMock, queryClient };
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('onRemoveTag', () => {
        it('calls removeTagFromSample, shows success toast, and calls onUpdate on success', async () => {
            mockRemoveTagFromSample.mockResolvedValue(undefined);
            const { onUpdateMock, queryClient } = setup();

            render(TestAnnotationDetailsPanel, {
                props: {
                    queryClient,
                    annotation: mockAnnotation,
                    onUpdate: onUpdateMock,
                    collectionId: 'collection-1'
                }
            });

            const removeButton = screen.getByRole('button', { name: /remove tag test tag/i });
            await fireEvent.click(removeButton);

            await waitFor(() => {
                expect(mockRemoveTagFromSample).toHaveBeenCalledWith('sample-123', 'tag-1');
                expect(toast.success).toHaveBeenCalledWith('Tag removed successfully');
                expect(onUpdateMock).toHaveBeenCalled();
            });
        });

        it('shows error toast and logs error when removeTagFromSample fails', async () => {
            const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
            const error = new Error('Network error');
            mockRemoveTagFromSample.mockRejectedValue(error);
            const { onUpdateMock, queryClient } = setup();

            render(TestAnnotationDetailsPanel, {
                props: {
                    queryClient,
                    annotation: mockAnnotation,
                    onUpdate: onUpdateMock,
                    collectionId: 'collection-1'
                }
            });

            const removeButton = screen.getByRole('button', { name: /remove tag test tag/i });
            await fireEvent.click(removeButton);

            await waitFor(() => {
                expect(toast.error).toHaveBeenCalledWith('Failed to remove tag. Please try again.');
                expect(consoleSpy).toHaveBeenCalledWith(
                    'Error removing tag from annotation:',
                    error
                );
                expect(onUpdateMock).not.toHaveBeenCalled();
            });

            consoleSpy.mockRestore();
        });
    });
});
