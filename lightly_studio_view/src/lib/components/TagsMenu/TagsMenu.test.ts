import {
    addSampleIdsToTagId,
    createTag,
    deleteTag,
    renameTag
} from '$lib/api/lightly_studio_local';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TagsMenu from './TagsMenu.svelte';
import type { TagView } from '$lib/services/types';
import { toast } from 'svelte-sonner';

const mocks = vi.hoisted(() => ({
    tags: [] as TagView[],
    tagsSelected: new Set<string>(),
    selectedSampleIdsByCollection: {} as Record<string, Set<string>>,
    selectedSampleAnnotationCropIds: {} as Record<string, Set<string>>,
    loadTags: vi.fn(),
    tagSelectionToggle: vi.fn(),
    clearTagSelected: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', async () => {
    const actual = await vi.importActual('$lib/api/lightly_studio_local');
    return {
        ...actual,
        createTag: vi.fn(),
        addSampleIdsToTagId: vi.fn(),
        deleteTag: vi.fn(),
        renameTag: vi.fn()
    };
});

vi.mock('$lib/hooks/useTags/useTags.js', () => ({
    useTags: vi.fn(() => ({
        tags: readable(mocks.tags),
        tagsSelected: readable(mocks.tagsSelected),
        tagSelectionToggle: mocks.tagSelectionToggle,
        loadTags: mocks.loadTags,
        clearTagSelected: mocks.clearTagSelected
    }))
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        getSelectedSampleIds: (collectionId: string) =>
            readable(mocks.selectedSampleIdsByCollection[collectionId] ?? new Set<string>()),
        selectedSampleAnnotationCropIds: readable(mocks.selectedSampleAnnotationCropIds)
    })
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        error: vi.fn(),
        success: vi.fn()
    }
}));

const sampleTag: TagView = {
    tag_id: 'tag-1',
    name: 'Vehicle',
    kind: 'sample',
    created_at: new Date('2024-01-01T00:00:00.000Z'),
    updated_at: new Date('2024-01-01T00:00:00.000Z')
};

const mockRequest = new Request('http://localhost/api/test');
const mockResponse = new Response(null, { status: 200 });

