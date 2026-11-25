import { toast } from 'svelte-sonner';
import type {
    WorkflowAction,
    WorkflowActionConfirmation,
    WorkflowFileState,
    WorkflowMenuAction
} from './workflowActions';

interface Params {
    /** Moves the file; resolves once the service confirmed it. */
    onTransition: (state: WorkflowFileState) => Promise<void>;
    /** Opens the next sample. */
    onAdvance?: () => void;
}

/**
 * Moves a workflow file from the action bar. An inline move (the natural next step) confirms
 * with a toast and opens the next sample; an admin override stays on the sample. A rejected
 * move shows the error and stays. Overrides, and inline moves that might be a slip, wait for
 * the user to confirm first.
 */
export function useWorkflowMove(getParams: () => Params) {
    let requested = $state<WorkflowFileState | null>(null);
    let confirming = $state<{ confirmation: WorkflowActionConfirmation; run: () => void } | null>(
        null
    );

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

    const moveAndAdvance = async (action: WorkflowAction) => {
        if ((await move(action.target)) === 'failed') return;
        toast.success(action.doneMessage);
        getParams().onAdvance?.();
    };

    return {
        /** The target of the move in flight, if any. */
        get requested() {
            return requested;
        },
        /** What the user is asked to confirm right now, if anything. */
        get confirmation() {
            return confirming?.confirmation ?? null;
        },
        /** The natural next step: once the service confirms, the labeler or reviewer moves on. */
        moveInline(action: WorkflowAction) {
            const run = () => void moveAndAdvance(action);
            if (action.confirmation) confirming = { confirmation: action.confirmation, run };
            else run();
        },
        /** An admin override, after confirmation: the admin stays on the sample. */
        override(action: WorkflowMenuAction) {
            confirming = {
                confirmation: action.confirmation,
                run: () => void move(action.target)
            };
        },
        /** Makes the move waiting for confirmation. */
        confirm() {
            confirming?.run();
            confirming = null;
        },
        /** Drops the move waiting for confirmation. */
        cancel() {
            confirming = null;
        }
    };
}
