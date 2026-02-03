import { addSampleIdsToTagId, createTag } from '$lib/api/lightly_studio_local';
import { QueryClient } from '@tanstack/svelte-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { readable, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type UseTagsCreateDialog } from './TagCreateDialog.svelte';

import TestTagCreateDialog from '$lib/components/TagCreateDialog/TagCreateDialog.test.svelte';
import * as useTags from '$lib/hooks/useTags/useTags';
import type { GridType, TagKind, TagView } from '$lib/services/types';

vi.useFakeTimers();

// Add this mock right here with your other mocks
vi.mock('$lib/components/SampleDetails/SampleDetails.svelte', () => ({
    default: {}
}));

// Mock SDK functions
vi.mock('$lib/api/lightly_studio_local', async () => {
    const actual = await vi.importActual('$lib/api/lightly_studio_local');
    return {
        ...actual,
        createTag: vi.fn(),
        addSampleIdsToTagId: vi.fn().mockResolvedValue({
            data: true,
            error: undefined
        })
    };
});

// Mock global storage with per-collection selection helpers
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => {
        const selectedSampleIdsByCollection = writable<Record<string, Set<string>>>({
            collection1: new Set(['sample1', 'sample2'])
        });
        const selectedSampleAnnotationCropIds = writable<Record<string, Set<string>>>({
            collection1: new Set(['annotation1', 'annotation2'])
        });

        const getSelectedSampleIds = (collectionId: string) =>
            readable(new Set<string>(), (set) =>
                selectedSampleIdsByCollection.subscribe((all) =>
                    set(all[collectionId] ?? new Set())
                )
            );

        return {
            getSelectedSampleIds,
            selectedSampleAnnotationCropIds,
            clearSelectedSamples: vi.fn(),
            clearSelectedSampleAnnotationCrops: vi.fn(),
            // In Svelte 5, we need to make sure all stores are properly subscribed
            lastGridType: writable('samples')
        };
    }
}));

const mockSampleTags: TagView[] = [
    { tag_id: 'tag1', name: 'Test Tag 1', kind: 'sample', description: 'Test Tag 1 description' },
    { tag_id: 'tag2', name: 'Test Tag 2', kind: 'sample', description: 'Test Tag 2 description' }
];

const mockAnnoTags: TagView[] = [
    {
        tag_id: 'tag1',
        name: 'Test Tag 1',
        kind: 'annotation',
        description: 'Test Tag 1 description'
    },
    {
        tag_id: 'tag2',
        name: 'Test Tag 2',
        kind: 'annotation',
        description: 'Test Tag 2 description'
    }
];
const defaultProps: Record<GridType, UseTagsCreateDialog> = {
    samples: {
        collectionId: 'collection1',
        gridType: 'samples',
        tagsQuery: readable({ data: { data: mockSampleTags }, isLoading: false, error: null })
    },
    annotations: {
        collectionId: 'collection1',
        gridType: 'annotations',
        tagsQuery: readable({ data: { data: mockAnnoTags }, isLoading: false, error: null })
    }
} as const;

const renderComponent = (props: Partial<UseTagsCreateDialog> = {}) => {
    const queryClient = new QueryClient();

    return render(TestTagCreateDialog, {
        props: {
            queryClient,
            TagCreateDialogProps: {
                ...defaultProps['samples'],
                ...props
            }
        }
    });
};

const setup = () => {
    vi.spyOn(useTags, 'useTags').mockReturnValueOnce({
        tags: readable(mockSampleTags)
    } as ReturnType<typeof useTags.useTags>);
};

