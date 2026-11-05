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
    // The collection that owns the sources, when it is not the route collection.
    ownerId: undefined as string | undefined
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
            isError: false
        }),
        useQueryClient: () => ({ invalidateQueries: vi.fn() })
    };
});

vi.mock('./DeleteAnnotationSourceDialog/useDeleteAnnotationSource.svelte', () => ({
    useDeleteAnnotationSource: (getParams: () => { onDeleted: () => void }) => ({
        mutation: { isPending: false },
        remove: () => {
            mocks.removeSource();
            getParams().onDeleted();
        }
    })
}));

vi.mock('$app/navigation', () => ({ goto: mocks.goto }));

vi.mock('$lib/hooks/useAnnotationSourceOwnerId/useAnnotationSourceOwnerId.svelte', () => ({
    useAnnotationSourceOwnerId: (getCollectionId: () => string) => ({
        get ownerCollectionId() {
            return mocks.ownerId ?? getCollectionId();
        }
    })
}));

vi.mock('svelte-sonner', () => ({ toast: { error: mocks.toastError, success: vi.fn() } }));

const COLLECTION_ID = 'c1';

const mockParams = (params: Record<string, string>) => {
    vi.spyOn(appState, 'page', 'get').mockReturnValue({
        params
    } as unknown as typeof appState.page);
};

describe('AnnotationSourcesTab', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.ownerId = undefined;
        mocks.data.set([
            { collection_id: 's1', name: 'ground_truth', annotation_count: 12 },
            { collection_id: 's2', name: 'model_v1', annotation_count: 3 }
        ]);
        mockParams({ dataset_id: 'd', collection_id: COLLECTION_ID });
        useGlobalStorage().lastAnnotationSource.set({});
    });

    it('lists sources with their annotation counts', () => {
        render(AnnotationSourcesTab);

        expect(screen.getByText('ground_truth')).toBeInTheDocument();
        expect(screen.getByText(/12\s+annotations/)).toBeInTheDocument();
        expect(screen.getByText('2 annotation sources')).toBeInTheDocument();
    });

    it('confirms a delete with the annotation count and the evaluation warning', async () => {
        render(AnnotationSourcesTab);

        await fireEvent.click(screen.getByRole('button', { name: 'Delete ground_truth' }));

        expect(screen.getByText(/its 12 annotations/)).toBeInTheDocument();
        expect(screen.getByText(/that evaluation runs use cannot be deleted/)).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
        expect(mocks.removeSource).toHaveBeenCalledOnce();
    });

    describe('on the annotations grid of a source', () => {
        beforeEach(() => {
            mockParams({ dataset_id: 'd', collection_type: 'annotation', collection_id: 's2' });
            mocks.ownerId = COLLECTION_ID;
        });

        it('leaves the grid of a deleted source for the owner collection', async () => {
            render(AnnotationSourcesTab);

            await fireEvent.click(screen.getByRole('button', { name: 'Delete model_v1' }));
            await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));

            expect(mocks.goto).toHaveBeenCalledWith(`/datasets/d/annotation/${COLLECTION_ID}`, {
                invalidateAll: true
            });
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
