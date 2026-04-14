import { addSampleIdsToTagId, createTag } from '$lib/api/lightly_studio_local';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TagsMenu from './TagsMenu.svelte';
import type { GridType } from '$lib/types';
import type { TagView } from '$lib/services/types';

const mocks = vi.hoisted(() => ({
    tags: [] as TagView[],
    tagsSelected: new Set<string>(),
    selectedSampleIdsByCollection: {} as Record<string, Set<string>>,
    selectedSampleAnnotationCropIds: {} as Record<string, Set<string>>,
    loadTags: vi.fn(),
    tagSelectionToggle: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', async () => {
    const actual = await vi.importActual('$lib/api/lightly_studio_local');
    return {
        ...actual,
        createTag: vi.fn(),
        addSampleIdsToTagId: vi.fn()
    };
});

vi.mock('$lib/hooks/useTags/useTags.js', () => ({
    useTags: vi.fn(() => ({
        tags: readable(mocks.tags),
        tagsSelected: readable(mocks.tagsSelected),
        tagSelectionToggle: mocks.tagSelectionToggle,
        loadTags: mocks.loadTags
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
        error: vi.fn()
    }
}));

const sampleTag: TagView = {
    tag_id: 'tag-1',
    name: 'Vehicle',
    kind: 'sample',
    description: 'Vehicle description',
    created_at: new Date('2024-01-01T00:00:00.000Z'),
    updated_at: new Date('2024-01-01T00:00:00.000Z')
};

const mockRequest = new Request('http://localhost/api/test');
const mockResponse = new Response(null, { status: 200 });

function renderComponent(gridType: GridType = 'samples') {
    return render(TagsMenu, {
        props: {
            collection_id: 'collection-1',
            gridType
        }
    });
}

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
                description: 'Created Tag description',
                created_at: new Date('2024-01-03T00:00:00.000Z'),
                updated_at: new Date('2024-01-03T00:00:00.000Z')
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

        renderComponent('samples');

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

        renderComponent('annotations');

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
                    description: 'New Annotation Tag description',
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
        renderComponent('samples');

        expect(screen.getByPlaceholderText('Assign tag to selection')).toBeDisabled();
    });
});
