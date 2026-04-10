import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import SegmentTags from './SegmentTags.svelte';
import * as hooks from '$lib/hooks';

const removeTagFromSampleMock = vi.fn();

vi.spyOn(hooks, 'useRemoveTagFromSample').mockReturnValue({
    removeTagFromSample: removeTagFromSampleMock
} as ReturnType<typeof hooks.useRemoveTagFromSample>);

describe('SegmentTags', () => {
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
});
