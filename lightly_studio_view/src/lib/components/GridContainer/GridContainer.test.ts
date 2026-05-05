import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import GridContainerTestWrapper from './GridContainerTestWrapper.test.svelte';

class MockIntersectionObserver {
    callback: IntersectionObserverCallback;
    targets: Element[] = [];

    static instances: MockIntersectionObserver[] = [];

    constructor(callback: IntersectionObserverCallback) {
        this.callback = callback;
        MockIntersectionObserver.instances.push(this);
    }

    observe(target: Element) {
        this.targets.push(target);
    }

    unobserve() {}
    disconnect() {}
    takeRecords(): IntersectionObserverEntry[] {
        return [];
    }

    trigger(isIntersecting = true) {
        const target = this.targets[0] as Element;
        this.callback(
            [
                {
                    target,
                    isIntersecting,
                    intersectionRatio: isIntersecting ? 1 : 0,
                    time: 0,
                    boundingClientRect: {} as DOMRectReadOnly,
                    intersectionRect: {} as DOMRectReadOnly,
                    rootBounds: null
                }
            ],
            this as unknown as IntersectionObserver
        );
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

describe('GridContainer', () => {
    beforeEach(() => {
        MockIntersectionObserver.instances = [];
        global.IntersectionObserver =
            MockIntersectionObserver as unknown as typeof IntersectionObserver;
    });

    it('renders loading state message', () => {
        const { container } = render(GridContainerTestWrapper, {
            props: {
                status: { loading: true, error: false, empty: false, success: false },
                message: {
                    loading: 'Loading custom text',
                    error: 'Custom error',
                    empty: {
                        title: 'Custom empty title',
                        description: 'Custom empty description'
                    }
                }
            }
        });

        expect(screen.getByText('Loading custom text')).toBeInTheDocument();
        expect(container.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('renders error state message', () => {
        render(GridContainerTestWrapper, {
            props: {
                status: { loading: false, error: true, empty: false, success: false },
                message: {
                    loading: 'Loading custom text',
                    error: 'Custom error',
                    empty: {
                        title: 'Custom empty title',
                        description: 'Custom empty description'
                    }
                }
            }
        });

        expect(screen.getByText('Custom error')).toBeInTheDocument();
    });

    it('renders empty state title and description', () => {
        render(GridContainerTestWrapper, {
            props: {
                status: { loading: false, error: false, empty: true, success: false },
                message: {
                    loading: 'Loading custom text',
                    error: 'Custom error',
                    empty: {
                        title: 'Nothing here',
                        description: 'Try a different filter'
                    }
                }
            }
        });

        expect(screen.getByText('Nothing here')).toBeInTheDocument();
        expect(screen.getByText('Try a different filter')).toBeInTheDocument();
    });

    it('renders success content', () => {
        render(GridContainerTestWrapper, {
            props: {
                status: { loading: false, error: false, empty: false, success: true }
            }
        });

        expect(screen.getByTestId('grid-success-content')).toBeInTheDocument();
    });

    it('triggers loadMore when lazy trigger intersects', () => {
        const onLoadMore = vi.fn();
        render(GridContainerTestWrapper, {
            props: {
                status: { loading: false, error: false, empty: false, success: true },
                loaderDisabled: false,
                onLoadMore
            }
        });

        expect(MockIntersectionObserver.instances).toHaveLength(1);

        MockIntersectionObserver.instances[0].trigger(true);

        expect(onLoadMore).toHaveBeenCalledTimes(1);
    });

    it('does not create observer when loading more is disabled', () => {
        render(GridContainerTestWrapper, {
            props: {
                status: { loading: false, error: false, empty: false, success: true },
                loaderDisabled: true
            }
        });

        expect(MockIntersectionObserver.instances).toHaveLength(0);
    });

    it('shows fetching next page spinner in the footer', () => {
        render(GridContainerTestWrapper, {
            props: {
                status: { loading: false, error: false, empty: false, success: true },
                loaderLoading: true
            }
        });

        expect(screen.getByTestId('grid-container-fetching-next-page')).toBeInTheDocument();
    });
});
