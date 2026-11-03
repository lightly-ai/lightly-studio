import { fireEvent, render, screen } from '@testing-library/svelte';
import { get, type Writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as appState from '$app/state';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import AnnotationSourcesTab from './AnnotationSourcesTab.svelte';

const mocks = vi.hoisted(() => ({
    data: null as unknown as Writable<unknown[] | undefined>,
    createSource: vi.fn(),
    renameAnnotationSource: vi.fn(),
    removeSource: vi.fn(),
    toastError: vi.fn()
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
        createMutation: () => ({ mutateAsync: mocks.createSource, isPending: false }),
        useQueryClient: () => ({ invalidateQueries: vi.fn() })
    };
});

vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    renameAnnotationSource: mocks.renameAnnotationSource
}));

vi.mock(
    '$lib/components/AnnotationCollectionsMenu/DeleteAnnotationSource/useDeleteAnnotationSource.svelte',
    () => ({
        useDeleteAnnotationSource: () => ({
            mutation: { isPending: false },
            remove: mocks.removeSource,
            annotationCount: () => undefined
        })
    })
);

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
        mocks.data.set([
            { collection_id: 's1', name: 'ground_truth', annotation_count: 12 },
            { collection_id: 's2', name: 'model_v1', annotation_count: 3 }
        ]);
        mocks.createSource.mockResolvedValue({ collection_id: 's3', name: 'review_round_2' });
        mocks.renameAnnotationSource.mockResolvedValue({ data: {} });
        mockParams({ dataset_id: 'd', collection_id: COLLECTION_ID });
        useCustomLabelColors().clearCustomColors();
        useGlobalStorage().lastAnnotationSource.set({});
    });

    const input = () => screen.getByLabelText('Find or add an annotation source');
    const rename = async (oldName: string, newName: string) => {
        await fireEvent.click(screen.getByRole('button', { name: `Rename ${oldName}` }));
        const field = screen.getByLabelText(`New name for ${oldName}`);
        await fireEvent.input(field, { target: { value: newName } });
        await fireEvent.keyDown(field, { key: 'Enter' });
    };

    it('lists sources with their annotation counts', () => {
        render(AnnotationSourcesTab);

        expect(screen.getByText('ground_truth')).toBeInTheDocument();
        expect(screen.getByText(/12\s+annotations/)).toBeInTheDocument();
        expect(screen.getByText('2 annotation sources')).toBeInTheDocument();
    });

    it('filters to matching sources and adds nothing on Enter', async () => {
        render(AnnotationSourcesTab);
        await fireEvent.input(input(), { target: { value: 'model' } });

        await fireEvent.keyDown(input(), { key: 'Enter' });

        expect(screen.getByText('model_v1')).toBeInTheDocument();
        expect(screen.queryByText('ground_truth')).not.toBeInTheDocument();
        expect(mocks.createSource).not.toHaveBeenCalled();
    });

    it('creates a new source on Enter and highlights it', async () => {
        render(AnnotationSourcesTab);
        await fireEvent.input(input(), { target: { value: 'review_round_2' } });

        await fireEvent.keyDown(input(), { key: 'Enter' });

        expect(mocks.createSource).toHaveBeenCalledWith({
            path: { collection_id: COLLECTION_ID },
            body: { name: 'review_round_2' }
        });
        await vi.waitFor(() => expect(input()).toHaveValue(''));
        mocks.data.update((sources) => [
            ...(sources ?? []),
            { collection_id: 's3', name: 'review_round_2', annotation_count: 0 }
        ]);
        await vi.waitFor(() =>
            expect(screen.getByText('review_round_2').closest('li')?.className).toContain(
                'ring-primary'
            )
        );
    });

    it('renames a source inline', async () => {
        render(AnnotationSourcesTab);

        await rename('model_v1', 'model_v2');

        expect(mocks.renameAnnotationSource).toHaveBeenCalledWith({
            path: { collection_id: COLLECTION_ID, annotation_collection_id: 's2' },
            body: { name: 'model_v2' }
        });
    });

    it('shows an error for a duplicate name', async () => {
        render(AnnotationSourcesTab);

        await rename('model_v1', 'ground_truth');

        expect(mocks.renameAnnotationSource).not.toHaveBeenCalled();
        expect(mocks.toastError).toHaveBeenCalledWith(
            'An annotation source named “ground_truth” already exists.'
        );
    });

    it('moves the custom color to the new name', async () => {
        const colors = useCustomLabelColors();
        colors.setCustomColor('model_v1', '#ff0000', 0.5);
        render(AnnotationSourcesTab);

        await rename('model_v1', 'model_v2');

        await vi.waitFor(() =>
            expect(colors.getCustomColor('model_v2')).toEqual({ color: '#ff0000', alpha: 0.5 })
        );
        expect(colors.getCustomColor('model_v1')).toBeUndefined();
    });

    it('renaming the pencil target keeps it the target', async () => {
        const { lastAnnotationSource } = useGlobalStorage();
        lastAnnotationSource.set({ [COLLECTION_ID]: 'model_v1', other: 'model_v1' });
        render(AnnotationSourcesTab);

        await rename('model_v1', 'model_v2');

        await vi.waitFor(() => expect(get(lastAnnotationSource)[COLLECTION_ID]).toBe('model_v2'));
        expect(get(lastAnnotationSource).other).toBe('model_v1');
    });

    it('confirms a delete with the annotation count and the evaluation warning', async () => {
        render(AnnotationSourcesTab);

        await fireEvent.click(screen.getByRole('button', { name: 'Delete ground_truth' }));

        expect(screen.getByText(/its 12 annotations/)).toBeInTheDocument();
        expect(screen.getByText(/Evaluation runs that use these/)).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
        expect(mocks.removeSource).toHaveBeenCalledOnce();
    });

    it('asks to open a dataset when there is no collection', () => {
        mockParams({});
        render(AnnotationSourcesTab);

        expect(
            screen.getByText('Open a dataset to manage its annotation sources.')
        ).toBeInTheDocument();
    });
});
