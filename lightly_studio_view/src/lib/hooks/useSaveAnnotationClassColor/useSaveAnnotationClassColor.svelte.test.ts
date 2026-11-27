import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'svelte-sonner';
import { setAnnotationClasses } from '$lib/hooks/useCustomLabelColors';
import { useSaveAnnotationClassColor } from './useSaveAnnotationClassColor.svelte';

const mocks = vi.hoisted(() => ({
    mutateAsync: vi.fn(),
    invalidateQueries: vi.fn()
}));

type MutationOptions = { onError?: (e: unknown) => unknown; onSettled?: () => unknown };

vi.mock('@tanstack/svelte-query', () => ({
    mutationOptions: (options: unknown) => options,
    // Run onError and onSettled after the call, like the real mutation does.
    createMutation: (getOptions: () => MutationOptions) => ({
        mutateAsync: async (variables: unknown) => {
            try {
                return await mocks.mutateAsync(variables);
            } catch (error) {
                getOptions().onError?.(error);
                throw error;
            } finally {
                await getOptions().onSettled?.();
            }
        }
    }),
    useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries })
}));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

const TOAST = 'Could not save the annotation class color.';

const setup = () => {
    setAnnotationClasses('dataset-1', [
        {
            annotation_label_id: 'label-1',
            annotation_label_name: 'cat',
            dataset_id: 'dataset-1',
            color: null,
            alpha: null
        }
    ]);
    return useSaveAnnotationClassColor();
};

describe('useSaveAnnotationClassColor', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.mutateAsync.mockResolvedValue({});
    });

    afterEach(() => setAnnotationClasses('dataset-1', []));

    it('saves the color for the class ID', async () => {
        const { saveClassColor } = setup();

        await saveClassColor('cat', { color: '#ff0000', alpha: 0.5 });

        expect(mocks.mutateAsync).toHaveBeenCalledWith({
            path: { label_id: 'label-1' },
            body: { color: '#ff0000', alpha: 0.5 }
        });
    });

    it('rejects and toasts for an unknown class', async () => {
        const { saveClassColor } = setup();

        await expect(saveClassColor('dog', { color: '#ff0000', alpha: 1 })).rejects.toThrow();

        expect(mocks.mutateAsync).not.toHaveBeenCalled();
        expect(toast.error).toHaveBeenCalledOnce();
        expect(toast.error).toHaveBeenCalledWith(TOAST);
    });

    it('rejects and toasts once when the save fails', async () => {
        const { saveClassColor } = setup();
        mocks.mutateAsync.mockRejectedValue(new Error('boom'));

        await expect(saveClassColor('cat', { color: '#ff0000', alpha: 1 })).rejects.toThrow();

        expect(toast.error).toHaveBeenCalledOnce();
        expect(toast.error).toHaveBeenCalledWith(TOAST);
    });

    it('invalidates only the class list queries', async () => {
        const { saveClassColor } = setup();

        await saveClassColor('cat', { color: '#ff0000', alpha: 1 });

        const { predicate } = mocks.invalidateQueries.mock.calls[0][0] as {
            predicate: (q: { queryKey: unknown[] }) => boolean;
        };
        const matches = (id: string) => predicate({ queryKey: [{ _id: id }] });
        expect(matches('readAnnotationLabels')).toBe(true);
        expect(matches('readAnnotationLabelsWithCounts')).toBe(true);
        expect(matches('readSamples')).toBe(false);
    });

    it('sends a second save of the same class only after the first settles', async () => {
        const { saveClassColor } = setup();
        let finishFirst!: () => void;
        mocks.mutateAsync.mockImplementationOnce(
            () => new Promise<void>((resolve) => (finishFirst = resolve))
        );

        const first = saveClassColor('cat', { color: '#111111', alpha: 1 });
        const second = saveClassColor('cat', { color: '#222222', alpha: 1 });
        await Promise.resolve();
        await Promise.resolve();
        expect(mocks.mutateAsync).toHaveBeenCalledTimes(1);

        finishFirst();
        await Promise.all([first, second]);

        expect(mocks.mutateAsync).toHaveBeenCalledTimes(2);
        expect(mocks.mutateAsync).toHaveBeenLastCalledWith({
            path: { label_id: 'label-1' },
            body: { color: '#222222', alpha: 1 }
        });
    });
});
