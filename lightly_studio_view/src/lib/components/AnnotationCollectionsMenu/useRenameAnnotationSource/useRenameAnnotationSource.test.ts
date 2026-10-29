import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRenameAnnotationSource } from './useRenameAnnotationSource';

const mocks = vi.hoisted(() => ({
    invalidateQueries: vi.fn(),
    renameAnnotationSource: vi.fn(),
    toastError: vi.fn(),
    onRenamed: vi.fn()
}));

vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries })
}));

vi.mock('$lib/api/lightly_studio_local', () => ({
    renameAnnotationSource: mocks.renameAnnotationSource
}));

vi.mock('svelte-sonner', () => ({
    toast: { error: mocks.toastError }
}));

const sources = [
    { id: 's1', name: 'ground_truth' },
    { id: 's2', name: 'predictions' }
];

const setup = () =>
    useRenameAnnotationSource(() => ({
        collectionId: 'col-1',
        sources,
        onRenamed: mocks.onRenamed
    }));

describe('useRenameAnnotationSource', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renames the source and refetches', async () => {
        mocks.renameAnnotationSource.mockResolvedValue({ data: {} });
        const { rename } = setup();

        await rename(sources[1], 'model_v2');

        expect(mocks.renameAnnotationSource).toHaveBeenCalledWith({
            path: { collection_id: 'col-1', annotation_collection_id: 's2' },
            body: { name: 'model_v2' }
        });
        expect(mocks.invalidateQueries).toHaveBeenCalledOnce();
        expect(mocks.onRenamed).toHaveBeenCalledOnce();
    });

    it('rejects a name that another source uses', async () => {
        const { rename } = setup();

        await rename(sources[1], 'ground_truth');

        expect(mocks.renameAnnotationSource).not.toHaveBeenCalled();
        expect(mocks.toastError).toHaveBeenCalledWith(
            'An annotation source named “ground_truth” already exists.'
        );
        expect(mocks.onRenamed).not.toHaveBeenCalled();
    });

    it('shows the server error and keeps editing when the rename fails', async () => {
        mocks.renameAnnotationSource.mockResolvedValue({ error: { error: 'Name taken.' } });
        const { rename } = setup();

        await rename(sources[1], 'model_v2');

        expect(mocks.toastError).toHaveBeenCalledWith('Name taken.');
        expect(mocks.onRenamed).not.toHaveBeenCalled();
    });
});
