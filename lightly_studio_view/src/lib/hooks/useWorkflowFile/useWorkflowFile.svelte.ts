import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';

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
    /** The user may edit the annotations now: on their turn, or always as an admin. */
    can_edit: boolean;
    /** It is the user's turn on this file as its labeler or reviewer. */
    your_turn: boolean;
    /** States the current user may move the file to right now. */
    allowed_transitions: WorkflowFileState[];
    waiting_for: string | null;
    position: number;
    total: number;
    previous_sample_id: string | null;
    next_sample_id: string | null;
    instructions: string;
    instructions_updated_by: string | null;
    instructions_updated_at: string | null;
}

type WorkflowFileState = WorkflowFile['state'];

const filePath = ({ projectId, batchId, sampleId }: WorkflowFileParams) => {
    const [project, batch, sample] = [projectId, batchId, sampleId].map(encodeURIComponent);
    return `/workflow/projects/${project}/batches/${batch}/files/${sample}`;
};

const workflowFileKey = (params: WorkflowFileParams | null) => ['workflow-file', params];

/**
 * Reads a batch file's context from the hosted workflow service on the same origin.
 * The proxy verifies the session cookie and tells the service who is asking.
 */
export async function fetchWorkflowFile(params: WorkflowFileParams): Promise<WorkflowFile> {
    const response = await fetch(`${filePath(params)}/context`, {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' }
    });
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
            queryKey: workflowFileKey(params),
            queryFn: () => fetchWorkflowFile(params!),
            enabled: params !== null,
            retry: false
        };
    });
    return { query };
};

/** Moves a batch file to another state; the service checks that the move and the caller are allowed. */
export async function transitionWorkflowFile(
    params: WorkflowFileParams,
    state: WorkflowFileState
): Promise<void> {
    const response = await fetch(`${filePath(params)}/transitions`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ state })
    });
    if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = typeof body?.detail === 'string' ? body.detail : null;
        throw new Error(detail ?? `Could not change the file state (${response.status})`);
    }
}

/**
 * Moves the open batch file to another state. Resolves only once the file's context was
 * read again, so the badge, turn and edit lock change after the service confirmed the move.
 * A rejected move reads the context again too, in case the file moved elsewhere meanwhile.
 */
export const useWorkflowFileTransition = (getParams: () => WorkflowFileParams | null) => {
    const client = useQueryClient();
    const mutation = createMutation(() => ({
        mutationFn: async (state: WorkflowFileState) => {
            const params = getParams();
            if (!params) throw new Error('The file was not opened from a batch');
            const refetch = () =>
                client.refetchQueries(
                    { queryKey: workflowFileKey(params), exact: true },
                    { throwOnError: true }
                );
            try {
                await transitionWorkflowFile(params, state);
            } catch (error) {
                await refetch().catch(() => undefined);
                throw error;
            }
            await refetch();
        }
    }));
    return { mutation };
};
