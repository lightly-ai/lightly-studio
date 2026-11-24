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
    /**
     * Call after an annotation was created on `sampleId`. The labeler's first annotation
     * moves a Not started file to In progress; anything else changes nothing.
     */
    startWork(sampleId: string): Promise<void>;
    /**
     * Registers how the page opens the next sample: the target of its → arrow. Returns the
     * unregister function; registering again replaces the previous handler.
     */
    registerNext(goToNext: () => void): () => void;
    /** Opens the next sample, if the page registered one; otherwise stays on this sample. */
    goToNext(): void;
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
    /** The page's → target, registered by its stepper. */
    let goToNextHandler: (() => void) | undefined;
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
        },
        async startWork(sampleId) {
            const file = this.file;
            if (
                file?.sample_id !== sampleId ||
                file.state !== 'not_started' ||
                file.your_role !== 'labeler' ||
                !file.your_turn
            ) {
                return;
            }
            await mutation.mutateAsync('in_progress');
        },
        registerNext(goToNext) {
            goToNextHandler = goToNext;
            return () => {
                if (goToNextHandler === goToNext) goToNextHandler = undefined;
            };
        },
        goToNext() {
            goToNextHandler?.();
        }
    };
    setContext(CONTEXT_KEY, context);
    return context;
}

/** The batch context of the open sample, or undefined in views that never open batch files. */
export function useWorkflowFileContext(): WorkflowFileContext | undefined {
    return getContext<WorkflowFileContext | undefined>(CONTEXT_KEY);
}
