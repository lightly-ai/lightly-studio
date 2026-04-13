import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { readable, writable } from 'svelte/store';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import TagsMenu from './TagsMenu.svelte';

const { mockReadImages, mockAddSampleIdsToTagId } = vi.hoisted(() => ({
    mockReadImages: vi.fn(),
    mockAddSampleIdsToTagId: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', async () => {
    const actual = await vi.importActual('$lib/api/lightly_studio_local');
    return {
        ...actual,
        createTag: vi.fn(),
        addSampleIdsToTagId: mockAddSampleIdsToTagId,
        readImages: mockReadImages,
        getAllFrames: vi.fn(),
        getVideoSampleIds: vi.fn(),
        readAnnotationsWithPayload: vi.fn()
    };
});

vi.mock('$lib/hooks/useTags/useTags.js', () => ({
    useTags: () => ({
        tags: readable([
            {
                tag_id: 'tag-1',
                name: 'Vehicle',
                kind: 'sample',
                description: 'Vehicle description'
            }
        ]),
        tagsSelected: readable(new Set<string>()),
        tagSelectionToggle: vi.fn(),
        loadTags: vi.fn()
    })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        getSelectedSampleIds: () => readable(new Set<string>()),
        selectedSampleAnnotationCropIds: writable<Record<string, Set<string>>>({})
    })
}));

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: () => ({
        metadataValues: readable(undefined)
    }),
    createMetadataFilters: vi.fn(() => [])
}));

vi.mock('$lib/hooks/useDimensions/useDimensions', () => ({
    useDimensions: () => ({
        dimensionsValues: readable(null)
    })
}));

vi.mock('$lib/hooks/useVideoFramesBounds/useVideoFramesBounds', () => ({
    useVideoFramesBounds: () => ({
        videoFramesBoundsValues: readable(null)
    })
}));

vi.mock('$lib/hooks/useVideosBounds/useVideosBounds', () => ({
    useVideoBounds: () => ({
        videoBoundsValues: readable(null)
    })
}));

vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({
        filterParams: readable({
            collection_id: 'collection-1',
            mode: 'normal',
            filters: {}
        })
    })
}));

vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', () => ({
    useVideoFilters: () => ({
        filterParams: readable(null)
    })
}));

vi.mock('$lib/hooks/useAnnotationsFilter/useAnnotationsFilter', () => ({
    useSelectedAnnotationsFilter: () => ({
        annotationLabelIds: readable(undefined),
        annotationFilter: readable(undefined)
    })
}));

vi.mock('$lib/hooks/useImagesInfinite/useImagesInfinite', () => ({
    isNormalModeParams: (params: { mode?: string }) => params.mode === 'normal'
}));

describe('TagsMenu', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockReadImages.mockResolvedValue({
            data: {
                data: [{ sample_id: 'sample-a' }, { sample_id: 'sample-b' }]
            }
        });
        mockAddSampleIdsToTagId.mockResolvedValue({
            data: true,
            error: undefined
        });
    });

    it('assigns tags to the current view when no samples are explicitly selected', async () => {
        render(TagsMenu, {
            props: {
                collection_id: 'collection-1',
                gridType: 'samples'
            }
        });

        const input = screen.getByPlaceholderText('Assign tag to selection');

        await fireEvent.focus(input);
        await fireEvent.input(input, { target: { value: 'Vehicle' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        await waitFor(() => {
            expect(mockReadImages).toHaveBeenCalledWith({
                path: { collection_id: 'collection-1' },
                body: {
                    filters: {
                        sample_filter: {
                            sample_ids: undefined,
                            annotations_filter: undefined,
                            tag_ids: undefined,
                            metadata_filters: undefined
                        }
                    }
                }
            });
        });

        await waitFor(() => {
            expect(mockAddSampleIdsToTagId).toHaveBeenCalledWith({
                path: {
                    collection_id: 'collection-1',
                    tag_id: 'tag-1'
                },
                body: {
                    sample_ids: ['sample-a', 'sample-b']
                }
            });
        });
    });
});
