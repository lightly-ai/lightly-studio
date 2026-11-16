import { toast } from 'svelte-sonner';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useStartSequenceTrack } from './useStartSequenceTrack.svelte';

const { mutateAsync, invalidateQueries } = vi.hoisted(() => ({
    mutateAsync: vi.fn(),
    invalidateQueries: vi.fn()
}));

vi.mock('@tanstack/svelte-query', () => ({
    createMutation: () => ({ mutateAsync }),
    useQueryClient: () => ({ invalidateQueries })
}));
vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', () => ({
    startSequenceTrackMutation: () => ({})
}));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

describe('useStartSequenceTrack', () => {
    const onStarted = vi.fn();
    const params = {
        getDatasetId: () => 'dataset-1',
        getSequenceId: () => 'sequence-1',
        onStarted
    };

    beforeEach(() => {
        vi.resetAllMocks();
        mutateAsync.mockResolvedValue({});
        onStarted.mockResolvedValue(undefined);
    });

    it('starts the track, then refreshes the track bars, tick details and the tick', async () => {
        const started = await useStartSequenceTrack(params).handleStartTrack('annotation-1');

        expect(started).toBe(true);
        expect(mutateAsync).toHaveBeenCalledWith({
            path: { dataset_id: 'dataset-1', sequence_id: 'sequence-1' },
            body: { annotation_id: 'annotation-1' }
        });
        const queryIds = invalidateQueries.mock.calls.map(([{ queryKey }]) => queryKey[0]._id);
        expect(queryIds).toEqual(['getSequenceTracks', 'getTickDetails']);
        expect(onStarted).toHaveBeenCalledOnce();
    });

    it('reports a failure without refreshing anything', async () => {
        mutateAsync.mockRejectedValue(new Error('409'));

        const started = await useStartSequenceTrack(params).handleStartTrack('annotation-1');

        expect(started).toBe(false);
        expect(toast.error).toHaveBeenCalledOnce();
        expect(invalidateQueries).not.toHaveBeenCalled();
        expect(onStarted).not.toHaveBeenCalled();
    });

    it('ignores a second request while one is running', async () => {
        let finish: () => void = () => {};
        mutateAsync.mockReturnValue(new Promise<void>((resolve) => (finish = resolve)));
        const { handleStartTrack } = useStartSequenceTrack(params);

        const first = handleStartTrack('annotation-1');
        const second = await handleStartTrack('annotation-1');
        finish();

        expect(second).toBe(false);
        expect(await first).toBe(true);
        expect(mutateAsync).toHaveBeenCalledOnce();
    });
});
