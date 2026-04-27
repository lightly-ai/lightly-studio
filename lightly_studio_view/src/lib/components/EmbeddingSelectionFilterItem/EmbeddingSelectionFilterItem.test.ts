import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import { writable } from 'svelte/store';
import EmbeddingSelectionFilterItem from './EmbeddingSelectionFilterItem.svelte';

const mocks = vi.hoisted(() => ({
    setRangeSelectionForCollection: vi.fn(),
    useEmbeddingFilterForImages: vi.fn(),
    useEmbeddingFilterForVideos: vi.fn()
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        setRangeSelectionForCollection: mocks.setRangeSelectionForCollection
    })
}));

vi.mock('$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForImages', () => ({
    useEmbeddingFilterForImages: mocks.useEmbeddingFilterForImages
}));

vi.mock('$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForVideos', () => ({
    useEmbeddingFilterForVideos: mocks.useEmbeddingFilterForVideos
}));

const imageEffectiveCount = writable(1);
const imageIsVisible = writable(false);
const imageSetVisibility = vi.fn();
const imageClearFilter = vi.fn();

const videoEffectiveCount = writable(3);
const videoIsVisible = writable(false);
const videoSetVisibility = vi.fn();
const videoClearFilter = vi.fn();

describe('EmbeddingSelectionFilterItem', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        imageEffectiveCount.set(1);
        imageIsVisible.set(false);
        videoEffectiveCount.set(3);
        videoIsVisible.set(false);

        mocks.useEmbeddingFilterForImages.mockReturnValue({
            effectiveCount: imageEffectiveCount,
            isVisible: imageIsVisible,
            setVisibility: imageSetVisibility,
            clearFilter: imageClearFilter
        });

        mocks.useEmbeddingFilterForVideos.mockReturnValue({
            effectiveCount: videoEffectiveCount,
            isVisible: videoIsVisible,
            setVisibility: videoSetVisibility,
            clearFilter: videoClearFilter
        });
    });

    it('uses image hook only and renders image label in images view', () => {
        render(EmbeddingSelectionFilterItem, {
            props: {
                collectionIdStore: writable('collection-id'),
                isVideos: false,
                isImages: true
            }
        });

        expect(mocks.useEmbeddingFilterForImages).toHaveBeenCalledOnce();
        expect(mocks.useEmbeddingFilterForVideos).not.toHaveBeenCalled();
        expect(screen.getByTestId('embedding-selection-filter-chip')).toBeInTheDocument();
        expect(screen.getByText('Embedding Plot Filter')).toBeInTheDocument();
        expect(screen.getByText(/1\s*image/i)).toBeInTheDocument();
    });

    it('uses video hook only and renders video label in videos view', () => {
        render(EmbeddingSelectionFilterItem, {
            props: {
                collectionIdStore: writable('collection-id'),
                isVideos: true,
                isImages: false
            }
        });

        expect(mocks.useEmbeddingFilterForVideos).toHaveBeenCalledOnce();
        expect(mocks.useEmbeddingFilterForImages).not.toHaveBeenCalled();
        expect(screen.getByText(/3\s*videos/i)).toBeInTheDocument();
    });

    it('calls active hook setVisibility when checkbox is toggled', async () => {
        render(EmbeddingSelectionFilterItem, {
            props: {
                collectionIdStore: writable('collection-id'),
                isVideos: true,
                isImages: false
            }
        });

        await fireEvent.click(screen.getByLabelText('Embedding plot filter'));
        expect(videoSetVisibility).toHaveBeenCalledWith(true);
        expect(imageSetVisibility).not.toHaveBeenCalled();
    });

    it('calls active hook clearFilter when clear button is clicked', async () => {
        render(EmbeddingSelectionFilterItem, {
            props: {
                collectionIdStore: writable('collection-id'),
                isVideos: false,
                isImages: true
            }
        });

        await fireEvent.click(screen.getByLabelText('Clear embedding plot filter'));
        expect(imageClearFilter).toHaveBeenCalledOnce();
        expect(videoClearFilter).not.toHaveBeenCalled();
    });

    it('does not render when there is no plot filter context', () => {
        render(EmbeddingSelectionFilterItem, {
            props: {
                collectionIdStore: writable('collection-id'),
                isVideos: false,
                isImages: false
            }
        });

        expect(screen.queryByTestId('embedding-selection-filter-chip')).not.toBeInTheDocument();
    });
});
