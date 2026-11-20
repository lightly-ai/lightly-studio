import { describe, expect, it, vi } from 'vitest';
import { useAnnotation } from './useAnnotation';

const updateAnnotations = vi.fn().mockResolvedValue(undefined);

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@tanstack/svelte-query')>()),
    createQuery: vi.fn(() => ({})),
    useQueryClient: () => ({ invalidateQueries: vi.fn() })
}));
vi.mock('../useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: () => ({ updateAnnotations })
}));
vi.mock('svelte-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

describe('useAnnotation', () => {
    it('refreshes the parent once on refetch and once after a save', async () => {
        const onUpdate = vi.fn();
        const { refetch, updateAnnotation } = useAnnotation(() => ({
            collectionId: 'images',
            annotationId: 'annotation',
            onUpdate
        }));

        refetch();
        expect(onUpdate).toHaveBeenCalledTimes(1);

        await updateAnnotation({ annotation_id: 'annotation', collection_id: 'images' });
        expect(onUpdate).toHaveBeenCalledTimes(2);
    });
});
