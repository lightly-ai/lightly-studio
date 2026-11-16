import { getContext, setContext } from 'svelte';
import { useWorkflowFile, useWorkflowFileTransition, type WorkflowFile } from '$lib/hooks';

type WorkflowFileParams = Parameters<typeof useWorkflowFile>[0] extends () => infer P
    ? NonNullable<P>
    : never;

/** URL search parameters that open a sample inside a hosted workflow batch. */
export const WORKFLOW_PROJECT_PARAM = 'workflow_project';
export const WORKFLOW_BATCH_PARAM = 'workflow_batch';

type WorkflowFileContext = {
    /** True when the sample was opened from a batch. */
    readonly active: boolean;
    readonly file: WorkflowFile | undefined;
    readonly isError: boolean;
    /** Outside a batch editing is unrestricted; inside one only after the service allows it. */
    readonly canEdit: boolean;
    /** The service said the user cannot edit, or could not be asked; false while loading. */
    readonly locked: boolean;
    /** Moves the file to another state; resolves once the new state is shown. */
    transition(state: WorkflowFile['state']): Promise<void>;
    /** True while a move waits for the service. */
    readonly transitioning: boolean;
};

const CONTEXT_KEY = 'workflow-file';

/** Reads the batch parameters of a sample URL, or null when it was not opened from a batch. */
export function getWorkflowParams(url: URL, sampleId: string): WorkflowFileParams | null {
    const projectId = url.searchParams.get(WORKFLOW_PROJECT_PARAM);
    const batchId = url.searchParams.get(WORKFLOW_BATCH_PARAM);
    return projectId && batchId ? { projectId, batchId, sampleId } : null;
}

export function createWorkflowFileContext(
    getParams: () => WorkflowFileParams | null
): WorkflowFileContext {
    const { query } = useWorkflowFile(getParams);
    const { mutation } = useWorkflowFileTransition(getParams);
    const context: WorkflowFileContext = {
        get active() {
            return getParams() !== null;
        },
        get file() {
            return this.active ? query.data : undefined;
        },
        get isError() {
            return this.active && query.isError;
        },
        get canEdit() {
            return !this.active || query.data?.can_edit === true;
        },
        get locked() {
            return this.active && (query.isError || query.data?.can_edit === false);
        },
        transition(state) {
            return mutation.mutateAsync(state);
        },
        get transitioning() {
            return mutation.isPending;
        }
    };
    setContext(CONTEXT_KEY, context);
    return context;
}

/** The batch context of the open sample, or undefined in views that never open batch files. */
export function useWorkflowFileContext(): WorkflowFileContext | undefined {
    return getContext<WorkflowFileContext | undefined>(CONTEXT_KEY);
}
