import { beforeEach, describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import SegmentTags from './SegmentTags.svelte';
import * as hooks from '$lib/hooks';
import type { TagView } from '$lib/services/types';

vi.mock('./AddTagPopover.svelte', async () => {
    const module = await import('./AddTagPopover.mock.svelte');
    return { default: module.default };
});

const removeTagFromSampleMock = vi.fn();
const addExistingMock = vi.fn();
const createAndAddMock = vi.fn();
const loadTagsMock = vi.fn();

vi.spyOn(hooks, 'useRemoveTagFromSample').mockReturnValue({
    removeTagFromSample: removeTagFromSampleMock
} as ReturnType<typeof hooks.useRemoveTagFromSample>);

vi.spyOn(hooks, 'useGlobalStorage').mockReturnValue({
    collections: writable({
        'collection-1': {
            sampleType: 'video',
            parentCollectionId: null,
            collectionId: 'collection-1'
        }
    })
} as unknown as ReturnType<typeof hooks.useGlobalStorage>);

vi.spyOn(hooks, 'useTags').mockImplementation(() => ({
    tags: writable<TagView[]>([
        {
            tag_id: 'existing-tag',
            name: 'Existing Tag',
            kind: 'sample',
            description: '',
            created_at: new Date(),
            updated_at: new Date()
        },
        {
            tag_id: 'other-tag',
            name: 'Other Tag',
            kind: 'sample',
            description: '',
            created_at: new Date(),
            updated_at: new Date()
        }
    ]),
    loadTags: loadTagsMock,
    tagsSelected: writable(new Set<string>()),
    clearTagsSelected: vi.fn(),
    clearTagSelected: vi.fn(),
    tagSelectionToggle: vi.fn(),
    isLoading: writable(false),
    error: writable(null)
}));

vi.spyOn(hooks, 'useAddTagToSample').mockReturnValue({
    busy: writable(false),
    addExisting: addExistingMock,
    createAndAdd: createAndAddMock
} as ReturnType<typeof hooks.useAddTagToSample>);

describe('SegmentTags', () => {
    beforeEach(() => {
        removeTagFromSampleMock.mockReset();
        addExistingMock.mockReset();
        createAndAddMock.mockReset();
        loadTagsMock.mockReset();
    });

    it('renders nothing when tags array is empty', () => {
        const { container } = render(SegmentTags, {
            props: {
                tags: [],
                collectionId: 'collection-1',
                sampleId: 'sample-1'
            }
        });

        expect(container.querySelector('[data-testid="segment-tag-name"]')).not.toBeInTheDocument();
    });

    it('renders all tags with their names', () => {
        const tags = [
            { tag_id: '1', name: 'Tag 1' },
            { tag_id: '2', name: 'Tag 2' },
            { tag_id: '3', name: 'Tag 3' }
        ];

        render(SegmentTags, {
            props: {
                tags,
                collectionId: 'collection-1',
                sampleId: 'sample-1'
            }
        });

        const tagElements = screen.getAllByTestId('segment-tag-name');
        expect(tagElements).toHaveLength(3);
        expect(tagElements[0]).toHaveTextContent('Tag 1');
        expect(tagElements[1]).toHaveTextContent('Tag 2');
        expect(tagElements[2]).toHaveTextContent('Tag 3');
    });

    it('renders remove button for each tag', () => {
        const tags = [
            { tag_id: '1', name: 'Tag 1' },
            { tag_id: '2', name: 'Tag 2' }
        ];

        render(SegmentTags, {
            props: {
                tags,
                collectionId: 'collection-1',
                sampleId: 'sample-1'
            }
        });

        expect(screen.getByTestId('remove-tag-Tag 1')).toBeInTheDocument();
        expect(screen.getByTestId('remove-tag-Tag 2')).toBeInTheDocument();
    });

    it('calls removeTagFromSample and onRefetch when remove button is clicked', async () => {
        const onRefetch = vi.fn();
        const tags = [{ tag_id: '123', name: 'Test Tag' }];

        removeTagFromSampleMock.mockClear();
        removeTagFromSampleMock.mockResolvedValue(undefined);

        render(SegmentTags, {
            props: {
                tags,
                collectionId: 'collection-1',
                sampleId: 'sample-1',
                onRefetch
            }
        });

        const removeButton = screen.getByTestId('remove-tag-Test Tag');
        await fireEvent.click(removeButton);

        expect(removeTagFromSampleMock).toHaveBeenCalledWith('sample-1', '123');
        expect(removeTagFromSampleMock).toHaveBeenCalledTimes(1);
        expect(onRefetch).toHaveBeenCalledTimes(1);
    });

    it('does not render remove button when tag has no tag_id', () => {
        const tags = [{ name: 'Tag Without ID' }];

        removeTagFromSampleMock.mockClear();

        render(SegmentTags, {
            props: {
                tags,
                collectionId: 'collection-1',
                sampleId: 'sample-1'
            }
        });

        expect(screen.queryByTestId('remove-tag-Tag Without ID')).not.toBeInTheDocument();
        expect(removeTagFromSampleMock).not.toHaveBeenCalled();
    });

    it('has correct aria-label on remove button', () => {
        const tags = [{ tag_id: '1', name: 'My Tag' }];

        render(SegmentTags, {
            props: {
                tags,
                collectionId: 'collection-1',
                sampleId: 'sample-1'
            }
        });

        const removeButton = screen.getByTestId('remove-tag-My Tag');
        expect(removeButton).toHaveAttribute('aria-label', 'Remove tag My Tag');
    });

    it('handles multiple tags correctly', async () => {
        const tags = [
            { tag_id: '1', name: 'Tag 1' },
            { tag_id: '2', name: 'Tag 2' },
            { tag_id: '3', name: 'Tag 3' }
        ];

        removeTagFromSampleMock.mockClear();
        removeTagFromSampleMock.mockResolvedValue(undefined);

        render(SegmentTags, {
            props: {
                tags,
                collectionId: 'collection-1',
                sampleId: 'sample-1'
            }
        });

        const removeButton2 = screen.getByTestId('remove-tag-Tag 2');
        await fireEvent.click(removeButton2);

        expect(removeTagFromSampleMock).toHaveBeenCalledWith('sample-1', '2');
        expect(removeTagFromSampleMock).toHaveBeenCalledTimes(1);
    });

    it('calls addExisting when selecting a tag that already exists in the collection', async () => {
        render(SegmentTags, {
            props: {
                tags: [],
                collectionId: 'collection-1',
                sampleId: 'sample-1'
            }
        });

        await fireEvent.click(screen.getByTestId('mock-add-existing'));

        expect(addExistingMock).toHaveBeenCalledWith({
            tag_id: 'existing-tag',
            name: 'Existing Tag',
            kind: 'sample',
            description: '',
            created_at: expect.any(Date),
            updated_at: expect.any(Date)
        });
        expect(addExistingMock).toHaveBeenCalledTimes(1);
        expect(createAndAddMock).not.toHaveBeenCalled();
    });

    it('calls createAndAdd when selecting a new tag name', async () => {
        render(SegmentTags, {
            props: {
                tags: [],
                collectionId: 'collection-1',
                sampleId: 'sample-1'
            }
        });

        await fireEvent.click(screen.getByTestId('mock-add-new'));

        expect(createAndAddMock).toHaveBeenCalledWith('Fresh Tag');
        expect(createAndAddMock).toHaveBeenCalledTimes(1);
        expect(addExistingMock).not.toHaveBeenCalled();
    });
});
