import type { WorkflowFile } from '$lib/hooks';

type WorkflowFileState = WorkflowFile['state'];

/** Labels and standard colors of the workflow file states, shared with the workspace pages. */
export const WORKFLOW_STATES: Record<WorkflowFileState, { label: string; color: string }> = {
    not_started: { label: 'Not started', color: '#71717a' },
    in_progress: { label: 'In progress', color: '#f59e0b' },
    in_review: { label: 'In review', color: '#60a5fa' },
    rework: { label: 'Rework', color: '#ef4444' },
    accepted: { label: 'Accepted', color: '#3bd99f' }
};

/** Whether a value is a workflow file state, that is a key of `WORKFLOW_STATES`. */
export function isWorkflowFileState(state: string): state is WorkflowFileState {
    return Object.hasOwn(WORKFLOW_STATES, state);
}

/** Turn indicator colors from the design: green on the user's turn, gray otherwise. */
export const TURN_COLORS = { yours: '#3bd99f', others: '#9f9fa6' };

const UNSUBMITTED = new Set<WorkflowFileState>(['not_started', 'in_progress']);

/** "Round N", or "---" while a file has not been submitted for review yet. */
export function roundText({ state, round }: Pick<WorkflowFile, 'state' | 'round'>): string {
    return round === 1 && UNSUBMITTED.has(state) ? '---' : `Round ${round}`;
}

/** Whose turn it is on a file, from the current user's point of view. */
export function turnText(file: Pick<WorkflowFile, 'state' | 'your_turn' | 'waiting_for'>): {
    text: string;
    yourTurn: boolean;
} {
    if (file.state === 'accepted') return { text: 'Done', yourTurn: false };
    if (file.your_turn) return { text: 'Your turn', yourTurn: true };
    return { text: `Waiting for ${file.waiting_for ?? 'an assignee'}`, yourTurn: false };
}

/** Why the current user cannot edit a file, or null when they can. */
export function readOnlyText(
    file: Pick<WorkflowFile, 'state' | 'can_edit' | 'your_role' | 'labeler' | 'reviewer'>
): string | null {
    if (file.can_edit) return null;
    const labeler = file.labeler ?? 'The labeler';
    const reviewer = file.reviewer ?? 'the reviewer';
    if (file.state === 'accepted') {
        return `Accepted by ${reviewer}. Only an admin can change an accepted file.`;
    }
    if (file.your_role === 'reviewer') {
        return `${labeler} is working on this file. You can edit it once it’s submitted for review.`;
    }
    if (file.your_role === 'labeler') {
        return `You submitted this file. It’s read-only while ${reviewer} reviews it.`;
    }
    return 'You aren’t assigned to this batch, so this file is read-only for you.';
}
