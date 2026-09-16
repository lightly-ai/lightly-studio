import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import McapSequencesGridTestWrapper from './McapSequencesGridTestWrapper.test.svelte';

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ sampleSize: writable({ width: 6, height: 200 }) })
}));

class MockResizeObserver {
    constructor(private callback: ResizeObserverCallback) {}

    observe(target: Element) {
        this.callback(
            [
                {
                    target,
                    contentRect: { width: 2000, height: 1000 } as DOMRectReadOnly,
                    borderBoxSize: [] as ReadonlyArray<ResizeObserverSize>,
                    contentBoxSize: [] as ReadonlyArray<ResizeObserverSize>,
                    devicePixelContentBoxSize: [] as ReadonlyArray<ResizeObserverSize>
                }
            ],
            this
        );
    }

    unobserve() {}
    disconnect() {}
}

class MockIntersectionObserver {
    constructor(private callback: IntersectionObserverCallback) {}

    observe(target: Element) {
        this.callback([{ isIntersecting: true, target } as IntersectionObserverEntry], this);
    }

    unobserve() {}
    disconnect() {}
    takeRecords() {
        return [];
    }
    get root() {
        return null;
    }
    get rootMargin() {
        return '';
    }
    get thresholds() {
        return [];
    }
}

describe('McapSequencesGrid', () => {
    const sequences = [{ sampleId: 'sequence-1', sampleCount: 5 }];
    const defaultProps = {
        sequences,
        isLoading: false,
        isEmpty: false,
        isError: false,
        hasNextPage: false,
        isFetchingNextPage: false,
        onLoadMore: vi.fn(),
        onSequenceClick: vi.fn()
    };

    beforeEach(() => {
        global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
        global.IntersectionObserver =
            MockIntersectionObserver as unknown as typeof IntersectionObserver;
        Element.prototype.scrollTo = vi.fn();
        vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(1000);
    });

    afterEach(() => vi.restoreAllMocks());

    it('renders the error state when isError is true', () => {
        render(McapSequencesGridTestWrapper, {
            props: { ...defaultProps, isError: true }
        });
        expect(screen.getByText('Something went wrong.')).toBeInTheDocument();
    });

    it('renders the loading and empty messages for their respective states', async () => {
        const { rerender } = render(McapSequencesGridTestWrapper, {
            props: { ...defaultProps, sequences: [], isLoading: true }
        });
        expect(screen.getByText('Loading sequences...')).toBeInTheDocument();

        await rerender({ ...defaultProps, sequences: [], isEmpty: true });
        expect(screen.getByText('No sequences found')).toBeInTheDocument();
    });

    it('opens the selected MCAP sequence', async () => {
        const onSequenceClick = vi.fn();
        render(McapSequencesGridTestWrapper, { props: { ...defaultProps, onSequenceClick } });

        await fireEvent.click(screen.getByRole('button', { name: 'View MCAP sequence 1' }));

        expect(onSequenceClick).toHaveBeenCalledWith(sequences[0].sampleId);
    });

    it('loads another page when it is available', () => {
        const onLoadMore = vi.fn();
        render(McapSequencesGridTestWrapper, {
            props: { ...defaultProps, hasNextPage: true, onLoadMore }
        });

        expect(onLoadMore).toHaveBeenCalledOnce();
    });
});
