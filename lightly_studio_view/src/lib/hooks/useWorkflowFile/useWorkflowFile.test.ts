import { afterEach, describe, expect, it, vi } from 'vitest';
import {
    fetchWorkflowFile,
    STALE_FILE_MESSAGE,
    transitionWorkflowFile
} from './useWorkflowFile.svelte';

const params = { projectId: 'p1', batchId: 'b1', sampleId: 's1' };

describe('fetchWorkflowFile', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('reads the batch file context from the workflow service with the session cookie', async () => {
        const body = { batch_name: 'Batch 1', can_edit: true };
        const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(body)));
        vi.stubGlobal('fetch', fetchMock);

        const file = await fetchWorkflowFile(params);

        expect(file).toEqual(body);
        expect(fetchMock).toHaveBeenCalledWith(
            '/workflow/projects/p1/batches/b1/files/s1/context',
            expect.objectContaining({ credentials: 'same-origin' })
        );
    });

    it('fails when the workflow service rejects the request', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 404 })));

        await expect(fetchWorkflowFile(params)).rejects.toThrow(
            'Could not load the batch context (404)'
        );
    });
});

describe('transitionWorkflowFile', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('asks the workflow service to move the file to the new state', async () => {
        const fetchMock = vi.fn().mockResolvedValue(new Response('{}'));
        vi.stubGlobal('fetch', fetchMock);

        await transitionWorkflowFile(
            { projectId: 'p1', batchId: 'b1', sampleId: 's1' },
            'in_review'
        );

        expect(fetchMock).toHaveBeenCalledWith(
            '/workflow/projects/p1/batches/b1/files/s1/transitions',
            expect.objectContaining({
                method: 'POST',
                credentials: 'same-origin',
                body: JSON.stringify({ state: 'in_review' })
            })
        );
    });

    it('says the file changed when the service rejects the move as out of date', async () => {
        vi.stubGlobal(
            'fetch',
            vi
                .fn()
                .mockResolvedValue(
                    new Response(
                        JSON.stringify({ detail: 'Cannot move a file from Accepted to Rework' }),
                        { status: 409 }
                    )
                )
        );

        await expect(transitionWorkflowFile(params, 'rework')).rejects.toThrow(STALE_FILE_MESSAGE);
    });

    it('fails with the service’s reason when the user may not make the move', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({ detail: 'Only the batch reviewer can make this change' }),
                    {
                        status: 403
                    }
                )
            )
        );

        await expect(transitionWorkflowFile(params, 'accepted')).rejects.toThrow(
            'Only the batch reviewer can make this change'
        );
    });

    it('fails as before when the service cannot be reached', async () => {
        vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

        await expect(transitionWorkflowFile(params, 'accepted')).rejects.toThrow('Failed to fetch');
    });

    it('fails with the status when the service gives no reason', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('oops', { status: 502 })));

        await expect(transitionWorkflowFile(params, 'accepted')).rejects.toThrow(
            'Could not change the file state (502)'
        );
    });
});
