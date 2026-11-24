import { toast } from 'svelte-sonner';
import type { WorkflowAction, WorkflowFileState } from './workflowActions';

interface Params {
    /** Moves the file; resolves once the service confirmed it. */
    onTransition: (state: WorkflowFileState) => Promise<void>;
    /** Opens the next sample. */
    onAdvance?: () => void;
}

/**
 * Moves a workflow file from the action bar. An inline move (the natural next step) confirms
 * with a toast and opens the next sample; an admin override stays on the sample. A rejected
 * move shows the error and stays.
 */
export function useWorkflowMove(getParams: () => Params) {
    let requested = $state<WorkflowFileState | null>(null);

    const move = async (target: WorkflowFileState): Promise<'moved' | 'failed'> => {
        requested = target;
        try {
            await getParams().onTransition(target);
            return 'moved';
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Could not change the file state');
            return 'failed';
        } finally {
            requested = null;
        }
    };

    return {
        /** The target of the move in flight, if any. */
        get requested() {
            return requested;
        },
        /** The natural next step: once confirmed, the labeler or reviewer moves on. */
        async moveAndAdvance(action: WorkflowAction) {
            if ((await move(action.target)) === 'failed') return;
            toast.success(action.doneMessage);
            getParams().onAdvance?.();
        },
        /** An admin override: the admin stays on the sample. */
        override(target: WorkflowFileState) {
            void move(target);
        }
    };
}
