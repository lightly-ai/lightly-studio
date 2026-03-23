import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import SegmentTags from './SegmentTags.svelte';

describe('SegmentTags', () => {
    it('renders nothing when tags array is empty', () => {
        const { container } = render(SegmentTags, {
            props: {
                tags: [],
                onClick: vi.fn()
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
                onClick: vi.fn()
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
                onClick: vi.fn()
            }
        });

        expect(screen.getByTestId('remove-tag-Tag 1')).toBeInTheDocument();
        expect(screen.getByTestId('remove-tag-Tag 2')).toBeInTheDocument();
    });

    it('calls onClick with tag_id when remove button is clicked', async () => {
        const onClick = vi.fn().mockResolvedValue(undefined);
        const tags = [{ tag_id: '123', name: 'Test Tag' }];

        render(SegmentTags, {
            props: {
                tags,
                onClick
            }
        });

        const removeButton = screen.getByTestId('remove-tag-Test Tag');
        await fireEvent.click(removeButton);

        expect(onClick).toHaveBeenCalledWith('123');
        expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('does not call onClick when tag has no tag_id', async () => {
        const onClick = vi.fn().mockResolvedValue(undefined);
        const tags = [{ name: 'Tag Without ID' }];

        render(SegmentTags, {
            props: {
                tags,
                onClick
            }
        });

        const removeButton = screen.getByTestId('remove-tag-Tag Without ID');
        await fireEvent.click(removeButton);

        expect(onClick).not.toHaveBeenCalled();
    });

    it('has correct aria-label on remove button', () => {
        const tags = [{ tag_id: '1', name: 'My Tag' }];

        render(SegmentTags, {
            props: {
                tags,
                onClick: vi.fn()
            }
        });

        const removeButton = screen.getByTestId('remove-tag-My Tag');
        expect(removeButton).toHaveAttribute('aria-label', 'Remove tag My Tag');
    });

    it('handles multiple tags correctly', async () => {
        const onClick = vi.fn().mockResolvedValue(undefined);
        const tags = [
            { tag_id: '1', name: 'Tag 1' },
            { tag_id: '2', name: 'Tag 2' },
            { tag_id: '3', name: 'Tag 3' }
        ];

        render(SegmentTags, {
            props: {
                tags,
                onClick
            }
        });

        const removeButton2 = screen.getByTestId('remove-tag-Tag 2');
        await fireEvent.click(removeButton2);

        expect(onClick).toHaveBeenCalledWith('2');
        expect(onClick).toHaveBeenCalledTimes(1);
    });
});
