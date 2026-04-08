import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import SegmentTags from './SegmentTags.svelte';

const defaultProps = {
    collectionId: 'collection-1',
    sampleId: 'sample-1'
};

describe('SegmentTags', () => {
    it('renders nothing when tags array is empty', () => {
        const { container } = render(SegmentTags, {
            props: {
                ...defaultProps,
                tags: []
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
            props: { ...defaultProps, tags }
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
            props: { ...defaultProps, tags }
        });

        expect(screen.getByTestId('remove-tag-Tag 1')).toBeInTheDocument();
        expect(screen.getByTestId('remove-tag-Tag 2')).toBeInTheDocument();
    });

    it('has correct aria-label on remove button', () => {
        const tags = [{ tag_id: '1', name: 'My Tag' }];

        render(SegmentTags, {
            props: { ...defaultProps, tags }
        });

        const removeButton = screen.getByTestId('remove-tag-My Tag');
        expect(removeButton).toHaveAttribute('aria-label', 'Remove tag My Tag');
    });

    it('renders multiple tags correctly', () => {
        const tags = [
            { tag_id: '1', name: 'Tag 1' },
            { tag_id: '2', name: 'Tag 2' },
            { tag_id: '3', name: 'Tag 3' }
        ];

        render(SegmentTags, {
            props: { ...defaultProps, tags }
        });

        expect(screen.getByTestId('remove-tag-Tag 1')).toBeInTheDocument();
        expect(screen.getByTestId('remove-tag-Tag 2')).toBeInTheDocument();
        expect(screen.getByTestId('remove-tag-Tag 3')).toBeInTheDocument();
    });
});