describe.each<{
    gridType: GridType;
    tagKind: TagKind;
    addIdsRequest: Partial<Parameters<typeof addSampleIdsToTagId>[0]>;
}>([
    {
        gridType: 'samples',
        tagKind: 'sample',
        addIdsRequest: {
            body: {
                sample_ids: ['sample1', 'sample2']
            }
        }
    },
    {
        gridType: 'annotations',
        tagKind: 'annotation',
        addSampleIdsToTagId: addSampleIdsToTagId,
        addIdsRequest: {
            body: {
                sample_ids: ['annotation1', 'annotation2']
            }
        }
    }
])('TagCreateDialog $gridType', ({ gridType, tagKind, addIdsRequest }) => {
    beforeEach(() => {
        // Reset all mocks
        vi.resetAllMocks();
        setup();
    });

    it('should render when items are selected', () => {
        renderComponent(defaultProps[gridType]);
        expect(screen.getByText(`Create new Tags`)).toBeInTheDocument();
    });

    it('should filter tags based on search input', async () => {
        renderComponent(defaultProps[gridType]);

        // Open dialog
        await fireEvent.click(screen.getByText(`Create new Tags`));

        // Type in search
        const searchInput = screen.getByPlaceholderText('Create or search tags');
        await fireEvent.input(searchInput, { target: { value: 'Test Tag 1' } });

        // Check filtered results
        expect(screen.getByText('Test Tag 1')).toBeInTheDocument();
        expect(screen.queryByText('Test Tag 2')).not.toBeInTheDocument();
    });

    it('should allow selecting existing tags', async () => {
        renderComponent(defaultProps[gridType]);

        // Open dialog
        await fireEvent.click(screen.getByText(`Create new Tags`));

        // Select a tag
        const checkbox = screen.getByText('Test Tag 1');
        await fireEvent.click(checkbox);

        // Commit button should be visible
        expect(screen.getByText('Save changes')).toBeInTheDocument();
    });

    it('should allow creating and selecting new tags', async () => {
        renderComponent(defaultProps[gridType]);

        // Open dialog
        await fireEvent.click(screen.getByText(`Create new Tags`));

        // Type new tag name
        const searchInput = screen.getByPlaceholderText('Create or search tags');
        await fireEvent.input(searchInput, { target: { value: 'New Tag' } });

        // Click create button
        await fireEvent.click(screen.getByText('Create tag "New Tag"'));

        // New tag should be in the list and selected
        expect(screen.getByText('New Tag')).toBeInTheDocument();
    });

    it('should handle tag creation and assignment', async () => {
        vi.mocked(createTag).mockResolvedValue({
            data: {
                tag_id: 'new-tag-created',
                name: 'New Tag',
                kind: 'sample',
                description: 'New Tag description'
            },
            error: undefined
        });

        renderComponent(defaultProps[gridType]);

        // Open dialog
        await fireEvent.click(screen.getByText(`Create new Tags`));

        // Create new tag
        const searchInput = screen.getByPlaceholderText('Create or search tags');
        await fireEvent.input(searchInput, { target: { value: 'New Tag' } });
        await fireEvent.click(screen.getByText('Create tag "New Tag"'));

        // Save changes
        await fireEvent.click(screen.getByText('Save changes'));

        // Verify SDK calls
        await waitFor(() => {
            expect(createTag).toHaveBeenCalledWith({
                path: {
                    collection_id: 'collection1'
                },
                body: {
                    name: 'New Tag',
                    description: 'New Tag description',
                    kind: tagKind
                }
            });
        });

        // ensure that we've reacted to
        await waitFor(() => {
            expect(addSampleIdsToTagId).toHaveBeenCalledWith({
                ...addIdsRequest,
                path: {
                    collection_id: 'collection1',
                    tag_id: 'new-tag-created'
                }
            });
        });
    });

    it('should handle errors during tag creation', async () => {
        // Mock error response
        vi.mocked(createTag).mockResolvedValue({
            data: undefined,
            error: JSON.stringify(new Error('Failed to create tag'))
        });

        renderComponent(defaultProps[gridType]);

        // Open dialog and create tag
        await fireEvent.click(screen.getByText(`Create new Tags`));
        await fireEvent.input(screen.getByPlaceholderText('Create or search tags'), {
            target: { value: 'New Tag' }
        });
        await fireEvent.click(screen.getByText('Create tag "New Tag"'));
        await fireEvent.click(screen.getByText('Save changes'));

        // Verify error is displayed
        expect(await screen.findByText('Error occured')).toBeInTheDocument();
    });
});