describe('TagsMenu', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.tags = [sampleTag];
        mocks.tagsSelected = new Set<string>();
        mocks.selectedSampleIdsByCollection = {};
        mocks.selectedSampleAnnotationCropIds = {};
        vi.mocked(addSampleIdsToTagId).mockResolvedValue({
            data: true,
            error: undefined,
            request: mockRequest,
            response: mockResponse
        });
        vi.mocked(createTag).mockResolvedValue({
            data: {
                tag_id: 'created-tag-id',
                name: 'Created Tag',
                kind: 'sample',
                created_at: new Date('2024-01-03T00:00:00.000Z'),
                updated_at: new Date('2024-01-03T00:00:00.000Z')
            },
            error: undefined,
            request: mockRequest,
            response: mockResponse
        });
        vi.mocked(deleteTag).mockResolvedValue({
            data: {
                status: 'deleted'
            },
            error: undefined,
            request: mockRequest,
            response: mockResponse
        });
        vi.mocked(renameTag).mockResolvedValue({
            data: {
                ...sampleTag,
                name: 'Renamed Vehicle'
            },
            error: undefined,
            request: mockRequest,
            response: mockResponse
        });
    });

    it('assigns an existing tag to the selected samples', async () => {
        mocks.selectedSampleIdsByCollection = {
            'collection-1': new Set(['sample-1', 'sample-2'])
        };

        render(TagsMenu, {
            props: {
                collection_id: 'collection-1',
                gridType: 'samples'
            }
        });

        const input = screen.getByPlaceholderText('Assign tag to selection');
        await fireEvent.focus(input);
        await fireEvent.input(input, { target: { value: 'veh' } });
        await fireEvent.click(screen.getByRole('button', { name: 'Vehicle' }));

        await waitFor(() => {
            expect(addSampleIdsToTagId).toHaveBeenCalledWith({
                path: {
                    collection_id: 'collection-1',
                    tag_id: 'tag-1'
                },
                body: {
                    sample_ids: ['sample-1', 'sample-2']
                }
            });
        });

        expect(createTag).not.toHaveBeenCalled();
        expect(mocks.loadTags).toHaveBeenCalled();
    });

    it('creates an annotation tag and assigns it to the selected annotations', async () => {
        mocks.tags = [];
        mocks.selectedSampleAnnotationCropIds = {
            'collection-1': new Set(['annotation-1', 'annotation-2'])
        };

        render(TagsMenu, {
            props: {
                collection_id: 'collection-1',
                gridType: 'annotations'
            }
        });

        const input = screen.getByPlaceholderText('Assign tag to selection');
        await fireEvent.focus(input);
        await fireEvent.input(input, { target: { value: 'New Annotation Tag' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        await waitFor(() => {
            expect(createTag).toHaveBeenCalledWith({
                path: {
                    collection_id: 'collection-1'
                },
                body: {
                    name: 'New Annotation Tag',
                    kind: 'annotation'
                }
            });
        });

        expect(addSampleIdsToTagId).toHaveBeenCalledWith({
            path: {
                collection_id: 'collection-1',
                tag_id: 'created-tag-id'
            },
            body: {
                sample_ids: ['annotation-1', 'annotation-2']
            }
        });
        expect(mocks.loadTags).toHaveBeenCalled();
    });

    it('disables tag assignment when no samples are selected', () => {
        render(TagsMenu, {
            props: {
                collection_id: 'collection-1',
                gridType: 'samples'
            }
        });

        expect(screen.getByPlaceholderText('Assign tag to selection')).toBeDisabled();
    });

    it('shows a toast when tag assignment throws unexpectedly', async () => {
        mocks.selectedSampleIdsByCollection = {
            'collection-1': new Set(['sample-1'])
        };
        const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
        vi.mocked(addSampleIdsToTagId).mockRejectedValue(new Error('network error'));

        render(TagsMenu, {
            props: {
                collection_id: 'collection-1',
                gridType: 'samples'
            }
        });

        const input = screen.getByPlaceholderText('Assign tag to selection');
        await fireEvent.focus(input);
        await fireEvent.input(input, { target: { value: 'veh' } });
        await fireEvent.click(screen.getByRole('button', { name: 'Vehicle' }));

        await waitFor(() => {
            expect(toast.error).toHaveBeenCalledWith('Failed to assign tag. Please try again.');
        });

        expect(mocks.loadTags).not.toHaveBeenCalled();
        consoleErrorSpy.mockRestore();
    });

    it('deletes a tag from the sidebar actions menu', async () => {
        render(TagsMenu, {
            props: {
                collection_id: 'collection-1',
                gridType: 'samples'
            }
        });

        await fireEvent.click(screen.getByTestId('tag-actions-trigger-tag-1'));
        await fireEvent.click(await screen.findByTestId('delete-tag-tag-1'));

        await waitFor(() => {
            expect(deleteTag).toHaveBeenCalledWith({
                path: {
                    collection_id: 'collection-1',
                    tag_id: 'tag-1'
                }
            });
        });

        expect(mocks.clearTagSelected).toHaveBeenCalledWith('tag-1');
        expect(mocks.loadTags).toHaveBeenCalled();
        expect(toast.success).toHaveBeenCalledWith('Tag deleted successfully');
    });

    it('shows a toast when deleting a tag fails', async () => {
        vi.mocked(deleteTag).mockRejectedValue(new Error('network error'));

        render(TagsMenu, {
            props: {
                collection_id: 'collection-1',
                gridType: 'samples'
            }
        });

        await fireEvent.click(screen.getByTestId('tag-actions-trigger-tag-1'));
        await fireEvent.click(await screen.findByTestId('delete-tag-tag-1'));

        await waitFor(() => {
            expect(toast.error).toHaveBeenCalledWith('Failed to delete tag. Please try again.');
        });

        expect(mocks.clearTagSelected).not.toHaveBeenCalled();
        expect(mocks.loadTags).not.toHaveBeenCalled();
    });

    it('renames a tag from the inline row edit via tick button', async () => {
        render(TagsMenu, {
            props: {
                collection_id: 'collection-1',
                gridType: 'samples'
            }
        });

        await fireEvent.click(screen.getByTestId('tag-actions-trigger-tag-1'));
        await fireEvent.click(await screen.findByTestId('rename-tag-tag-1'));

        expect(await screen.findByTestId('rename-tag-form-tag-1')).toBeVisible();
        const input = screen.getByTestId('rename-tag-input-tag-1') as HTMLInputElement;
        expect(input).toHaveValue('Vehicle');
        await waitFor(() => {
            expect(document.activeElement).toBe(input);
            expect(input.selectionStart).toBe(0);
            expect(input.selectionEnd).toBe('Vehicle'.length);
        });
        expect(screen.queryByTestId('rename-tag-tag-1')).not.toBeInTheDocument();

        await fireEvent.input(input, { target: { value: '  Renamed Vehicle  ' } });
        await fireEvent.click(screen.getByTestId('save-tag-rename-tag-1'));

        await waitFor(() => {
            expect(renameTag).toHaveBeenCalledWith({
                path: {
                    collection_id: 'collection-1',
                    tag_id: 'tag-1'
                },
                body: {
                    name: 'Renamed Vehicle'
                }
            });
            expect(mocks.loadTags).toHaveBeenCalled();
            expect(mocks.clearTagSelected).not.toHaveBeenCalled();
            expect(screen.queryByTestId('rename-tag-form-tag-1')).not.toBeInTheDocument();
            expect(toast.success).not.toHaveBeenCalled();
        });
    });

    it('shows a toast when renaming a tag fails', async () => {
        vi.mocked(renameTag).mockRejectedValue(new Error('network error'));

        render(TagsMenu, {
            props: {
                collection_id: 'collection-1',
                gridType: 'samples'
            }
        });

        await fireEvent.click(screen.getByTestId('tag-actions-trigger-tag-1'));
        await fireEvent.click(await screen.findByTestId('rename-tag-tag-1'));

        const input = await screen.findByTestId('rename-tag-input-tag-1');
        await fireEvent.input(input, { target: { value: 'Renamed Vehicle' } });
        await fireEvent.click(screen.getByTestId('save-tag-rename-tag-1'));

        await waitFor(() => {
            expect(toast.error).toHaveBeenCalledWith('Failed to rename tag. Please try again.');
        });

        expect(screen.getByTestId('rename-tag-form-tag-1')).toBeVisible();
        expect(mocks.loadTags).not.toHaveBeenCalled();
    });

    it('does not toggle the checkbox when opening the tag actions menu', async () => {
        render(TagsMenu, {
            props: {
                collection_id: 'collection-1',
                gridType: 'samples'
            }
        });

        await fireEvent.click(screen.getByTestId('tag-actions-trigger-tag-1'));

        expect(mocks.tagSelectionToggle).not.toHaveBeenCalled();
    });
});
