import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import Page from './+page.svelte';
import { goto } from '$app/navigation';
import type { PageData } from './$types';

// The labeling route sits under the collection layout, which resolves the hierarchy by the
// dataset slot — so that slot must be a collection id. Navigation forwards the route dataset
// id (a collection id); the labeling page derives the real dataset id from the loaded collection.
const ROUTE_DATASET_ID = 'route-dataset-id';
const pageData = {} as PageData;

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$app/state', () => ({
    page: {
        params: {
            dataset_id: 'route-dataset-id',
            collection_type: 'mcap',
            collection_id: 'collection-1'
        }
    }
}));

const { toggleSampleSelection, workflow, grid } = vi.hoisted(() => ({
    toggleSampleSelection: vi.fn(),
    workflow: { projectId: null as string | null, selected: [] as string[] },
    // The params getter the page passes to the grid query.
    grid: { getParams: null as (() => { filter: unknown }) | null }
}));

vi.mock('$lib/hooks/useWorkflowProject/useWorkflowProject.svelte', () => ({
    useWorkflowProject: () => ({
        get projectId() {
            return workflow.projectId;
        }
    })
}));

vi.mock('$lib/hooks/useWorkflowStatusFilter/useWorkflowStatusFilter', () => ({
    useWorkflowStatusFilter: () => ({ selectedWorkflowStates: writable(workflow.selected) })
}));

vi.mock('$lib/hooks/useWorkflowStatusCounts/useWorkflowStatusCounts.svelte', () => ({
    useWorkflowStatusCounts: () => ({ counts: null, refreshIfOlderThan: vi.fn() })
}));

vi.mock('$lib/hooks/useTags/useTags', () => ({
    useTags: () => ({ tagsSelected: writable(new Set<string>()) })
}));

vi.mock('$lib/hooks', async () => ({
    useMcapSequenceFilters: (
        await vi.importActual<
            typeof import('$lib/hooks/useMcapSequenceFilters/useMcapSequenceFilters')
        >('$lib/hooks/useMcapSequenceFilters/useMcapSequenceFilters')
    ).useMcapSequenceFilters,
    useGlobalStorage: () => ({
        setfilteredSampleCount: vi.fn(),
        sampleSize: writable({ width: 6, height: 200 }),
        textEmbedding: writable(null),
        getSelectedSampleIds: () => writable(new Set<string>()),
        toggleSampleSelection
    }),
    useMcapSequencesInfinite: (getParams: () => { filter: unknown }) => {
        grid.getParams = getParams;
        return {
            data: writable(
                Array.from({ length: 11 }, (_, index) => ({
                    sample_id: `sequence-${index + 1}`,
                    sample_count: 5
                }))
            ),
            query: {
                isPending: false,
                isSuccess: true,
                isError: false,
                hasNextPage: false,
                isFetchingNextPage: false
            },
            loadMore: vi.fn(),
            totalCount: writable(1)
        };
    }
}));

vi.mock('$lib/hooks/useMcapSequenceTicks/useMcapSequenceTicks.svelte', () => ({
    useMcapSequenceTicks: () => ({ ticks: { data: { ticks: [] } } })
}));

vi.mock('$lib/hooks/useMcapSequenceSummary/useMcapSequenceSummary', () => ({
    useMcapSequenceSummary: () => ({ summary: { data: { reference_frames: [] } } })
}));

class MockResizeObserver {
    constructor(private callback: ResizeObserverCallback) {}

    observe(target: Element) {
        this.callback(
            [{ target, contentRect: { width: 2000, height: 1000 } } as ResizeObserverEntry],
            this
        );
    }

    unobserve() {}
    disconnect() {}
}

class MockIntersectionObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
        return [];
    }
    root = null;
    rootMargin = '';
    thresholds = [];
}

describe('point-clouds/+page.svelte', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        workflow.projectId = null;
        workflow.selected = [];
        global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
        global.IntersectionObserver =
            MockIntersectionObserver as unknown as typeof IntersectionObserver;
        Element.prototype.scrollTo = vi.fn();
        vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(1000);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.clearAllMocks();
    });

    it('selects a sequence on click', async () => {
        render(Page, { props: { data: pageData } });

        await fireEvent.click(screen.getByRole('button', { name: 'View MCAP sequence 1' }));

        expect(toggleSampleSelection).toHaveBeenCalledWith('sequence-1', 'collection-1');
        expect(goto).not.toHaveBeenCalled();
    });

    it('navigates with the route dataset id (a collection id the layout can resolve)', async () => {
        render(Page, { props: { data: pageData } });

        await fireEvent.dblClick(screen.getByRole('button', { name: 'View MCAP sequence 1' }));

        expect(goto).toHaveBeenCalledOnce();
        const destination = vi.mocked(goto).mock.calls[0][0] as string;
        expect(destination).toContain(ROUTE_DATASET_ID);
    });

    it('filters the grid by the selected workflow states when the dataset has a project', () => {
        workflow.projectId = 'project-1';
        workflow.selected = ['accepted', 'not_in_workflow'];

        render(Page, { props: { data: pageData } });

        expect(grid.getParams?.().filter).toEqual({
            filter_type: 'mcap_sequence',
            sample_filter: { workflow_states: ['accepted', 'not_in_workflow'] }
        });
    });
});
