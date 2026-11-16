import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchWorkflowFile } from './useWorkflowFile.svelte';

describe('fetchWorkflowFile', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('reads the batch file context from the workflow service with the session cookie', async () => {
        const body = { batch_name: 'Batch 1', can_edit: true };
        const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(body)));
        vi.stubGlobal('fetch', fetchMock);

        const file = await fetchWorkflowFile({ projectId: 'p1', batchId: 'b1', sampleId: 's1' });

        expect(file).toEqual(body);
        expect(fetchMock).toHaveBeenCalledWith(
            '/workflow/projects/p1/batches/b1/files/s1/context',
            expect.objectContaining({ credentials: 'same-origin' })
        );
    });

    it('fails when the workflow service rejects the request', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 404 })));

        await expect(
            fetchWorkflowFile({ projectId: 'p1', batchId: 'b1', sampleId: 's1' })
        ).rejects.toThrow('Could not load the batch context (404)');
    });
});
