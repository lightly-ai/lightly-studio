import { fireEvent, render, screen } from '@testing-library/svelte';
import type { Writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as appState from '$app/state';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import AnnotationSourcesTab from './AnnotationSourcesTab.svelte';

const mocks = vi.hoisted(() => ({
    data: null as unknown as Writable<unknown[] | undefined>,
    removeSource: vi.fn(),
    goto: vi.fn(),
    toastError: vi.fn(),
    sourcesError: false
}));

// The query data is a store, so the tab reacts when a test changes it.
vi.mock('@tanstack/svelte-query', async (importOriginal) => {
    const { writable, fromStore } = await import('svelte/store');
    mocks.data = writable(undefined);
    const data = fromStore(mocks.data);
    return {
        ...(await importOriginal<object>()),
        createQuery: () => ({
            get data() {
                return data.current;
            },
            isLoading: false,
            get isError() {
                return mocks.sourcesError;
            }
        }),
        useQueryClient: () => ({ invalidateQueries: vi.fn() })
    };
});

vi.mock('./DeleteAnnotationSourceDialog/useDeleteAnnotationSource.svelte', () => ({
    useDeleteAnnotationSource: (
        getParams: () => { collectionId: string; onDeleted: () => void }
    ) => ({
        mutation: { isPending: false },
        remove: () => {
            mocks.removeSource(getParams().collectionId);
            getParams().onDeleted();
        }
    })
}));

vi.mock('$app/navigation', () => ({ goto: mocks.goto }));

vi.mock('svelte-sonner', () => ({ toast: { error: mocks.toastError, success: vi.fn() } }));

const COLLECTION_ID = 'c1';

const source = (collectionId: string, name: string, count: number, parentId = COLLECTION_ID) => ({
    collection_id: collectionId,
    name,
    annotation_count: count,
    parent_collection_id: parentId,
    parent_sample_type: 'image'
});

const mockParams = (params: Record<string, string>) => {
    vi.spyOn(appState, 'page', 'get').mockReturnValue({
        params
    } as unknown as typeof appState.page);
};

describe('AnnotationSourcesTab', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.sourcesError = false;
        mocks.data.set([source('s1', 'ground_truth', 12), source('s2', 'model_v1', 3)]);
        mockParams({ dataset_id: 'd', collection_id: COLLECTION_ID });
        useGlobalStorage().lastAnnotationSource.set({});
    });

    it('lists sources with their annotation counts', () => {
        render(AnnotationSourcesTab);

        expect(screen.getByText('ground_truth')).toBeInTheDocument();
        expect(screen.getByText(/12\s+annotations/)).toBeInTheDocument();
        expect(screen.getByText('2 annotation sources')).toBeInTheDocument();
    });

    it('names where each source lives when the sources live in more than one place', () => {
        mocks.data.set([
            { ...source('s1', 'events', 4, 'videos-1'), parent_sample_type: 'video' },
            { ...source('s2', 'detections', 18, 'frames-1'), parent_sample_type: 'video_frame' }
        ]);
        render(AnnotationSourcesTab);

        expect(screen.getByText('Videos')).toBeInTheDocument();
        expect(screen.getByText('Frames')).toBeInTheDocument();
    });

    it('does not name where the sources live when they all live in one place', () => {
        render(AnnotationSourcesTab);

        expect(screen.queryByText('Images')).not.toBeInTheDocument();
    });

    it('shows an error without a count when the sources fail to load', () => {
        mocks.sourcesError = true;
        mocks.data.set(undefined);
        render(AnnotationSourcesTab);

        expect(screen.getByText('Could not load the annotation sources.')).toBeInTheDocument();
        expect(screen.queryByText(/annotation sources?$/)).not.toBeInTheDocument();
        expect(screen.queryByText('Loading annotation sources…')).not.toBeInTheDocument();
    });

    it('confirms a delete with the annotation count and the evaluation warning', async () => {
        render(AnnotationSourcesTab);

        await fireEvent.click(screen.getByRole('button', { name: 'Delete ground_truth' }));

        expect(screen.getByText(/its 12 annotations/)).toBeInTheDocument();
        expect(screen.getByText(/that evaluation runs use cannot be deleted/)).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
        expect(mocks.removeSource).toHaveBeenCalledOnce();
    });

    it('deletes a source from the collection it belongs to', async () => {
        mocks.data.set([source('s1', 'events', 4), source('s2', 'detections', 18, 'frames-1')]);
        render(AnnotationSourcesTab);

        await fireEvent.click(screen.getByRole('button', { name: 'Delete detections' }));
        await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

        expect(mocks.removeSource).toHaveBeenCalledWith('frames-1');
    });

    describe('on the annotations grid of a source', () => {
        beforeEach(() => {
            mockParams({ dataset_id: 'd', collection_type: 'annotation', collection_id: 's2' });
            mocks.data.set([source('s1', 'events', 4), source('s2', 'detections', 18, 'frames-1')]);
        });

        it('leaves the grid of a deleted source for the collection it belonged to', async () => {
            render(AnnotationSourcesTab);

            await fireEvent.click(screen.getByRole('button', { name: 'Delete detections' }));
            await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

            expect(mocks.goto).toHaveBeenCalledWith('/datasets/d/annotation/frames-1', {
                invalidateAll: true
            });
        });

        it('stays on the grid when another source is deleted', async () => {
            render(AnnotationSourcesTab);

            await fireEvent.click(screen.getByRole('button', { name: 'Delete events' }));
            await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

            expect(mocks.goto).not.toHaveBeenCalled();
        });
    });

    it('asks to open a dataset when there is no collection', () => {
        mockParams({});
        render(AnnotationSourcesTab);

        expect(
            screen.getByText('Open a dataset to manage its annotation sources.')
        ).toBeInTheDocument();
    });
});
