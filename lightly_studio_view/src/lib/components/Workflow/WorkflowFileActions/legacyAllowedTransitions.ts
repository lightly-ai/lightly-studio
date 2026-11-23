import type { WorkflowFile } from '$lib/hooks';
import type { WorkflowFileState } from './workflowActions';

/**
 * TEMPORARY (admin-overrides ticket 02 deletes this): the moves the current user may make,
 * worked out on the client from today's turn rules. Once the workflow service returns
 * `allowed_transitions` in the file context, use that instead.
 */
export function legacyAllowedTransitions(
    file: Pick<WorkflowFile, 'state' | 'your_role' | 'can_edit'>
): WorkflowFileState[] {
    if (!file.can_edit) return [];
    if (file.your_role === 'labeler' && (file.state === 'in_progress' || file.state === 'rework')) {
        return ['in_review'];
    }
    if (file.your_role === 'reviewer' && file.state === 'in_review') {
        return ['rework', 'accepted'];
    }
    return [];
}
