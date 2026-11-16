import { createQuery } from '@tanstack/svelte-query';

interface WorkflowFileParams {
    projectId: string;
    batchId: string;
    sampleId: string;
}

/**
 * A file opened from a hosted workflow batch, as the workflow service describes it.
 * Exported as the contract of an API without a generated client, like `types.gen`.
 */
export interface WorkflowFile {
    project_id: string;
    project_name: string;
    batch_id: string;
    batch_name: string;
    sample_id: string;
    state: 'not_started' | 'in_progress' | 'in_review' | 'rework' | 'accepted';
    round: number;
    labeler: string | null;
    reviewer: string | null;
    your_role: 'labeler' | 'reviewer' | null;
    can_edit: boolean;
    waiting_for: string | null;
    position: number;
    total: number;
    previous_sample_id: string | null;
    next_sample_id: string | null;
    instructions: string;
    instructions_updated_by: string | null;
    instructions_updated_at: string | null;
}

/**
 * Reads a batch file's context from the hosted workflow service on the same origin.
 * The proxy verifies the session cookie and tells the service who is asking.
 */
export async function fetchWorkflowFile({
    projectId,
    batchId,
    sampleId
}: WorkflowFileParams): Promise<WorkflowFile> {
    const path = [projectId, batchId, sampleId].map(encodeURIComponent);
    const response = await fetch(
        `/workflow/projects/${path[0]}/batches/${path[1]}/files/${path[2]}/context`,
        { credentials: 'same-origin', headers: { Accept: 'application/json' } }
    );
    if (!response.ok) {
        throw new Error(`Could not load the batch context (${response.status})`);
    }
    return response.json();
}

/** Batch context for a file, or a disabled query when the file was not opened from a batch. */
export const useWorkflowFile = (getParams: () => WorkflowFileParams | null) => {
    const query = createQuery(() => {
        const params = getParams();
        return {
            queryKey: ['workflow-file', params],
            queryFn: () => fetchWorkflowFile(params!),
            enabled: params !== null,
            retry: false
        };
    });
    return { query };
};
